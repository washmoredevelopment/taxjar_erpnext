# Copyright (c) 2026, Washmore Development and contributors
# For license information, please see license.txt

import frappe
from erpnext.setup.utils import enable_all_roles_and_domains, set_defaults_for_tests
from test_utils.utils.setup_fixtures import (
	before_test as load_company,
	create_item_groups,
	get_fixtures_data_from_file,
)

from taxjar_erpnext.tests.constants import (
	COMPANY,
	CUSTOMER_MA,
	CUSTOMER_NH,
	PIE_ITEM,
)


def before_test():
	frappe.clear_cache()
	load_company(COMPANY)
	enable_all_roles_and_domains()
	set_defaults_for_tests()
	ensure_us_regional_fields()
	frappe.db.set_default("company", COMPANY)

	settings = frappe._dict(
		company=COMPANY,
		day=frappe.utils.getdate().replace(month=1, day=1),
	)

	create_company_address()
	create_item_groups(settings)
	create_pie_items(settings)
	create_test_customers(settings)
	ensure_stock_for_pies(settings)
	create_taxjar_account(settings)

	for module in frappe.get_all("Module Onboarding"):
		frappe.db.set_value("Module Onboarding", module, "is_complete", 1)

	frappe.db.commit()


def ensure_us_regional_fields():
	if frappe.db.has_column("Customer", "exempt_from_sales_tax"):
		return

	from erpnext.regional.united_states.setup import setup as setup_us_regional

	setup_us_regional()


def create_company_address():
	addresses = get_fixtures_data_from_file("addresses.json")
	for address in addresses:
		company_links = [
			link
			for link in address.get("links", [])
			if link.get("link_doctype") == "Company" and link.get("link_name") == COMPANY
		]
		if not company_links:
			continue

		if frappe.db.exists("Address", {"address_line1": address.get("address_line1")}):
			return

		addr = frappe.new_doc("Address")
		addr.update({key: value for key, value in address.items() if key != "links"})
		addr.set("links", company_links)
		addr.insert(ignore_permissions=True)
		return


def default_warehouse(company=COMPANY):
	abbr = frappe.db.get_value("Company", company, "abbr")
	stores = f"Stores - {abbr}"
	if frappe.db.exists("Warehouse", stores):
		return stores

	return frappe.get_value(
		"Warehouse",
		{"company": company, "is_group": 0},
	)


def create_pie_items(settings):
	pie_items = (
		"Ambrosia Pie",
		"Double Plum Pie",
		"Gooseberry Pie",
	)
	warehouse = default_warehouse(settings.company)
	income_account = frappe.get_value("Company", settings.company, "default_income_account")

	for item in get_fixtures_data_from_file("items.json"):
		item_code = item.get("item_code")
		if item_code not in pie_items:
			continue

		if frappe.db.exists("Item", item_code):
			item_doc = frappe.get_doc("Item", item_code)
			for row in item_doc.item_defaults:
				if row.company == settings.company:
					row.default_warehouse = warehouse
					row.income_account = income_account
			item_doc.save(ignore_permissions=True)
			continue

		doc = frappe.new_doc("Item")
		doc.update({key: value for key, value in item.items() if key != "item_defaults"})
		for row in item.get("item_defaults", []):
			doc.append(
				"item_defaults",
				{
					**row,
					"company": settings.company,
					"default_warehouse": warehouse,
					"income_account": income_account,
				},
			)
		doc.insert(ignore_permissions=True)


def create_test_customers(settings):
	from erpnext.accounts.party import get_party_account

	test_customers = (CUSTOMER_MA, CUSTOMER_NH)

	for customer in get_fixtures_data_from_file("customers.json"):
		customer_name = customer.get("customer_name")
		if customer_name not in test_customers or frappe.db.exists("Customer", customer_name):
			continue

		cust = frappe.new_doc("Customer")
		cust.update({key: value for key, value in customer.items() if key not in ("user", "email")})
		cust.insert(ignore_permissions=True)

	for customer_name in test_customers:
		get_party_account("Customer", customer_name, settings.company)

	for address in get_fixtures_data_from_file("addresses.json"):
		customer_links = [
			link
			for link in address.get("links", [])
			if link.get("link_doctype") == "Customer" and link.get("link_name") in test_customers
		]
		if not customer_links:
			continue

		address_name = address.get("name")
		if address_name and frappe.db.exists("Address", address_name):
			continue

		addr = frappe.new_doc("Address")
		addr.update({key: value for key, value in address.items() if key != "links"})
		addr.set("links", customer_links)
		addr.insert(ignore_permissions=True)


def ensure_stock_for_pies(settings):
	warehouse = default_warehouse(settings.company)
	if frappe.db.get_value("Bin", {"item_code": PIE_ITEM, "warehouse": warehouse}, "actual_qty"):
		return

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type = "Material Receipt"
	stock_entry.company = settings.company
	stock_entry.append(
		"items",
		{
			"item_code": PIE_ITEM,
			"qty": 100,
			"t_warehouse": warehouse,
			"basic_rate": 12,
		},
	)
	stock_entry.insert(ignore_permissions=True)
	stock_entry.submit()


def get_or_create_account(account_name, root_type, account_type=None, parent_account=None):
	company_abbr = frappe.db.get_value("Company", COMPANY, "abbr")
	full_name = f"{account_name} - {company_abbr}"

	if frappe.db.exists("Account", full_name):
		return full_name

	if not parent_account:
		parent_account = frappe.get_value(
			"Account",
			{"company": COMPANY, "root_type": root_type, "is_group": 1},
		)

	account = frappe.new_doc("Account")
	account.account_name = account_name
	account.company = COMPANY
	account.root_type = root_type
	account.parent_account = parent_account
	if account_type:
		account.account_type = account_type
	account.insert(ignore_permissions=True)
	return account.name


def create_taxjar_account(settings):
	tax_account = get_tax_account()
	shipping_account = get_or_create_account(
		"Shipping Charges",
		"Expense",
		account_type="Chargeable",
	)

	if frappe.db.exists("TaxJar Account", COMPANY):
		doc = frappe.get_doc("TaxJar Account", COMPANY)
	else:
		doc = frappe.new_doc("TaxJar Account")
		doc.company = COMPANY

	doc.taxjar_calculate_tax = 1
	doc.is_sandbox = 1
	doc.taxjar_create_transactions = 1
	doc.sandbox_api_key = "test_sandbox_key"
	doc.tax_account_head = tax_account
	doc.shipping_account_head = shipping_account
	doc.calculate_tax_for_all_states = 1
	doc.notify_on_non_nexus_sales = 1
	doc.non_nexus_notification_user = "Administrator"
	doc.set("nexus", [])
	doc.append(
		"nexus",
		{
			"region_code": "MA",
			"region": "Massachusetts",
			"country": "United States",
			"country_code": "US",
		},
	)
	doc.save(ignore_permissions=True)


def get_tax_account():
	existing = frappe.get_value(
		"Account",
		{"company": COMPANY, "account_type": "Tax", "is_group": 0},
	)
	if existing:
		return existing

	parent = frappe.get_value(
		"Account",
		{"company": COMPANY, "account_name": "Duties and Taxes", "is_group": 1},
	)
	return get_or_create_account(
		"Sales Tax Payable",
		"Liability",
		account_type="Tax",
		parent_account=parent,
	)


def ensure_taxjar_enabled():
	frappe.db.set_value("TaxJar Account", COMPANY, "taxjar_calculate_tax", 1)
	frappe.clear_cache()


def disable_taxjar_calculation():
	frappe.db.set_value("TaxJar Account", COMPANY, "taxjar_calculate_tax", 0)
	frappe.clear_cache()

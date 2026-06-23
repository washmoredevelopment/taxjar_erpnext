# Copyright (c) 2026, Washmore Development and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

from taxjar_erpnext.taxjar_erpnext.taxjar_erpnext import set_sales_tax
from taxjar_erpnext.tests.constants import (
	COMPANY,
	PIE_ITEM,
)
from taxjar_erpnext.tests.setup import default_warehouse


def append_pie_line(doc, rate=24.00):
	row = {"item_code": PIE_ITEM, "qty": 1, "rate": rate}
	if doc.doctype in ("Sales Order", "Sales Invoice"):
		row["warehouse"] = default_warehouse(COMPANY)
	doc.append("items", row)


def make_quotation(customer, shipping_address_name, rate=24.00):
	doc = frappe.new_doc("Quotation")
	doc.company = COMPANY
	doc.quotation_to = "Customer"
	doc.party_name = customer
	doc.shipping_address_name = shipping_address_name
	doc.transaction_date = frappe.utils.today()
	doc.valid_till = frappe.utils.add_days(frappe.utils.today(), 30)
	append_pie_line(doc, rate=rate)
	return doc


def make_sales_order(customer, shipping_address_name, rate=24.00):
	doc = frappe.new_doc("Sales Order")
	doc.company = COMPANY
	doc.customer = customer
	doc.delivery_date = frappe.utils.add_days(frappe.utils.today(), 7)
	doc.shipping_address_name = shipping_address_name
	append_pie_line(doc, rate=rate)
	return doc


def make_sales_invoice(customer, shipping_address_name, rate=24.00):
	doc = frappe.new_doc("Sales Invoice")
	doc.company = COMPANY
	doc.customer = customer
	doc.due_date = frappe.utils.add_days(frappe.utils.today(), 30)
	doc.shipping_address_name = shipping_address_name
	append_pie_line(doc, rate=rate)
	return doc


def save_and_validate(doc):
	if hasattr(doc, "set_missing_values"):
		doc.set_missing_values()

	doc.insert(ignore_permissions=True)
	set_sales_tax(doc, "validate")
	doc.save(ignore_permissions=True)
	return doc


def tax_account_head():
	return frappe.db.get_value("TaxJar Account", COMPANY, "tax_account_head")


def assert_no_taxjar_tax_row(doc):
	assert tax_row(doc) is None


def tax_row(doc):
	account = tax_account_head()
	for row in doc.taxes:
		if row.account_head == account:
			return row
	return None


def assert_taxjar_tax_row(doc, amount, description="Sales Tax"):
	row = tax_row(doc)
	assert row is not None, f"Expected TaxJar tax row on {doc.doctype}"
	assert flt(row.tax_amount) == flt(amount)
	assert row.description == description

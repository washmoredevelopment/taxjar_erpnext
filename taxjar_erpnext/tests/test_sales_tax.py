# Copyright (c) 2026, Washmore Development and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import flt

from taxjar_erpnext.tests.fixtures import (
	COMPANY,
	CUSTOMER_MA,
	CUSTOMER_WA,
	EXEMPT_ITEM,
	EXEMPT_TAX_CODE,
	PIE_ITEM,
	PIE_TAX_CODE,
	SHIPPING_MA,
	SHIPPING_WA,
)
from taxjar_erpnext.tests.sales_documents import (
	assert_no_taxjar_tax_row,
	assert_taxjar_tax_row,
	find_item_row,
	make_quotation,
	make_sales_invoice,
	make_sales_order,
	save_and_validate,
	tax_row,
)
from taxjar_erpnext.tests.setup import disable_taxjar_calculation, ensure_taxjar_enabled
from taxjar_erpnext.tests.taxjar_client import (
	make_mixed_cart_tax_response,
	make_rates_for_location_response,
	make_tax_for_order_response,
	patch_taxjar_client,
)


@pytest.mark.order(10)
def test_set_sales_tax_without_enabled_taxjar_account():
	"""
	Ambrosia has no active TaxJar integration when calculation is disabled.

	| Document   | Expected tax row |
	| ---------- | ---------------- |
	| Quotation  | none             |
	| Sales Order| none             |
	| Sales Invoice | none          |
	"""
	disable_taxjar_calculation()

	for factory, kwargs in (
		(make_quotation, {"customer": CUSTOMER_MA, "shipping_address_name": SHIPPING_MA}),
		(make_sales_order, {"customer": CUSTOMER_MA, "shipping_address_name": SHIPPING_MA}),
		(make_sales_invoice, {"customer": CUSTOMER_MA, "shipping_address_name": SHIPPING_MA}),
	):
		doc = factory(**kwargs)
		save_and_validate(doc)
		assert_no_taxjar_tax_row(doc)

	ensure_taxjar_enabled()


@pytest.mark.order(20)
def test_nexus_state_applies_tax_on_quotation_sales_order_and_invoice(monkeymodule):
	"""
	Cassiopeia ships to Salem, MA. Ambrosia has MA nexus and TaxJar returns $1.92 on a $24 pie.

	| Document      | Tax row | Line tax_collectable |
	| ------------- | ------- | -------------------- |
	| Quotation     | $1.92   | $1.92                |
	| Sales Order   | $1.92   | $1.92                |
	| Sales Invoice | $1.92   | $1.92                |
	"""
	tax_response = make_tax_for_order_response(amount_to_collect=1.92)
	patch_taxjar_client(monkeymodule, tax_for_order=tax_response)

	for factory, kwargs in (
		(make_quotation, {"customer": CUSTOMER_MA, "shipping_address_name": SHIPPING_MA}),
		(make_sales_order, {"customer": CUSTOMER_MA, "shipping_address_name": SHIPPING_MA}),
		(make_sales_invoice, {"customer": CUSTOMER_MA, "shipping_address_name": SHIPPING_MA}),
	):
		doc = factory(**kwargs)
		save_and_validate(doc)
		assert_taxjar_tax_row(doc, 1.92)
		assert flt(doc.items[0].tax_collectable) == 1.92
		assert flt(doc.items[0].taxable_amount) == 24.00


@pytest.mark.order(25)
def test_nexus_sales_invoice_sends_product_tax_code_from_item_default(monkeymodule):
	"""
	Cassiopeia's MA invoice sends Ambrosia Pie's company Item Default category to TaxJar.
	"""
	client = patch_taxjar_client(
		monkeymodule,
		tax_for_order=make_tax_for_order_response(amount_to_collect=1.92),
	)

	si = make_sales_invoice(customer=CUSTOMER_MA, shipping_address_name=SHIPPING_MA)
	save_and_validate(si)

	payload = client.tax_for_order.call_args[0][0]
	assert payload["line_items"][0]["product_tax_code"] == PIE_TAX_CODE


@pytest.mark.order(30)
def test_non_nexus_destination_clears_tax_and_notifies_on_sales_order_submit(monkeymodule):
	"""
	Circe Pacific Foods ships to Seattle, WA. Ambrosia has no WA nexus, so Sales Orders and
	Sales Invoices validate without TaxJar tax. Submitting the Sales Order still creates
	a ToDo for the configured recipient.
	"""
	patch_taxjar_client(
		monkeymodule,
		tax_for_order=make_tax_for_order_response(amount_to_collect=1.50),
	)

	for factory, kwargs in (
		(make_sales_order, {"customer": CUSTOMER_WA, "shipping_address_name": SHIPPING_WA}),
		(make_sales_invoice, {"customer": CUSTOMER_WA, "shipping_address_name": SHIPPING_WA}),
	):
		doc = factory(**kwargs)
		save_and_validate(doc)
		assert_no_taxjar_tax_row(doc)

	so = make_sales_order(customer=CUSTOMER_WA, shipping_address_name=SHIPPING_WA)
	save_and_validate(so)
	so.submit()

	todos = frappe.get_all(
		"ToDo",
		filters={"reference_type": "Sales Order", "reference_name": so.name},
		pluck="name",
	)
	assert len(todos) == 1
	todo = frappe.get_doc("ToDo", todos[0])
	assert todo.allocated_to == "Administrator"
	assert "WA" in todo.description


@pytest.mark.order(40)
def test_quotation_non_nexus_uses_estimated_sales_tax_fallback(monkeymodule):
	"""
	Non-nexus WA quote with calculate_tax_for_all_states uses rates_for_location fallback.

	| Document  | Destination | Tax description      | Amount         |
	| --------- | ----------- | -------------------- | -------------- |
	| Quotation | WA          | Estimated Sales Tax  | $24 × 10.25%   |
	| Sales Order | WA        | none                 |                |
	"""
	patch_taxjar_client(
		monkeymodule,
		tax_for_order=make_tax_for_order_response(amount_to_collect=0),
		rates_for_location=make_rates_for_location_response(combined_rate=0.1025),
	)

	quote = make_quotation(customer=CUSTOMER_WA, shipping_address_name=SHIPPING_WA)
	save_and_validate(quote)
	assert_taxjar_tax_row(quote, 2.46, description="Estimated Sales Tax")

	so = make_sales_order(customer=CUSTOMER_WA, shipping_address_name=SHIPPING_WA)
	save_and_validate(so)
	assert_no_taxjar_tax_row(so)


@pytest.mark.order(45)
def test_nexus_mixed_cart_partial_tax_on_taxable_line_only(monkeymodule):
	"""
	Cassiopeia ships to Salem, MA. The cart has Ambrosia Pie (Prepared Foods, taxable)
	and Cloudberry Preserves (home-consumption grocery, exempt category). TaxJar returns
	tax only on the pie line.

	| Line                 | product_tax_code | tax_collectable |
	| -------------------- | ---------------- | --------------- |
	| Ambrosia Pie         | 41000            | $1.92           |
	| Cloudberry Preserves | 50000000A0000    | $0.00           |
	| Document tax row     |                  | $1.92           |

	| Account             |  Debit  | Credit |
	| ------------------- | ------: | -----: |
	| Accounts Receivable |  $37.92 |        |
	| Sales               |         | $36.00 |
	| Sales Tax Payable   |         |  $1.92 |
	"""
	client = patch_taxjar_client(
		monkeymodule,
		tax_for_order=make_mixed_cart_tax_response(),
	)

	si = make_sales_invoice(
		customer=CUSTOMER_MA,
		shipping_address_name=SHIPPING_MA,
		mixed_cart=True,
	)
	save_and_validate(si)
	assert_taxjar_tax_row(si, 1.92)

	pie_line = find_item_row(si, PIE_ITEM)
	exempt_line = find_item_row(si, EXEMPT_ITEM)
	assert flt(pie_line.tax_collectable) == 1.92
	assert flt(pie_line.taxable_amount) == 24.00
	assert flt(exempt_line.tax_collectable) == 0
	assert flt(exempt_line.taxable_amount) == 0

	payload = client.tax_for_order.call_args[0][0]
	assert payload["line_items"][0]["product_tax_code"] == PIE_TAX_CODE
	assert payload["line_items"][1]["product_tax_code"] == EXEMPT_TAX_CODE

	si.submit()

	client.create_order.assert_called_once()
	order_payload = client.create_order.call_args[0][0]
	assert flt(order_payload["sales_tax"]) == 1.92
	assert order_payload["line_items"][0]["product_tax_code"] == PIE_TAX_CODE
	assert order_payload["line_items"][1]["product_tax_code"] == EXEMPT_TAX_CODE
	assert flt(order_payload["line_items"][0]["sales_tax"]) == 1.92
	assert flt(order_payload["line_items"][1]["sales_tax"]) == 0

	gl_entries = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Sales Invoice", "voucher_no": si.name, "is_cancelled": 0},
		fields=["account", "debit", "credit"],
	)
	tax_account = tax_row(si).account_head
	receivable = frappe.get_value(
		"Account",
		{"company": COMPANY, "account_type": "Receivable", "is_group": 0},
	)
	pie_sales_account = frappe.db.get_value(
		"Sales Invoice Item",
		{"parent": si.name, "item_code": PIE_ITEM},
		"income_account",
	)

	debits = {row.account: flt(row.debit) for row in gl_entries if flt(row.debit)}
	credits = {row.account: flt(row.credit) for row in gl_entries if flt(row.credit)}

	assert flt(debits.get(receivable)) == 37.92
	assert flt(credits.get(pie_sales_account)) == 36.00
	assert flt(credits.get(tax_account)) == 1.92


@pytest.mark.order(50)
def test_exempt_customer_skips_tax_collection(monkeymodule):
	"""
	Document-level exemption zeroes TaxJar tax on Quotation, Sales Order, and Sales Invoice.
	"""
	patch_taxjar_client(
		monkeymodule,
		tax_for_order=make_tax_for_order_response(amount_to_collect=1.92),
	)

	for factory, kwargs in (
		(make_quotation, {"customer": CUSTOMER_MA, "shipping_address_name": SHIPPING_MA}),
		(make_sales_order, {"customer": CUSTOMER_MA, "shipping_address_name": SHIPPING_MA}),
		(make_sales_invoice, {"customer": CUSTOMER_MA, "shipping_address_name": SHIPPING_MA}),
	):
		doc = factory(**kwargs)
		doc.exempt_from_sales_tax = 1
		save_and_validate(doc)
		assert_no_taxjar_tax_row(doc)


@pytest.mark.order(60)
def test_sales_invoice_submit_posts_tax_and_creates_taxjar_order(monkeymodule):
	"""
	Ambrosia sells an Ambrosia Pie to Cassiopeia in MA with $1.92 sales tax.

	| Account             |  Debit  | Credit |
	| ------------------- | ------: | -----: |
	| Accounts Receivable |  $25.92 |        |
	| Sales               |         | $24.00 |
	| Sales Tax Payable   |         |  $1.92 |
	"""
	tax_response = make_tax_for_order_response(amount_to_collect=1.92)
	client = patch_taxjar_client(monkeymodule, tax_for_order=tax_response)

	si = make_sales_invoice(customer=CUSTOMER_MA, shipping_address_name=SHIPPING_MA)
	save_and_validate(si)
	assert_taxjar_tax_row(si, 1.92)
	si.submit()

	client.create_order.assert_called_once()
	order_payload = client.create_order.call_args[0][0]
	assert order_payload["transaction_id"] == si.name
	assert flt(order_payload["sales_tax"]) == 1.92

	gl_entries = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Sales Invoice", "voucher_no": si.name, "is_cancelled": 0},
		fields=["account", "debit", "credit"],
	)
	tax_account = tax_row(si).account_head
	receivable = frappe.get_value(
		"Account",
		{"company": COMPANY, "account_type": "Receivable", "is_group": 0},
	)
	sales_account = frappe.db.get_value(
		"Sales Invoice Item",
		{"parent": si.name, "item_code": PIE_ITEM},
		"income_account",
	)

	debits = {row.account: flt(row.debit) for row in gl_entries if flt(row.debit)}
	credits = {row.account: flt(row.credit) for row in gl_entries if flt(row.credit)}

	assert flt(debits.get(receivable)) == 25.92
	assert flt(credits.get(sales_account)) == 24.00
	assert flt(credits.get(tax_account)) == 1.92


@pytest.mark.order(70)
def test_sales_invoice_cancel_deletes_taxjar_order(monkeymodule):
	"""
	Cancelling a submitted invoice removes the TaxJar order transaction.
	"""
	tax_response = make_tax_for_order_response(amount_to_collect=1.92)
	client = patch_taxjar_client(monkeymodule, tax_for_order=tax_response)

	si = make_sales_invoice(customer=CUSTOMER_MA, shipping_address_name=SHIPPING_MA)
	save_and_validate(si)
	si.submit()
	si.cancel()

	client.delete_order.assert_called_once_with(si.name)

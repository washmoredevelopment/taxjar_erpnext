# Copyright (c) 2026, Washmore Development and contributors
# For license information, please see license.txt

import frappe
import pytest

from taxjar_erpnext.tests.constants import COMPANY
from taxjar_erpnext.taxjar_erpnext.doctype.taxjar_account.taxjar_account import (
	add_product_tax_categories,
	make_custom_fields,
)


@pytest.mark.order(80)
def test_taxjar_account_requires_calculation_before_sandbox_or_transactions():
	"""
	Enabling sandbox mode or transaction sync without tax calculation is rejected.
	"""
	doc = frappe.new_doc("TaxJar Account")
	doc.company = COMPANY
	doc.taxjar_calculate_tax = 0
	doc.is_sandbox = 1

	with pytest.raises(frappe.exceptions.ValidationError):
		doc.validate()

	doc.is_sandbox = 0
	doc.taxjar_create_transactions = 1

	with pytest.raises(frappe.exceptions.ValidationError):
		doc.validate()


@pytest.mark.order(90)
def test_product_tax_categories_and_custom_fields_are_created():
	"""
	Enabling tax calculation seeds Product Tax Category rows and Item / SI custom fields.
	"""
	add_product_tax_categories()
	make_custom_fields(update=True)

	assert frappe.db.exists(
		"Custom Field",
		{"dt": "Sales Invoice Item", "fieldname": "product_tax_category"},
	)
	assert frappe.db.exists(
		"Custom Field",
		{"dt": "Item", "fieldname": "product_tax_category"},
	)
	assert frappe.db.count("Product Tax Category") > 0

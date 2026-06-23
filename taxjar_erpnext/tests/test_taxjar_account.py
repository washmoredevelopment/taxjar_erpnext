# Copyright (c) 2026, Washmore Development and contributors
# For license information, please see license.txt

import frappe
import pytest

from taxjar_erpnext.tests.fixtures import COMPANY
from taxjar_erpnext.taxjar_erpnext.doctype.taxjar_account.taxjar_account import (
	add_product_tax_categories,
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
def test_product_tax_categories_are_seeded():
	"""Enabling tax calculation seeds Product Tax Category rows from fixture data."""
	add_product_tax_categories()

	assert frappe.db.count("Product Tax Category") > 0


@pytest.mark.order(91)
def test_custom_fields_are_defined_in_json():
	"""Item Default and Sales Invoice Item custom fields are synced from app JSON on migrate."""
	assert frappe.db.exists(
		"Custom Field",
		{"dt": "Sales Invoice Item", "fieldname": "product_tax_category"},
	)
	assert frappe.db.exists(
		"Custom Field",
		{"dt": "Sales Invoice Item", "fieldname": "tax_collectable"},
	)
	assert frappe.db.exists(
		"Custom Field",
		{"dt": "Sales Invoice Item", "fieldname": "taxable_amount"},
	)
	assert frappe.db.exists(
		"Custom Field",
		{"dt": "Item Default", "fieldname": "product_tax_category"},
	)

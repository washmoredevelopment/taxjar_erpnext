# Copyright (c) 2026, Washmore Development, AgriTheory and contributors
# For license information, please see license.txt

import json
from pathlib import Path

import frappe

PRODUCT_TAX_CATEGORY_DATA_PATH = (
	Path(__file__).resolve().parent
	/ "taxjar_erpnext"
	/ "doctype"
	/ "taxjar_account"
	/ "product_tax_category_data.json"
)


def after_install():
	add_product_tax_categories()


def add_product_tax_categories():
	if PRODUCT_TAX_CATEGORY_DATA_PATH.is_file():
		with PRODUCT_TAX_CATEGORY_DATA_PATH.open() as f:
			tax_categories = json.loads(f.read())
		create_tax_categories(tax_categories["categories"])
	else:
		frappe.log_error("product_tax_category_data.json not found", "TaxJar Account Setup")


def create_tax_categories(data):
	for d in data:
		if not frappe.db.exists("Product Tax Category", {"product_tax_code": d.get("product_tax_code")}):
			tax_category = frappe.new_doc("Product Tax Category")
			tax_category.description = d.get("description")
			tax_category.product_tax_code = d.get("product_tax_code")
			tax_category.category_name = d.get("name")
			tax_category.db_insert()

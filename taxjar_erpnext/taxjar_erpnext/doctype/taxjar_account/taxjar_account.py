# Copyright (c) 2024, Washmore Development and contributors
# For license information, please see license.txt

import json
import os

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model.document import Document
from frappe.permissions import add_permission, update_permission_property


class TaxJarAccount(Document):
	def validate(self):
		self.validate_tax_calculation_settings()

	def on_update(self):
		self.setup_custom_fields_if_needed()

	def validate_tax_calculation_settings(self):
		if not self.taxjar_calculate_tax and (self.taxjar_create_transactions or self.is_sandbox):
			frappe.throw(
				_(
					"Before enabling <b>Create Transaction</b> or <b>Sandbox Mode</b>, "
					"you need to check the <b>Enable Tax Calculation</b> box"
				)
			)

	def setup_custom_fields_if_needed(self):
		"""Setup custom fields when tax calculation is enabled"""
		if not self.taxjar_calculate_tax:
			return

		fields_already_exist = frappe.db.exists(
			"Custom Field",
			{"dt": ("in", ["Item", "Sales Invoice Item"]), "fieldname": "product_tax_category"},
		)

		if not fields_already_exist:
			add_product_tax_categories()
			make_custom_fields()
			add_permissions()

	@frappe.whitelist()
	def update_nexus_list(self):
		"""Fetch nexus regions from TaxJar API and update the nexus table"""
		from taxjar_erpnext.taxjar_erpnext.taxjar_erpnext import get_client

		client = get_client(self.company)
		if not client:
			frappe.throw(_("Unable to connect to TaxJar. Please check your API credentials."))

		nexus = client.nexus_regions()
		new_nexus_list = [frappe._dict(address) for address in nexus]

		self.set("nexus", [])
		self.set("nexus", new_nexus_list)
		self.save()

		frappe.msgprint(_("Nexus list updated successfully"), indicator="green")


def toggle_tax_category_fields(hidden):
	frappe.set_value(
		"Custom Field",
		{"dt": "Sales Invoice Item", "fieldname": "product_tax_category"},
		"hidden",
		hidden,
	)
	frappe.set_value(
		"Custom Field", {"dt": "Item", "fieldname": "product_tax_category"}, "hidden", hidden
	)


def add_product_tax_categories():
	# Look for the data file in the taxjar_settings folder (for backward compatibility)
	# or in the current folder
	possible_paths = [
		os.path.join(os.path.dirname(__file__), "product_tax_category_data.json"),
		os.path.join(os.path.dirname(__file__), "..", "taxjar_settings", "product_tax_category_data.json"),
	]
	
	for path in possible_paths:
		if os.path.exists(path):
			with open(path, "r") as f:
				tax_categories = json.loads(f.read())
			create_tax_categories(tax_categories["categories"])
			return
	
	frappe.log_error("product_tax_category_data.json not found", "TaxJar Account Setup")


def create_tax_categories(data):
	for d in data:
		if not frappe.db.exists("Product Tax Category", {"product_tax_code": d.get("product_tax_code")}):
			tax_category = frappe.new_doc("Product Tax Category")
			tax_category.description = d.get("description")
			tax_category.product_tax_code = d.get("product_tax_code")
			tax_category.category_name = d.get("name")
			tax_category.db_insert()


def make_custom_fields(update=True):
	custom_fields = {
		"Sales Invoice Item": [
			dict(
				fieldname="product_tax_category",
				fieldtype="Link",
				insert_after="description",
				options="Product Tax Category",
				label="Product Tax Category",
				fetch_from="item_code.product_tax_category",
			),
			dict(
				fieldname="tax_collectable",
				fieldtype="Currency",
				insert_after="net_amount",
				label="Tax Collectable",
				read_only=1,
				options="currency",
			),
			dict(
				fieldname="taxable_amount",
				fieldtype="Currency",
				insert_after="tax_collectable",
				label="Taxable Amount",
				read_only=1,
				options="currency",
			),
		],
		"Item": [
			dict(
				fieldname="product_tax_category",
				fieldtype="Link",
				insert_after="item_group",
				options="Product Tax Category",
				label="Product Tax Category",
			)
		],
	}
	create_custom_fields(custom_fields, update=update)


def add_permissions():
	doctype = "Product Tax Category"
	for role in (
		"Accounts Manager",
		"Accounts User",
		"System Manager",
		"Item Manager",
		"Stock Manager",
	):
		add_permission(doctype, role, 0)
		update_permission_property(doctype, role, 0, "write", 1)
		update_permission_property(doctype, role, 0, "create", 1)

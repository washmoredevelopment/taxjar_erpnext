# Copyright (c) 2026, Washmore Development, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TaxJarAccount(Document):
	def validate(self):
		self.validate_tax_calculation_settings()

	def validate_tax_calculation_settings(self):
		if not self.taxjar_calculate_tax and (self.taxjar_create_transactions or self.is_sandbox):
			frappe.throw(
				_(
					"Before enabling <b>Create Transaction</b> or <b>Sandbox Mode</b>, "
					"you need to check the <b>Enable Tax Calculation</b> box"
				)
			)

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

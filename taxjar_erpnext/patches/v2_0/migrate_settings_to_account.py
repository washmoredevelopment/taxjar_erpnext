# Copyright (c) 2024, Washmore Development and contributors
# For license information, please see license.txt

"""
Migration patch to convert existing TaxJar Settings (Single DocType)
to the new TaxJar Account (regular DocType with multi-company support).
"""

import frappe
from frappe import _


def execute():
	"""
	Migrate existing TaxJar Settings data to TaxJar Account.
	
	This patch:
	1. Checks if old TaxJar Settings data exists
	2. Creates a new TaxJar Account record for the configured company
	3. Copies all settings including API keys and nexus list
	"""
	# Check if TaxJar Settings table exists (from old installation)
	if not frappe.db.table_exists("tabTaxJar Settings"):
		return
	
	# Check if there's any data in the old settings
	try:
		settings_data = frappe.db.sql("""
			SELECT 
				company, taxjar_calculate_tax, is_sandbox, taxjar_create_transactions,
				api_key, sandbox_api_key, tax_account_head, shipping_account_head
			FROM `tabTaxJar Settings`
			LIMIT 1
		""", as_dict=True)
	except Exception:
		# Table might not exist or have different structure
		return
	
	if not settings_data:
		return
	
	settings = settings_data[0]
	
	# Skip if no company was configured
	if not settings.get("company"):
		frappe.log_error(
			"TaxJar Settings migration skipped: No company was configured in the old settings.",
			"TaxJar Migration"
		)
		return
	
	# Skip if TaxJar Account already exists for this company
	if frappe.db.exists("TaxJar Account", settings.get("company")):
		frappe.log_error(
			f"TaxJar Account already exists for {settings.get('company')}. Migration skipped.",
			"TaxJar Migration"
		)
		return
	
	# Get nexus data from old settings
	nexus_data = []
	try:
		nexus_data = frappe.db.sql("""
			SELECT region, region_code, country, country_code
			FROM `tabTaxJar Nexus`
			WHERE parent = 'TaxJar Settings' AND parenttype = 'TaxJar Settings'
		""", as_dict=True)
	except Exception:
		pass
	
	# Create new TaxJar Account
	try:
		doc = frappe.new_doc("TaxJar Account")
		doc.company = settings.get("company")
		doc.taxjar_calculate_tax = settings.get("taxjar_calculate_tax") or 0
		doc.is_sandbox = settings.get("is_sandbox") or 0
		doc.taxjar_create_transactions = settings.get("taxjar_create_transactions") or 0
		doc.tax_account_head = settings.get("tax_account_head")
		doc.shipping_account_head = settings.get("shipping_account_head")
		
		# Copy API keys (they're stored encrypted, need to copy the encrypted values)
		if settings.get("api_key"):
			doc.api_key = settings.get("api_key")
		if settings.get("sandbox_api_key"):
			doc.sandbox_api_key = settings.get("sandbox_api_key")
		
		# Copy nexus entries
		for nexus in nexus_data:
			doc.append("nexus", {
				"region": nexus.get("region"),
				"region_code": nexus.get("region_code"),
				"country": nexus.get("country"),
				"country_code": nexus.get("country_code"),
			})
		
		doc.flags.ignore_permissions = True
		doc.insert()
		
		frappe.db.commit()
		
		print(f"Successfully migrated TaxJar Settings to TaxJar Account for company: {settings.get('company')}")
		
	except Exception as e:
		frappe.log_error(
			f"Failed to migrate TaxJar Settings: {str(e)}",
			"TaxJar Migration Error"
		)

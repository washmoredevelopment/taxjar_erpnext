"""
TaxJar Integration for ERPNext - Multi-Company Support

This module handles tax calculation and transaction creation via TaxJar API,
with support for multiple companies each having their own TaxJar account.
"""

import traceback

import frappe
import taxjar
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.utils import cint, flt

from erpnext import get_region

SUPPORTED_COUNTRY_CODES = [
	"AT", "AU", "BE", "BG", "CA", "CY", "CZ", "DE", "DK", "EE",
	"ES", "FI", "FR", "GB", "GR", "HR", "HU", "IE", "IT", "LT",
	"LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK", "US",
]

SUPPORTED_STATE_CODES = [
	"AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
	"GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
	"MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
	"NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
	"SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]


def get_taxjar_account(company):
	"""
	Get TaxJar Account for a specific company.
	
	Args:
		company: The company name to look up
		
	Returns:
		TaxJar Account document if found and enabled, None otherwise
	"""
	if not company:
		return None
	
	account_name = frappe.db.get_value(
		"TaxJar Account",
		{"company": company, "taxjar_calculate_tax": 1}
	)
	
	if not account_name:
		return None
	
	return frappe.get_doc("TaxJar Account", account_name)


def get_client(company):
	"""
	Get TaxJar API client for a specific company.
	
	Args:
		company: The company name
		
	Returns:
		TaxJar client instance or None if not configured
	"""
	taxjar_account = get_taxjar_account(company)
	
	if not taxjar_account:
		return None
	
	if taxjar_account.is_sandbox:
		api_key = taxjar_account.get_password("sandbox_api_key") if taxjar_account.sandbox_api_key else None
		api_url = taxjar.SANDBOX_API_URL
	else:
		api_key = taxjar_account.get_password("api_key") if taxjar_account.api_key else None
		api_url = taxjar.DEFAULT_API_URL
	
	if api_key and api_url:
		client = taxjar.Client(api_key=api_key, api_url=api_url)
		client.set_api_config("headers", {"x-api-version": "2022-01-24"})
		return client
	
	return None


def create_transaction(doc, method):
	"""
	Create an order transaction in TaxJar on Sales Invoice submit.
	
	Args:
		doc: Sales Invoice document
		method: Hook method name
	"""
	taxjar_account = get_taxjar_account(doc.company)
	
	if not taxjar_account:
		return
	
	if not taxjar_account.taxjar_create_transactions:
		return
	
	client = get_client(doc.company)
	if not client:
		return
	
	TAX_ACCOUNT_HEAD = taxjar_account.tax_account_head
	sales_tax = sum([tax.tax_amount for tax in doc.taxes if tax.account_head == TAX_ACCOUNT_HEAD])
	
	if not sales_tax:
		return
	
	tax_dict = get_tax_data(doc, taxjar_account)
	if not tax_dict:
		return
	
	tax_dict["transaction_id"] = doc.name
	tax_dict["transaction_date"] = frappe.utils.today()
	tax_dict["sales_tax"] = sales_tax
	tax_dict["amount"] = doc.total + tax_dict["shipping"]
	
	try:
		if doc.is_return:
			client.create_refund(tax_dict)
		else:
			client.create_order(tax_dict)
	except taxjar.exceptions.TaxJarResponseError as err:
		doc_link = frappe.utils.get_link_to_form(doc.doctype, doc.name)
		frappe.throw(
			_("TaxJar transaction creation failed for {0}.<br><br>{1}").format(
				doc_link, sanitize_error_response(err)
			),
			title=_("TaxJar Transaction Error")
		)
	except Exception as ex:
		frappe.log_error(traceback.format_exc(), "TaxJar Transaction Error")


def delete_transaction(doc, method):
	"""
	Delete an existing TaxJar order transaction on Sales Invoice cancel.
	
	Args:
		doc: Sales Invoice document
		method: Hook method name
	"""
	taxjar_account = get_taxjar_account(doc.company)
	
	if not taxjar_account:
		return
	
	if not taxjar_account.taxjar_create_transactions:
		return
	
	client = get_client(doc.company)
	if not client:
		return
	
	try:
		client.delete_order(doc.name)
	except taxjar.exceptions.TaxJarResponseError:
		# Transaction may not exist in TaxJar, ignore
		pass


def notify_non_nexus_sales_order(doc, method):
	"""
	Create a ToDo notification when a Sales Order is submitted
	for a state without established nexus.
	
	This function is designed to fail silently - notification failures
	should never block Sales Order submission.
	
	Args:
		doc: Sales Order document
		method: Hook method name
	"""
	try:
		taxjar_account = get_taxjar_account(doc.company)
		
		if not taxjar_account:
			return
		
		if not taxjar_account.notify_on_non_nexus_sales:
			return
		
		if not taxjar_account.non_nexus_notification_user:
			return
		
		# Get tax data to determine destination state
		# Use a try-except since get_tax_data can throw errors
		try:
			tax_dict = get_tax_data(doc, taxjar_account)
		except Exception:
			# If we can't get tax data, we can't determine nexus status
			# Skip notification silently
			return
		
		if not tax_dict:
			return
		
		# Check if destination has nexus
		has_nexus = False
		for nexus in taxjar_account.nexus:
			if nexus.region_code == tax_dict["to_state"]:
				has_nexus = True
				break
		
		if has_nexus:
			return  # No notification needed
		
		# Create ToDo for the designated user
		destination_state = tax_dict.get("to_state", "Unknown")
		
		todo = frappe.get_doc({
			"doctype": "ToDo",
			"allocated_to": taxjar_account.non_nexus_notification_user,
			"reference_type": "Sales Order",
			"reference_name": doc.name,
			"description": (
				f"Sales Order {doc.name} has been submitted for {destination_state}, "
				f"a state without established sales tax nexus for {doc.company}.\n\n"
				f"Customer: {doc.customer_name}\n"
				f"Grand Total: {doc.currency} {doc.grand_total:,.2f}\n\n"
				f"It is recommended to evaluate your business presence in {destination_state} "
				f"and establish nexus for proper tax filings if applicable."
			),
			"status": "Open",
			"priority": "Medium",
			"date": frappe.utils.today(),
		})
		todo.insert(ignore_permissions=True)
	except Exception:
		# Log the error but don't block the Sales Order submission
		frappe.log_error(
			title="TaxJar Non-Nexus Notification Failed",
			message=f"Failed to create non-nexus notification for Sales Order {doc.name}"
		)


def get_tax_data(doc, taxjar_account=None):
	"""
	Build tax data dictionary for TaxJar API call.
	
	Args:
		doc: Sales document (Quotation, Sales Order, Sales Invoice)
		taxjar_account: TaxJar Account document (optional, will be fetched if not provided)
		
	Returns:
		Dictionary with tax calculation parameters or None
	"""
	if not taxjar_account:
		taxjar_account = get_taxjar_account(doc.company)
	
	if not taxjar_account:
		return None
	
	SHIP_ACCOUNT_HEAD = taxjar_account.shipping_account_head
	
	from_address = get_company_address_details(doc)
	if not from_address:
		return None
	
	from_shipping_state = from_address.get("state")
	from_country_code = frappe.db.get_value("Country", from_address.country, "code")
	if not from_country_code:
		return None
	from_country_code = from_country_code.upper()
	
	to_address = get_shipping_address_details(doc)
	if not to_address:
		return None
	
	to_shipping_state = to_address.get("state")
	to_country_code = frappe.db.get_value("Country", to_address.country, "code")
	if not to_country_code:
		return None
	to_country_code = to_country_code.upper()
	
	shipping = sum([tax.tax_amount for tax in doc.taxes if tax.account_head == SHIP_ACCOUNT_HEAD])
	
	line_items = [get_line_item_dict(item, doc.docstatus) for item in doc.items]
	
	if from_shipping_state not in SUPPORTED_STATE_CODES:
		from_shipping_state = get_state_code(from_address, "Company")
	
	if to_shipping_state not in SUPPORTED_STATE_CODES:
		to_shipping_state = get_state_code(to_address, "Shipping")
	
	tax_dict = {
		"from_country": from_country_code,
		"from_zip": from_address.pincode,
		"from_state": from_shipping_state,
		"from_city": from_address.city,
		"from_street": from_address.address_line1,
		"to_country": to_country_code,
		"to_zip": to_address.pincode,
		"to_city": to_address.city,
		"to_street": to_address.address_line1,
		"to_state": to_shipping_state,
		"shipping": shipping,
		"amount": doc.net_total,
		"plugin": "erpnext",
		"line_items": line_items,
	}
	return tax_dict


def get_state_code(address, location):
	"""
	Get ISO 3166-2 state code from address.
	
	Args:
		address: Address document
		location: Location type for error message ("Company" or "Shipping")
		
	Returns:
		State code string
	"""
	if address is not None:
		address_name = address.get("name") or "Unknown"
		address_link = frappe.utils.get_link_to_form("Address", address_name)
		
		state_code = get_iso_3166_2_state_code(address)
		if state_code not in SUPPORTED_STATE_CODES:
			frappe.throw(
				_("The state '{0}' in {1} Address {2} is not a supported US state.<br><br>"
				  "Please enter a valid 2-letter US state code.").format(
					address.get("state"), location, address_link
				),
				title=_("Unsupported State")
			)
	else:
		frappe.throw(
			_("No {0} Address found. Please ensure an address is set.").format(location),
			title=_("Missing Address")
		)
	
	return state_code


def get_line_item_dict(item, docstatus):
	"""
	Build line item dictionary for TaxJar API.
	
	Args:
		item: Sales document item row
		docstatus: Document status (0=Draft, 1=Submitted)
		
	Returns:
		Line item dictionary
	"""
	tax_dict = dict(
		id=item.get("idx"),
		quantity=item.get("qty"),
		unit_price=item.get("rate"),
		product_tax_code=item.get("product_tax_category"),
	)
	
	if docstatus == 1:
		tax_dict.update({"sales_tax": item.get("tax_collectable")})
	
	return tax_dict


def set_sales_tax(doc, method):
	"""
	Calculate and set sales tax on document validate.
	
	Args:
		doc: Sales document (Quotation, Sales Order, Sales Invoice)
		method: Hook method name
	"""
	taxjar_account = get_taxjar_account(doc.company)
	
	# Skip silently if no TaxJar Account configured for this company
	if not taxjar_account:
		return
	
	TAX_ACCOUNT_HEAD = taxjar_account.tax_account_head
	
	# Check if company is in United States
	if get_region(doc.company) != "United States":
		return
	
	if not doc.items:
		return
	
	if check_sales_tax_exemption(doc, taxjar_account):
		return
	
	tax_dict = get_tax_data(doc, taxjar_account)
	
	if not tax_dict:
		# Remove existing tax rows if address is changed from a taxable state/country
		setattr(doc, "taxes", [tax for tax in doc.taxes if tax.account_head != TAX_ACCOUNT_HEAD])
		for item in doc.get("items"):
			item.tax_collectable = flt(0)
			item.taxable_amount = flt(0)
		return
	
	# Check if delivering within a nexus
	has_nexus = check_for_nexus(doc, tax_dict, taxjar_account, skip_cleanup=True)
	
	if not has_nexus:
		# For Quotations, allow tax calculation if setting is enabled
		if doc.doctype == "Quotation" and taxjar_account.calculate_tax_for_all_states:
			pass  # Continue to calculate tax
		else:
			# Clean up any existing TaxJar tax rows
			cleanup_taxjar_rows(doc, taxjar_account)
			return
	
	tax_data = validate_tax_request(doc, tax_dict)
	
	# Determine if we need to use rate fallback for non-nexus quotes
	is_non_nexus_quote = (
		doc.doctype == "Quotation"
		and not has_nexus
		and taxjar_account.calculate_tax_for_all_states
	)
	
	# Calculate tax amount
	tax_amount = 0
	use_rate_fallback = False
	
	if tax_data is not None and tax_data.amount_to_collect > 0:
		# Normal case: TaxJar returned a tax amount
		tax_amount = tax_data.amount_to_collect
	elif is_non_nexus_quote:
		# Fallback: Use rates_for_location for non-nexus quotes
		tax_rate = get_tax_rate_for_location(doc, tax_dict)
		if tax_rate > 0:
			# Calculate tax on net_total (taxable amount before tax)
			tax_amount = flt(doc.net_total * tax_rate, 2)
			use_rate_fallback = True
	
	if not tax_amount:
		# No tax to collect - remove any existing TaxJar tax rows and reset item fields
		setattr(doc, "taxes", [tax for tax in doc.taxes if tax.account_head != TAX_ACCOUNT_HEAD])
		for item in doc.get("items"):
			item.tax_collectable = flt(0)
			item.taxable_amount = flt(0)
		return
	
	# Determine description based on source
	if use_rate_fallback:
		destination_state = tax_dict.get("to_state", "")
		description = f"Estimated Sales Tax - {destination_state} (Nexus Not Established)"
	elif is_non_nexus_quote:
		description = "Estimated Sales Tax (Nexus Not Established)"
	else:
		description = "Sales Tax"
	
	# Loop through tax rows for existing Sales Tax entry
	# If none are found, add a row with the tax amount
	tax_row_found = False
	for tax in doc.taxes:
		if tax.account_head == TAX_ACCOUNT_HEAD:
			tax.tax_amount = tax_amount
			tax.description = description
			tax_row_found = True
			doc.run_method("calculate_taxes_and_totals")
			break
	
	if not tax_row_found:
		doc.append(
			"taxes",
			{
				"charge_type": "Actual",
				"description": description,
				"account_head": TAX_ACCOUNT_HEAD,
				"tax_amount": tax_amount,
			},
		)
	
	# Only assign per-item tax breakdown if we have it from tax_for_order
	# (rates_for_location doesn't provide line-item breakdown)
	if tax_data and tax_data.amount_to_collect > 0 and hasattr(tax_data, 'breakdown'):
		for item in tax_data.breakdown.line_items:
			doc.get("items")[cint(item.id) - 1].tax_collectable = item.tax_collectable
			doc.get("items")[cint(item.id) - 1].taxable_amount = item.taxable_amount
	else:
		# Clear stale line-item tax data when:
		# - Using rate fallback (rates_for_location doesn't provide per-item breakdown)
		# - tax_for_order returned data but without breakdown attribute
		for item in doc.get("items"):
			item.tax_collectable = flt(0)
			item.taxable_amount = flt(0)
	
	doc.run_method("calculate_taxes_and_totals")


def cleanup_taxjar_rows(doc, taxjar_account):
	"""
	Remove TaxJar tax rows and reset item tax fields.
	
	Args:
		doc: Sales document
		taxjar_account: TaxJar Account document
	"""
	TAX_ACCOUNT_HEAD = taxjar_account.tax_account_head
	
	for item in doc.get("items"):
		item.tax_collectable = flt(0)
		item.taxable_amount = flt(0)
	
	for tax in list(doc.taxes):
		if tax.account_head == TAX_ACCOUNT_HEAD:
			doc.taxes.remove(tax)


def check_for_nexus(doc, tax_dict, taxjar_account, skip_cleanup=False):
	"""
	Check if the destination state has nexus configured for this company.
	
	Args:
		doc: Sales document
		tax_dict: Tax calculation dictionary
		taxjar_account: TaxJar Account document
		skip_cleanup: If True, don't remove tax rows (caller will handle)
		
	Returns:
		True if nexus exists, False otherwise
	"""
	# Check nexus in the company's TaxJar Account
	has_nexus = False
	for nexus in taxjar_account.nexus:
		if nexus.region_code == tax_dict["to_state"]:
			has_nexus = True
			break
	
	if not has_nexus and not skip_cleanup:
		cleanup_taxjar_rows(doc, taxjar_account)
	
	return has_nexus


def check_sales_tax_exemption(doc, taxjar_account):
	"""
	Check if the document or customer is exempt from sales tax.
	
	Args:
		doc: Sales document
		taxjar_account: TaxJar Account document
		
	Returns:
		True if exempt, False otherwise
	"""
	TAX_ACCOUNT_HEAD = taxjar_account.tax_account_head
	
	# Get customer name:
	# - Sales Order/Invoice: use customer field directly
	# - Quotation: use party_name only if quotation_to == "Customer" (not Lead)
	customer_name = getattr(doc, "customer", None)
	if not customer_name and doc.doctype == "Quotation":
		# Only treat party_name as a Customer if quotation_to is "Customer"
		quotation_to = getattr(doc, "quotation_to", None)
		if quotation_to == "Customer":
			customer_name = getattr(doc, "party_name", None)
	
	# Check document-level exemption first, then customer-level exemption
	sales_tax_exempted = (
		hasattr(doc, "exempt_from_sales_tax")
		and doc.exempt_from_sales_tax
	)
	
	# If not exempt at document level, check customer level
	if not sales_tax_exempted and customer_name:
		if frappe.db.has_column("Customer", "exempt_from_sales_tax"):
			sales_tax_exempted = frappe.db.get_value(
				"Customer", customer_name, "exempt_from_sales_tax"
			)
	
	if sales_tax_exempted:
		for tax in doc.taxes:
			if tax.account_head == TAX_ACCOUNT_HEAD:
				tax.tax_amount = 0
				break
		doc.run_method("calculate_taxes_and_totals")
		return True
	
	return False


def validate_tax_request(doc, tax_dict):
	"""
	Call TaxJar API to calculate tax for an order.
	
	Args:
		doc: Sales document (Quotation, Sales Order, Sales Invoice)
		tax_dict: Tax calculation dictionary
		
	Returns:
		TaxJar tax response or None
	"""
	client = get_client(doc.company)
	
	if not client:
		return None
	
	try:
		tax_data = client.tax_for_order(tax_dict)
	except taxjar.exceptions.TaxJarResponseError as err:
		doc_link = frappe.utils.get_link_to_form(doc.doctype, doc.name)
		frappe.throw(
			_("TaxJar tax calculation failed for {0}.<br><br>{1}").format(
				doc_link, sanitize_error_response(err)
			),
			title=_("TaxJar Calculation Error")
		)
	else:
		return tax_data


def get_tax_rate_for_location(doc, tax_dict):
	"""
	Get tax rate for a location using TaxJar's rates_for_location API.
	
	This is used for non-nexus states where tax_for_order returns 0.
	Note: This does NOT apply product tax category exemptions - it returns
	the general combined rate for the location.
	
	Args:
		doc: Sales document
		tax_dict: Tax calculation dictionary with address details
		
	Returns:
		Combined tax rate as decimal (e.g., 0.0825 for 8.25%) or 0 on failure
	"""
	client = get_client(doc.company)
	
	if not client:
		return 0
	
	try:
		# Build location details for more accurate rate lookup
		location_details = {
			"city": tax_dict.get("to_city"),
			"state": tax_dict.get("to_state"),
			"country": tax_dict.get("to_country"),
		}
		
		# Add street address if available for most accurate rate
		if tax_dict.get("to_street"):
			location_details["street"] = tax_dict.get("to_street")
		
		rates = client.rates_for_location(tax_dict.get("to_zip"), location_details)
		
		# combined_rate includes state + county + city + special district rates
		# Ensure we always return a number, never None
		if rates and rates.combined_rate is not None:
			return rates.combined_rate
		return 0
		
	except Exception as err:
		# Log error but don't block the document
		frappe.log_error(
			title="TaxJar Rate Lookup Failed",
			message=f"Failed to get tax rate for {tax_dict.get('to_zip')}: {str(err)}"
		)
		return 0


def get_company_address_details(doc):
	"""
	Return company address details for the document's company.
	
	Args:
		doc: Sales document
		
	Returns:
		Address document or None
	"""
	company_address_data = get_company_address(doc.company)
	
	if not company_address_data or not company_address_data.company_address:
		company_link = frappe.utils.get_link_to_form("Company", doc.company)
		frappe.throw(
			_("No default address found for company {0}.<br><br>"
			  "Please set a default company address in the Company settings.").format(company_link),
			title=_("Missing Company Address")
		)
	
	company_address = frappe.get_doc("Address", company_address_data.company_address)
	return company_address


def get_shipping_address_details(doc):
	"""
	Return customer shipping address details.
	
	Args:
		doc: Sales document
		
	Returns:
		Address document
	"""
	if doc.shipping_address_name:
		shipping_address = frappe.get_doc("Address", doc.shipping_address_name)
	elif doc.customer_address:
		shipping_address = frappe.get_doc("Address", doc.customer_address)
	else:
		shipping_address = get_company_address_details(doc)
	
	return shipping_address


def get_iso_3166_2_state_code(address):
	"""
	Get ISO 3166-2 state code from address state field.
	
	Args:
		address: Address document
		
	Returns:
		State code string
	"""
	import pycountry
	
	country_code = frappe.db.get_value("Country", address.get("country"), "code")
	
	address_name = address.get("name") or "Unknown"
	address_link = frappe.utils.get_link_to_form("Address", address_name)
	
	state = address.get("state")
	if not state:
		frappe.throw(
			_("State is required in address {0}.<br><br>"
			  "Please open the address and add a valid US state code (e.g., TX, CA, FL).").format(address_link),
			title=_("Missing State in Address")
		)
	
	state = state.upper().strip()
	
	error_message = _(
		"{0} is not a valid state in address {1}.<br><br>"
		"Check for typos or enter the ISO code for your state (e.g., TX, CA, FL)."
	).format(state, address_link)
	
	# The max length for ISO state codes is 3, excluding the country code
	if len(state) <= 3:
		# PyCountry returns state code as {country_code}-{state-code} (e.g. US-FL)
		address_state = (country_code + "-" + state).upper()
		
		states = pycountry.subdivisions.get(country_code=country_code.upper())
		states = [pystate.code for pystate in states]
		
		if address_state in states:
			return state
		
		frappe.throw(_(error_message), title=_("Invalid State Code"))
	else:
		try:
			lookup_state = pycountry.subdivisions.lookup(state)
		except LookupError:
			frappe.throw(_(error_message), title=_("Invalid State"))
		else:
			return lookup_state.code.split("-")[1]


def sanitize_error_response(response):
	"""
	Sanitize TaxJar error response for display.
	
	Args:
		response: TaxJar error response
		
	Returns:
		Sanitized error message string
	"""
	response = response.full_response.get("detail")
	response = response.replace("_", " ")
	
	sanitized_responses = {
		"to zip": "Zipcode",
		"to city": "City",
		"to state": "State",
		"to country": "Country",
	}
	
	for k, v in sanitized_responses.items():
		response = response.replace(k, v)
	
	return response

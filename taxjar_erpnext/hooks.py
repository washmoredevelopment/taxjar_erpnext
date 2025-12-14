from . import __version__ as app_version

app_name = "taxjar_erpnext"
app_title = "TaxJar ERPNext"
app_publisher = "Washmore Development"
app_description = "TaxJar Integration with ERPNext - Multi-Company Support"
app_email = "dev@washmore.app"
app_license = "MIT"

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		"on_submit": "taxjar_erpnext.taxjar_erpnext.taxjar_erpnext.create_transaction",
		"on_cancel": "taxjar_erpnext.taxjar_erpnext.taxjar_erpnext.delete_transaction"
	},
	("Quotation", "Sales Order", "Sales Invoice"): {
		"validate": ["taxjar_erpnext.taxjar_erpnext.taxjar_erpnext.set_sales_tax"]
	},
}

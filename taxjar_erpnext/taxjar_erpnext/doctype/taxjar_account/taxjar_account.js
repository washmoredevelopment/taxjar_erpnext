// Copyright (c) 2024, Washmore Development and contributors
// For license information, please see license.txt

frappe.ui.form.on("TaxJar Account", {
  setup: function (frm) {
    // Filter account fields by company only
    frm.set_query("tax_account_head", function () {
      return {
        filters: {
          company: frm.doc.company,
          is_group: 0,
        },
      };
    });

    frm.set_query("shipping_account_head", function () {
      return {
        filters: {
          company: frm.doc.company,
          is_group: 0,
        },
      };
    });
  },

  refresh: function (frm) {
    // Add Update Nexus List button
    if (!frm.is_new() && frm.doc.taxjar_calculate_tax) {
      frm.add_custom_button(__("Update Nexus List"), function () {
        frm.call({
          doc: frm.doc,
          method: "update_nexus_list",
          freeze: true,
          freeze_message: __("Fetching nexus regions from TaxJar..."),
        });
      });
    }
  },

  company: function (frm) {
    // Clear account fields when company changes
    if (frm.doc.company) {
      frm.set_value("tax_account_head", "");
      frm.set_value("shipping_account_head", "");
    }
  },

  is_sandbox: function (frm) {
    // Toggle API key requirements based on sandbox mode
    frm.toggle_reqd(
      "api_key",
      frm.doc.taxjar_calculate_tax && !frm.doc.is_sandbox,
    );
    frm.toggle_reqd(
      "sandbox_api_key",
      frm.doc.taxjar_calculate_tax && frm.doc.is_sandbox,
    );
  },

  taxjar_calculate_tax: function (frm) {
    // Toggle requirements when tax calculation is enabled/disabled
    frm.toggle_reqd(
      "api_key",
      frm.doc.taxjar_calculate_tax && !frm.doc.is_sandbox,
    );
    frm.toggle_reqd(
      "sandbox_api_key",
      frm.doc.taxjar_calculate_tax && frm.doc.is_sandbox,
    );
    frm.toggle_reqd("tax_account_head", frm.doc.taxjar_calculate_tax);
    frm.toggle_reqd("shipping_account_head", frm.doc.taxjar_calculate_tax);
  },
});

<!-- Copyright (c) 2026, Washmore Development, AgriTheory and contributors
For license information, please see license.txt-->

# TaxJar ERPNext

<div class="byline">
  Tyler Matteson 2026-06-23
</div>


TaxJar ERPNext connects [ERPNext](https://erpnext.com/) selling documents to [TaxJar](https://www.taxjar.com/) so US-based companies can calculate sales tax at quote, order, and invoice time without maintaining rate tables by hand. The integration respects nexus, product tax categories, and exemptions, then optionally reports completed sales back to TaxJar for compliance workflows such as AutoFile.

Each company that uses TaxJar gets its own **TaxJar Account**: API credentials, nexus list, and GL mapping stay separate in multi-company sites. Tax is calculated on **Quotation**, **Sales Order**, and **Sales Invoice** when the ship-to destination is in a nexus state. Optional features extend that baseline—estimated tax on quotes for non-nexus states, ToDo alerts when orders ship outside nexus, and transaction sync when invoices are submitted.

This documentation is the user guide and technical reference for installing, configuring, and operating the app. Start with [Setup](setup.md) to install and configure a site; use [Integration](integration.md) for hooks, data model, and API behavior; see [Troubleshooting and contributing](troubleshooting.md) for common failures, development, and licensing.

## In this section

- [Setup](setup.md) — Installation, prerequisites, TaxJar Account configuration, and what to expect on each selling document.
- [Integration](integration.md) — Hooks, DocTypes, custom fields, calculation pipeline, transaction sync, and limitations.
- [Troubleshooting and contributing](troubleshooting.md) — Symptom checklist, running tests, license, and acknowledgements.

---

## Development and testing

- Hooks entry point: [`hooks.py`](../taxjar_erpnext/hooks.py).
- Whitelisted DocType method: `TaxJar Account.update_nexus_list`.
- Integration tests: [`taxjar_erpnext/tests/`](../taxjar_erpnext/tests/) (`test_sales_tax.py`, `test_taxjar_account.py`). Fixture loading uses [test_utils](https://github.com/agritheory/test_utils).
- Load fixture data once on a test site, then run pytest from the bench:

  ```bash
  bench execute 'taxjar_erpnext.tests.setup.before_test'
  cd frappe-bench && source env/bin/activate && pytest apps/taxjar_erpnext/ --disable-warnings -s -v
  ```

- CI: [`.github/workflows/`](../.github/workflows/) (lint, pytest, release, and related workflows).

---

## License and acknowledgements

**License:** This project is distributed under the MIT License. The full text is in the repository `license.txt` at the app root (same folder as `pyproject.toml`).

**Acknowledgements:** This project is a fork of the original [TaxJar Integration](https://github.com/frappe/taxjar_integration) developed by [Frappe](https://frappe.io/). Thanks to the Frappe team and all contributors to the upstream project.
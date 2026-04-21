<!-- Copyright (c) 2026, Washmore Development, AgriTheory and contributors
For license information, please see license.txt-->

# Troubleshooting and contributing

[← Documentation index](index.md) · [Setup](setup.md) · [Integration](integration.md)

## Troubleshooting

| Symptom | Things to check |
|--------|-------------------|
| No tax calculated | Company region United States; Enable Tax Calculation; items present; not exempt; addresses complete; nexus (unless quotation plus estimate-all-states). |
| Tax cleared after address change | `get_tax_data` returned `None` (for example missing address or country code); integration removes TaxJar tax rows. |
| Missing Company Address | Set default company address on Company. |
| State or ZIP errors | Shipping and company addresses: valid state for country; US state codes where enforced. |
| TaxJar API errors on save | TaxJar Calculation Error vs TaxJar Transaction Error titles; message body is sanitized API `detail`. |
| Transactions not created | Create TaxJar Transaction; non-zero tax on Tax Account Head; live vs sandbox keys and Sandbox Mode alignment. |
| Nexus notifications missing | Notify checkbox; Notification Recipient; destination must be outside nexus; failures only in Error Log. |
| Nexus list empty | Save TaxJar Account with valid keys, then Update Nexus List. |

---

## Development and testing

- Hooks entry point: [`hooks.py`](../taxjar_erpnext/hooks.py).
- Whitelisted DocType method: `TaxJar Account.update_nexus_list`.
- Example tests: [`test_product_tax_category.py`](../taxjar_erpnext/taxjar_erpnext/doctype/product_tax_category/test_product_tax_category.py).
- CI: [`.github/workflows/`](../.github/workflows/) (lint, pytest, release, and related workflows).

---

## License and acknowledgements

**License:** This project is distributed under the MIT License. The full text is in the repository `license.txt` at the app root (same folder as `pyproject.toml`).

**Acknowledgements:** This project is a fork of the original [TaxJar Integration](https://github.com/frappe/taxjar_integration) developed by [Frappe](https://frappe.io/). Thanks to the Frappe team and all contributors to the upstream project.

<!-- Copyright (c) 2026, Washmore Development, AgriTheory and contributors
For license information, please see license.txt-->

# Setup

<div class="byline">
  Tyler Matteson 2026-04-21
</div>


[← Documentation index](index.md)

## Overview

TaxJar ERPNext connects ERPNext to [TaxJar](https://www.taxjar.com/) for automated sales tax calculation and reporting. It handles tax rates, nexus management, and product tax categories to support compliance workflows.

### Tax calculation

- Automatic sales tax on Quotation, Sales Order, and Sales Invoice (United States companies only; see [Scope](#scope-and-stack) below).
- Nexus-aware: tax for destinations where nexus is configured on the TaxJar Account.
- Product tax categories for different rates by product type (set per company on Item Default; see [Product tax categories](#product-tax-categories)).
- Sales tax exemption at document or customer level (requires ERPNext United States regional fields).
- Line-item breakdown with `tax_collectable` and `taxable_amount` on **Sales Invoice** lines when TaxJar returns a full breakdown.

### Multi-company

- Separate TaxJar Account per company: own API credentials, nexus list, and GL account mapping.
- Sandbox mode for testing against the TaxJar sandbox.

### Non-nexus quotation estimates (optional)

- Estimate sales tax on Quotations for states without nexus when Calculate Estimated Tax for All States is enabled on the TaxJar Account.
- Uses TaxJar `rates_for_location` when the primary calculation does not return collectable tax for that scenario.
- Tax rows use the description Estimated Sales Tax so they are distinct from nexus-backed Sales Tax.
- Estimates are designed so quotes do not undercharge; they can be higher than actual tax because product exemptions are not applied on the rate fallback path.

### Non-nexus Sales Order notifications (optional)

- When enabled, submitting a Sales Order for a state without nexus creates a ToDo for a chosen user with order details, to help watch nexus thresholds.

### Transaction reporting (optional)

- Create TaxJar Transaction on the TaxJar Account: on Sales Invoice submit, creates an order in TaxJar; return invoices create refunds; cancel removes the order in TaxJar.
- Supports syncing into TaxJar for reporting and services such as AutoFile.

---

## Scope and stack

**Scope (tax calculation):** Sales tax is calculated only when the company’s region is the United States. The integration checks `get_region(company) == "United States"` in `set_sales_tax` before calling TaxJar ([`taxjar_erpnext.py`](../taxjar_erpnext/taxjar_erpnext/taxjar_erpnext.py)).

**Upstream:** This app is a fork of Frappe’s [TaxJar Integration](https://github.com/frappe/taxjar_integration). License and acknowledgements are in [Troubleshooting and contributing](troubleshooting.md).

| Component | Notes |
|-----------|--------|
| Frappe / ERPNext | v15.x (`pyproject.toml`, `[tool.bench.frappe-dependencies]`) |
| Python `taxjar` client | Project dependencies |
| `pycountry` | State and subdivision resolution for addresses |
| TaxJar API version | Request header `x-api-version: 2022-01-24` in `get_client` ([`taxjar_erpnext.py`](../taxjar_erpnext/taxjar_erpnext/taxjar_erpnext.py)) |

---

## Installation

- Go to the bench directory (commonly `frappe-bench`):

  ```bash
  cd frappe-bench
  ```

- Fetch the app:

  ```bash
  bench get-app https://github.com/washmoredevelopment/taxjar_erpnext.git
  ```

- Install it on the site (replace the site name with yours):

  ```bash
  bench --site your-site.localhost install-app taxjar_erpnext
  ```

- Run migrations:

  ```bash
  bench --site your-site.localhost migrate
  ```

---

## Prerequisites for tax behavior

- TaxJar Account per company with Enable Tax Calculation checked. The resolver `get_taxjar_account` only returns accounts where `taxjar_calculate_tax` is enabled; the same lookup is used for the API client and transaction hooks.
- Default company address: `set_sales_tax` and `get_tax_data` resolve the ship-from address via `get_company_address`. If none is set, users see a missing company address error ([`get_company_address_details`](../taxjar_erpnext/taxjar_erpnext/taxjar_erpnext.py)).
- Destination address: prefer Shipping Address on the document; otherwise Customer Address; if neither is set, the company address is used as a fallback ([`get_shipping_address_details`](../taxjar_erpnext/taxjar_erpnext/taxjar_erpnext.py)).
- Valid state data: states must resolve to supported codes (see [Limitations](integration.md#limitations-and-operational-notes) on the integration page). Address validation uses `pycountry` in `get_iso_3166_2_state_code`.
- Sales tax exemption fields: document and customer `exempt_from_sales_tax` come from ERPNext’s United States regional setup (`erpnext.regional.united_states.setup`). Run that setup (or install ERPNext with US regional data) before relying on exemption checks.

---

## Behavior by document type

| Scenario | Quotation | Sales Order | Sales Invoice |
|----------|-----------|-------------|---------------|
| Nexus destination | Sales Tax calculated | Sales Tax calculated | Sales Tax calculated; line breakdown on invoice rows |
| Non-nexus destination | Estimated Sales Tax when enabled | No tax | No tax |
| Non-nexus notification | — | ToDo when enabled | — |
| TaxJar transaction sync | — | — | On submit / cancel when enabled |

See [Integration](integration.md#behavior-by-document-type) for hook-level detail.

---

## Configuration

### Basic setup

- Open TaxJar Account in ERPNext.
- Create a TaxJar Account for each Company that will use TaxJar.
- Enable **Enable Tax Calculation** first, then enter Live API Key or enable Sandbox Mode and enter Sandbox API Key. Sandbox Mode and Create TaxJar Transaction cannot be saved unless Enable Tax Calculation is checked.
- Set Tax Account Head and Shipping Account Head to the correct company accounts. The form only lists non-group accounts for that company ([`taxjar_account.js`](../taxjar_erpnext/taxjar_erpnext/doctype/taxjar_account/taxjar_account.js)).

The integration reads the selling document’s taxes table: amounts on the row whose account is Tax Account Head are treated as sales tax for TaxJar and for transaction sync. Amounts on the row whose account is Shipping Account Head are treated as shipping in the TaxJar payload.

Example T-account for a simple taxable sale (illustrative amounts; the Tax Account Head line is the GL account chosen on the TaxJar Account):

| Account | Party | Stock Ledger | Debit | Credit |
| :--------| :----: | :------------: | -----: | ------: |
| Debtors | Customer A | | $108.00 | |
| Sales | | | | $100.00 |
| Sales Tax Payable (Tax Account Head) | | | | $8.00 |

- Save the TaxJar Account, then click Update Nexus List to load nexus regions from TaxJar into the read-only child table (`update_nexus_list` in [`taxjar_account.py`](../taxjar_erpnext/taxjar_erpnext/doctype/taxjar_account/taxjar_account.py)).
- Optionally enable Create TaxJar Transaction so submitted Sales Invoices sync to TaxJar.

### Non-nexus state settings

For tax estimates on Quotations in states where there is no nexus:

- Enable Calculate Estimated Tax for All States on the TaxJar Account. Quotations can show estimated tax from location-based rates. Product exemptions are not applied on the fallback path; quoted tax may be higher than what would be collected on a real order.
- Optionally enable Notify User on Non-Nexus Sales Orders and choose a Notification Recipient. A ToDo is created when a Sales Order is submitted for a non-nexus destination.

### Product tax categories

- Open the Product Tax Category list. Categories are seeded on app install and when tax calculation is first enabled on a TaxJar Account (if the list is empty).
- Add or adjust rows so Product Tax Code matches TaxJar’s product tax codes.
- On each Item, open **Item Defaults** and set **Product Tax Category** for each company that sells the item. This is the primary path for multi-company setups; the Item-level field is optional.
- Different product tax codes on the same document (for example taxable and exempt lines) are supported; TaxJar may return tax on some lines only.

For hook timing, nexus logic, and API details, see [Integration](integration.md).

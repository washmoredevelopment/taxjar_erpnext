<!-- Copyright (c) 2026, Washmore Development, AgriTheory and contributors
For license information, please see license.txt-->

# Setup

<div class="byline">
  Tyler Matteson 2026-06-23
</div>


[← Documentation index](index.md)

This page covers installation and day-to-day configuration. For hooks, code paths, and API behavior, see [Integration](integration.md).

---

## Requirements

- **ERPNext v15** with a **United States** company. Tax is calculated only for US companies; other regions are ignored even if a TaxJar Account exists.
- A [TaxJar](https://www.taxjar.com/) account with Live or Sandbox API keys.
- ERPNext **United States regional setup** applied on the site if you rely on sales tax exemption fields on Customer or selling documents.

This app is a fork of Frappe’s [TaxJar Integration](https://github.com/frappe/taxjar_integration). License and acknowledgements are in [Troubleshooting and contributing](troubleshooting.md).

---

## Installation

From your bench directory (commonly `frappe-bench`):

```bash
bench get-app https://github.com/washmoredevelopment/taxjar_erpnext.git
bench --site your-site.localhost install-app taxjar_erpnext
bench --site your-site.localhost migrate
```

---

## Before you configure

Complete these on each company that will use TaxJar:

| Requirement | Where in ERPNext |
|-------------|------------------|
| TaxJar Account with **Enable Tax Calculation** | TaxJar Account (one per company) |
| Default **company address** (ship-from) | Company |
| **Shipping address** on selling documents (or customer address as fallback) | Quotation / Sales Order / Sales Invoice |
| **Tax Account Head** and **Shipping Account Head** GL accounts | TaxJar Account |
| **Product Tax Category** on item defaults | Item → Item Defaults (per company) |
| Nexus list synced from TaxJar | TaxJar Account → **Update Nexus List** |

Without a company address or a resolvable destination address, tax calculation stops and any existing TaxJar tax row is removed.

---

## What to expect by document type

| Scenario | Quotation | Sales Order | Sales Invoice |
|----------|-----------|-------------|---------------|
| Ship-to in a **nexus** state | **Sales Tax** row | **Sales Tax** row | **Sales Tax** row; per-line amounts on invoice lines when TaxJar provides a breakdown |
| Ship-to **outside nexus** | **Estimated Sales Tax** when [Calculate Estimated Tax for All States](#optional-non-nexus-features) is enabled; otherwise no tax | No tax | No tax |
| Non-nexus alert | — | ToDo for [Notification Recipient](#optional-non-nexus-features) when enabled | — |
| Sync to TaxJar | — | — | Order or refund on submit; delete on cancel when [Create TaxJar Transaction](#taxjar-account) is enabled |

**Mixed carts:** lines with different product tax categories on one document are supported. TaxJar may collect tax on some lines only; the document tax row shows the total.

---

## TaxJar Account

Open **TaxJar Account** and create one record per company.

1. Select the **Company**.
2. Check **Enable Tax Calculation** (required before any other TaxJar feature can be saved).
3. Enter credentials:
   - Live: **Live API Key**
   - Testing: enable **Sandbox Mode** and enter **Sandbox API Key**
4. Set **Tax Account Head** and **Shipping Account Head** to non-group accounts for that company. The integration reads the selling document’s taxes table: the row matching Tax Account Head is sales tax; the row matching Shipping Account Head is shipping in the TaxJar payload.
5. Save, then click **Update Nexus List** to load nexus regions into the read-only child table.
6. Optionally enable **Create TaxJar Transaction** to push submitted Sales Invoices to TaxJar.

Example posting for a simple taxable sale (Tax Account Head = Sales Tax Payable):

| Account | Party | Debit | Credit |
| :-------- | :----: | -----: | ------: |
| Debtors | Customer A | $108.00 | |
| Sales | | | $100.00 |
| Sales Tax Payable | | | $8.00 |

---

## Optional non-nexus features

Both settings are on the TaxJar Account form under **Non-Nexus State Settings**.

**Calculate Estimated Tax for All States**

- Applies to **Quotations** only.
- Shows **Estimated Sales Tax** for destinations outside your nexus list.
- Uses general location rates; product exemptions are **not** applied. Quoted tax may be **higher** than tax on a real order so quotes do not undercharge.

**Notify User on Non-Nexus Sales Orders**

- When a **Sales Order** is submitted to a state without nexus, creates a **ToDo** for the **Notification Recipient** with order details.
- Failures are logged only; submission is never blocked.

---

## Product tax categories

1. Open **Product Tax Category**. Default categories are created on app install and when tax calculation is first enabled on a TaxJar Account (if the list is empty).
2. Ensure **Product Tax Code** values match your TaxJar product tax codes.
3. On each **Item**, open **Item Defaults** and set **Product Tax Category** for every company that sells the item. Use Item Defaults for multi-company sites; the Item-level field is optional.

On **Sales Invoice**, the integration fills blank line categories from the item default before calling TaxJar.

---

## Next steps

- [Integration](integration.md) — hooks, DocTypes, custom fields, calculation pipeline, and limitations.
- [Troubleshooting and contributing](troubleshooting.md) — when tax or transactions do not behave as expected.

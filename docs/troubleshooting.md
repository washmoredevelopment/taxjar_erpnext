<!-- Copyright (c) 2026, Washmore Development, AgriTheory and contributors
For license information, please see license.txt-->

# Troubleshooting and contributing

<div class="byline">
  Tyler Matteson 2026-06-23
</div>


[← Documentation index](index.md) · [Setup](setup.md) · [Integration](integration.md)

## Troubleshooting

| Symptom | Things to check |
|--------|-------------------|
| No tax calculated | Company region United States; Enable Tax Calculation; items present; not exempt; addresses complete; nexus (unless quotation plus estimate-all-states). |
| Exemption ignored | ERPNext US regional setup installed; `exempt_from_sales_tax` on document or Customer. |
| Tax cleared after address change | `get_tax_data` returned `None` (for example missing address or country code); integration removes TaxJar tax rows. |
| Missing Company Address | Set default company address on Company. |
| State or ZIP errors | Shipping and company addresses: valid state for country; US state codes where enforced. |
| TaxJar API errors on save | TaxJar Calculation Error vs TaxJar Transaction Error titles; message body is sanitized API `detail`. |
| Transactions not created | Create TaxJar Transaction; non-zero tax on Tax Account Head; live vs sandbox keys and Sandbox Mode alignment. |
| Nexus notifications missing | Notify checkbox; Notification Recipient; destination must be outside nexus; failures only in Error Log. |
| Nexus list empty | Save TaxJar Account with valid keys, then Update Nexus List. |


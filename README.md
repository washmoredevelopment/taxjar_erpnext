<!-- Copyright (c) 2026, Washmore Development and contributors
For license information, please see license.txt-->

<div align="center" markdown="1">

<a href="https://github.com/washmoredevelopment/taxjar_erpnext">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./.github/assets/taxjar-dark.png">
    <img alt="TaxJar" src="./.github/assets/taxjar-light.png" width="200">
  </picture>
</a>

# TaxJar Integration for ERPNext

**Seamless sales tax calculation, remittance, and reporting for ERPNext**

[![MIT License][license-shield]][license-url]

<p align="center">
  <br />
  <a href="https://github.com/washmoredevelopment/taxjar_erpnext/issues/new?labels=bug">Report Bug</a>
  ·
  <a href="https://github.com/washmoredevelopment/taxjar_erpnext/issues/new?labels=enhancement">Request Feature</a>
</p>

</div>

<a id="readme-top"></a>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#configuration">Configuration</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
    <li><a href="#license">License</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

TaxJar Integration connects your ERPNext instance with [TaxJar](https://www.taxjar.com/) for automated sales tax calculation and reporting. It handles tax rates, nexus management, and product tax categories to ensure accurate tax compliance.

### Features

**Tax Calculation**
- Automatic sales tax calculation on Quotations, Sales Orders, and Sales Invoices
- Nexus-aware — calculates tax for states where you have nexus configured
- Product tax categories for different tax rates based on product type
- Sales tax exemption support at document or customer level
- Line-item tax breakdown with `tax_collectable` and `taxable_amount` per item

**Multi-Company Support**
- Separate TaxJar accounts per company
- Independent API credentials, nexus lists, and account mappings
- Sandbox mode for testing

**Non-Nexus Quotation Estimates**
- Optional non-nexus calculations.
- Calculate estimated sales tax for Quotations even in states without nexus
- Uses TaxJar's `rates_for_location` API for accurate location-based rates
- Tax rows labeled as "Estimated Sales Tax" to distinguish from regular tax calculations
- Ensures quotes never undercharge (estimates may be higher than actual tax due to exemptions not being applied)
- _Enable via "Calculate Estimated Tax for All States" in TaxJar Account settings_

**Non-Nexus Sales Notifications**
- Get notified when Sales Orders are submitted for states without nexus
- Creates a ToDo assigned to a designated user with order details
- Helps track potential nexus threshold triggers
- _Enable via "Notify User on Non-Nexus Sales Orders" in TaxJar Account settings_

**Transaction Reporting**
- Creates order transactions in TaxJar when Sales Invoice is submitted
- Creates refund transactions automatically for return invoices
- Deletes transactions from TaxJar when Sales Invoice is cancelled
- Syncs sales data to TaxJar for AutoFile remittance and filing services

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- INSTALLATION -->
## Installation

1. Navigate to your bench directory
   ```bash
   cd frappe-bench
   ```

2. Get the app
   ```bash
   bench get-app https://github.com/washmoredevelopment/taxjar_erpnext.git
   ```

3. Install the app on your site
   ```bash
   bench --site your-site.localhost install-app taxjar_erpnext
   ```

4. Run migrations
   ```bash
   bench --site your-site.localhost migrate
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONFIGURATION -->
## Configuration

### Basic Setup

1. Navigate to **TaxJar Account List** in ERPNext
2. Create a new TaxJar Account for your company
3. Enter your TaxJar API credentials (Live or Sandbox)
4. Configure your **Tax Account Head** and **Shipping Account Head**
5. Click **Sync Nexus Addresses** to pull your nexus list from TaxJar

### Non-Nexus State Settings

For businesses that want tax estimates on Quotations for states without nexus:

1. Enable **Calculate Estimated Tax for All States**
   - Quotations will show estimated tax using location-based rates
   - Note: Product exemptions are NOT applied — quoted tax may be higher than actual

2. Enable **Notify User on Non-Nexus Sales Orders** (optional)
   - Select a **Notification Recipient** user
   - A ToDo will be created when Sales Orders are submitted for non-nexus states

### Product Tax Categories

1. Navigate to **Product Tax Category** list
2. Create categories matching your TaxJar product tax codes
3. Assign categories to Items to apply correct tax rates

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements

This project is a fork of the original [TaxJar Integration](https://github.com/frappe/taxjar_integration) developed by [Frappe](https://frappe.io/). We extend our thanks to the Frappe team and all contributors to the original project.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the MIT License. See `license.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[license-shield]: https://img.shields.io/badge/License-MIT-green?style=flat
[license-url]: https://github.com/washmoredevelopment/taxjar_erpnext/blob/main/license.txt

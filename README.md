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

1. Navigate to **TaxJar Account List** in ERPNext
2. Enter your TaxJar API credentials
3. Configure your nexus addresses
4. Set up product tax categories as needed

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

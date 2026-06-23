# Copyright (c) 2026, Washmore Development, AgriTheory and contributors
# For license information, please see license.txt

from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in taxjar_erpnext/__init__.py
from taxjar_erpnext import __version__ as version

setup(
	name="taxjar_erpnext",
	version=version,
	description="TaxJar Integration with ERPNext - Multi-Company Support",
	author="Washmore Development",
	author_email="dev@washmore.app",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
)

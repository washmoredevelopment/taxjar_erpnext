# Copyright (c) 2026, Washmore Development and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest.mock import MagicMock

from taxjar_erpnext.tests.fixtures import COMPANY


def make_tax_for_order_response(amount_to_collect=1.92, line_items=None):
	if line_items is None:
		line_items = [
			SimpleNamespace(id=1, tax_collectable=amount_to_collect, taxable_amount=24.00),
		]

	return SimpleNamespace(
		amount_to_collect=amount_to_collect,
		breakdown=SimpleNamespace(line_items=line_items),
	)


def make_mixed_cart_tax_response():
	return make_tax_for_order_response(
		amount_to_collect=1.92,
		line_items=[
			SimpleNamespace(id=1, tax_collectable=1.92, taxable_amount=24.00),
			SimpleNamespace(id=2, tax_collectable=0, taxable_amount=0),
		],
	)


def make_rates_for_location_response(combined_rate=0.0625):
	return SimpleNamespace(combined_rate=combined_rate)


def patch_taxjar_client(monkeypatch, tax_for_order=None, rates_for_location=None):
	client = MagicMock()
	client.tax_for_order.return_value = tax_for_order
	client.rates_for_location.return_value = rates_for_location
	client.create_order.return_value = None
	client.create_refund.return_value = None
	client.delete_order.return_value = None
	client.nexus_regions.return_value = []

	def get_client(company):
		if company == COMPANY:
			return client
		return None

	monkeypatch.setattr(
		"taxjar_erpnext.taxjar_erpnext.taxjar_erpnext.get_client",
		get_client,
	)
	return client

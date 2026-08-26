"""Thin REST client and shared fixtures for the end-to-end suite (runs against a live site, not inside frappe)."""

import json
import os
import re
import unittest

import requests

BASE_URL = os.environ.get("FB_E2E_BASE_URL", "")
ADMIN_PASSWORD = os.environ.get("FB_E2E_ADMIN_PASSWORD", "admin")
COMPANY = "_Test Company"
BRANCH = "_Test Branch E2E"
EXPENSE_ACCOUNT = "Sales Expenses - _TC"
COST_CENTER = "_Test Cost Center - _TC"
TARGET_START = "2027-01-01"
BUDGET_START = "2027-02-01"
POSTING_DATE = "2027-02-15"

requires_live_site = unittest.skipUnless(BASE_URL, "set FB_E2E_BASE_URL to run end-to-end tests")


class ApiError(Exception):
	def __init__(self, response):
		self.response = response
		super().__init__(f"{response.status_code}: {response.text[:500]}")


class Client:
	def __init__(self, user="Administrator", password=ADMIN_PASSWORD):
		self.session = requests.Session()
		if user:
			self.login(user, password)

	def login(self, user, password):
		self.session.post(
			f"{BASE_URL}/api/method/login", data={"usr": user, "pwd": password}
		).raise_for_status()
		match = re.search(r'csrf_token\s*=\s*"([^"]+)"', self.session.get(f"{BASE_URL}/desk").text)
		if match:
			self.session.headers["X-Frappe-CSRF-Token"] = match.group(1)

	@property
	def sid(self):
		return self.session.cookies.get("sid")

	def call(self, method, **kwargs):
		response = self.session.post(f"{BASE_URL}/api/method/{method}", data=kwargs)
		if response.status_code != 200:
			raise ApiError(response)
		return response.json().get("message")

	def get_list(self, doctype, filters=None, fields=None, limit=20):
		params = {
			"filters": json.dumps(filters or {}),
			"fields": json.dumps(fields or ["name"]),
			"limit_page_length": limit,
		}
		response = self.session.get(f"{BASE_URL}/api/resource/{doctype}", params=params)
		if response.status_code != 200:
			raise ApiError(response)
		return response.json()["data"]

	def get(self, doctype, name):
		response = self.session.get(f"{BASE_URL}/api/resource/{doctype}/{name}")
		if response.status_code != 200:
			raise ApiError(response)
		return response.json()["data"]

	def insert(self, doc):
		response = self.session.post(f"{BASE_URL}/api/resource/{doc['doctype']}", json=doc)
		if response.status_code != 200:
			raise ApiError(response)
		return response.json()["data"]

	def update(self, doctype, name, values):
		response = self.session.put(f"{BASE_URL}/api/resource/{doctype}/{name}", json=values)
		if response.status_code != 200:
			raise ApiError(response)
		return response.json()["data"]

	def submit(self, doc):
		return self.call("frappe.client.submit", doc=json.dumps(doc))

	def cancel(self, doctype, name):
		return self.call("frappe.client.cancel", doctype=doctype, name=name)

	def delete(self, doctype, name):
		response = self.session.delete(f"{BASE_URL}/api/resource/{doctype}/{name}")
		if response.status_code not in (200, 202, 404):
			raise ApiError(response)


def ensure_fixtures(client):
	"""Company Budget Control, branch, submitted target (50%) and submitted budget (1000) for Feb 2027."""
	if not client.get_list("Company Budget Control", {"company": COMPANY}):
		client.insert(
			{
				"doctype": "Company Budget Control",
				"company": COMPANY,
				"frequency": "Monthly",
				"target_calculation_method": "Fixed Target",
				"fixed_target_revenue_amount": 100000,
				"group_income_account": "Income - _TC",
				"applicable_on_purchase_order": 1,
				"action_if_budget_exceeded_on_po": "Stop",
				"applicable_on_material_request": 1,
				"action_if_budget_exceeded_on_mr": "Stop",
				"applicable_on_booking_actual_expenses": 1,
				"action_if_budget_exceeded_on_actual": "Stop",
			}
		)
	if not client.get_list("Branch", {"name": BRANCH}):
		client.insert({"doctype": "Branch", "branch": BRANCH})
	targets = client.get_list(
		"Target Revenue", {"branch": BRANCH, "start_date": TARGET_START, "docstatus": 1}
	)
	if not targets:
		target = client.insert(
			{
				"doctype": "Target Revenue",
				"company": COMPANY,
				"branch": BRANCH,
				"start_date": TARGET_START,
				"override_earned_amount": 1,
				"actual_earned_amount": 50000,
			}
		)
		client.submit(target)
	budgets = client.get_list(
		"Multi-Dimensional Budget", {"company": COMPANY, "start_date": BUDGET_START, "docstatus": 1}
	)
	if budgets:
		return client.get("Multi-Dimensional Budget", budgets[0]["name"])
	budget = client.insert(
		{
			"doctype": "Multi-Dimensional Budget",
			"company": COMPANY,
			"start_date": BUDGET_START,
			"accounting_dimensions": [
				{"accounting_dimension": "Branch", "accounting_dimension_name": BRANCH}
			],
			"accounts": [{"account": EXPENSE_ACCOUNT, "budget_amount": 1000}],
		}
	)
	return client.submit(budget)


def purchase_order(amount, branch=BRANCH, **overrides):
	doc = {
		"doctype": "Purchase Order",
		"company": COMPANY,
		"supplier": "_Test Supplier",
		"transaction_date": POSTING_DATE,
		"schedule_date": POSTING_DATE,
		"currency": "INR",
		"conversion_rate": 1,
		"items": [
			{
				"item_code": "_Test Non Stock Item",
				"qty": 1,
				"rate": amount,
				"schedule_date": POSTING_DATE,
				"expense_account": EXPENSE_ACCOUNT,
				"cost_center": COST_CENTER,
				"branch": branch,
			}
		],
	}
	doc.update(overrides)
	return doc

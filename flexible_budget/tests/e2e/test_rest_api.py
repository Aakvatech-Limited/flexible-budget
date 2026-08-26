"""REST / whitelisted-method checks against a live site (FB_E2E_BASE_URL)."""

import json
import unittest

import requests

from flexible_budget.tests.e2e.client import (
	BASE_URL,
	BRANCH,
	BUDGET_START,
	COMPANY,
	EXPENSE_ACCOUNT,
	ApiError,
	Client,
	ensure_fixtures,
	purchase_order,
	requires_live_site,
)

MDB_MODULE = "flexible_budget.flexible_budget.doctype.multi_dimensional_budget.multi_dimensional_budget"
REPORT_MODULE = "flexible_budget.flexible_budget.report.multi_dimensional_budget_variance.multi_dimensional_budget_variance"


@requires_live_site
class TestRestApi(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.client = Client()
		cls.budget = ensure_fixtures(cls.client)
		cls.created = []

	@classmethod
	def tearDownClass(cls):
		for doctype, name in reversed(cls.created):
			doc = cls.client.get(doctype, name)
			if doc["docstatus"] == 1:
				cls.client.cancel(doctype, name)
			cls.client.delete(doctype, name)

	def test_ping_and_login(self):
		self.assertEqual(requests.get(f"{BASE_URL}/api/method/ping").json()["message"], "pong")
		self.assertTrue(self.client.sid)

	def test_resource_listing(self):
		names = [row["name"] for row in self.client.get_list("Multi-Dimensional Budget", {"docstatus": 1})]
		self.assertIn(self.budget["name"], names)
		doc = self.client.get("Multi-Dimensional Budget", self.budget["name"])
		self.assertEqual(doc["total_budget_amount"], 1000)
		self.assertEqual(doc["accounting_dimensions"][0]["accounting_dimension_name"], BRANCH)

	def test_get_acc_dimensions(self):
		options = self.client.call(f"{MDB_MODULE}.get_acc_dimensions")
		for expected in ("Branch", "Cost Center", "Project"):
			self.assertIn(expected, options)

	def test_run_doc_method_end_date(self):
		doc = {
			"doctype": "Multi-Dimensional Budget",
			"company": COMPANY,
			"start_date": "2027-04-01",
			"__islocal": 1,
		}
		response = self.client.session.post(
			f"{BASE_URL}/api/method/run_doc_method",
			data={"method": "set_end_date_from_frequency", "docs": json.dumps(doc)},
		).json()
		self.assertEqual(response["message"], "2027-04-30")
		self.assertEqual(response["docs"][0]["end_date"], "2027-04-30")

	def test_run_doc_method_total_amount(self):
		doc = {
			"doctype": "Multi-Dimensional Budget",
			"company": COMPANY,
			"start_date": "2027-04-01",
			"__islocal": 1,
			"accounts": [
				{
					"doctype": "Multi-Dimensional Budget Account",
					"account": EXPENSE_ACCOUNT,
					"budget_amount": 700,
				},
				{
					"doctype": "Multi-Dimensional Budget Account",
					"account": "Office Rent - _TC",
					"budget_amount": 300,
				},
			],
		}
		response = self.client.session.post(
			f"{BASE_URL}/api/method/run_doc_method",
			data={
				"method": "calculate_total_amount",
				"docs": json.dumps(doc),
				"args": json.dumps({"caller": "Front End"}),
			},
		).json()
		self.assertEqual(response["message"], 1000)

	def test_target_revenue_end_date(self):
		doc = {
			"doctype": "Target Revenue",
			"company": COMPANY,
			"branch": BRANCH,
			"start_date": "2027-04-01",
			"__islocal": 1,
		}
		response = self.client.session.post(
			f"{BASE_URL}/api/method/run_doc_method",
			data={"method": "set_end_date_from_frequency", "docs": json.dumps(doc)},
		).json()
		self.assertEqual(response["message"], "2027-04-30")

	def test_validation_error_surfaces_as_417(self):
		response = self.client.session.post(
			f"{BASE_URL}/api/resource/Company Budget Control",
			json={
				"doctype": "Company Budget Control",
				"company": "_Test Company 1",
				"frequency": "Monthly",
				"target_calculation_method": "Fixed Target",
				"fixed_target_revenue_amount": 0,
			},
		)
		self.assertEqual(response.status_code, 417)
		self.assertIn("Fixed Target Revenue Amount", response.text)

	def test_purchase_order_budget_flow(self):
		po = self.client.insert(purchase_order(600))
		self.created.append(("Purchase Order", po["name"]))
		self.assertIn("Total Expense", po["budget_overview"])
		with self.assertRaises(ApiError) as caught:
			self.client.submit(po)
		self.assertEqual(caught.exception.response.status_code, 417)
		self.assertIn("Budget Exceeded", caught.exception.response.text)
		self.assertEqual(self.client.get("Purchase Order", po["name"])["docstatus"], 0)
		self.client.delete("Purchase Order", po["name"])
		self.created.remove(("Purchase Order", po["name"]))

	def test_purchase_order_within_budget_submits(self):
		po = self.client.insert(purchase_order(100))
		self.created.append(("Purchase Order", po["name"]))
		submitted = self.client.submit(po)
		self.assertEqual(submitted["docstatus"], 1)
		self.assertIn("Remaining Budget", submitted["budget_overview"])

	def test_query_report_run(self):
		fiscal_year = self.client.get_list(
			"Fiscal Year", {"year_start_date": ["<=", BUDGET_START], "year_end_date": [">=", BUDGET_START]}
		)[0]["name"]
		filters = {
			"company": COMPANY,
			"from_fiscal_year": fiscal_year,
			"to_fiscal_year": fiscal_year,
			"branch": [BRANCH],
		}
		result = self.client.call(
			"frappe.desk.query_report.run",
			report_name="Multi-Dimensional Budget Variance",
			filters=json.dumps(filters),
		)
		rows = [
			row
			for row in result["result"]
			if isinstance(row, dict) and row.get("budget_name") == self.budget["name"]
		]
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["month"], "February 2027")
		self.assertEqual(rows[0]["target_percentage"], 50)
		self.assertEqual(result["chart"]["type"], "bar")
		self.assertTrue(result["report_summary"])
		url = self.client.call(f"{REPORT_MODULE}.export_to_excel", filters=json.dumps(filters))
		self.assertIn("multi_dimensional_budget_variance_", url)
		self.assertEqual(self.client.session.get(url).status_code, 200)

	def test_export_custom_fields(self):
		names = [
			row["name"]
			for row in self.client.get_list(
				"Custom Field", {"dt": "Purchase Order", "fieldname": "budget_overview"}
			)
		]
		exported = self.client.call(
			"flexible_budget.patches.create_custom_fields.export_custom_fields", docnames=json.dumps(names)
		)
		self.assertIn("budget_overview", exported)

	def test_guest_is_denied(self):
		response = requests.post(f"{BASE_URL}/api/method/{MDB_MODULE}.get_acc_dimensions")
		self.assertEqual(response.status_code, 403)
		response = requests.get(f"{BASE_URL}/api/resource/Multi-Dimensional Budget")
		self.assertEqual(response.status_code, 403)

	def test_accounts_user_cannot_read_budgets(self):
		email = "fb_e2e_accounts_user@example.com"
		if not self.client.get_list("User", {"name": email}):
			self.client.insert(
				{
					"doctype": "User",
					"email": email,
					"first_name": "FB E2E",
					"send_welcome_email": 0,
					"new_password": "Test@12345",
					"roles": [{"role": "Accounts User"}],
				}
			)
		user_client = Client(email, "Test@12345")
		with self.assertRaises(ApiError) as caught:
			user_client.get_list("Multi-Dimensional Budget")
		self.assertEqual(caught.exception.response.status_code, 403)

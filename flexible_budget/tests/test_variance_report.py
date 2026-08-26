"""Multi-Dimensional Budget Variance script report."""

import os

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from flexible_budget.flexible_budget.report.multi_dimensional_budget_variance import (
	multi_dimensional_budget_variance as report,
)
from flexible_budget.tests.utils import (
	BRANCH,
	COMPANY,
	COST_CENTER,
	EXPENSE_ACCOUNT,
	OTHER_BRANCH,
	OTHER_COMPANY,
	OTHER_EXPENSE_ACCOUNT,
	fiscal_year_name,
	make_budget,
	make_company_budget_control,
	make_purchase_invoice,
	make_target_revenue,
)


def filters(**extra):
	fiscal_year = fiscal_year_name()
	return {"company": COMPANY, "from_fiscal_year": fiscal_year, "to_fiscal_year": fiscal_year, **extra}


class TestVarianceReport(IntegrationTestCase):
	"""Budget 1000 for June 2026, target at 50%, 600 booked -> allowed 500, variance -100."""

	def setUp(self):
		super().setUp()
		self.settings = make_company_budget_control()
		self.target = make_target_revenue(override_earned_amount=1, actual_earned_amount=50000)
		self.budget = make_budget()
		self.invoice = make_purchase_invoice(600, submit=True, bypass_budget_validation=1)

	def tearDown(self):
		frappe.db.rollback()

	def run_report(self, **extra):
		return report.execute(filters(**extra))

	def test_single_month_row(self):
		columns, data, message, chart, summary = self.run_report()
		self.assertEqual(len(data), 1)
		row = data[0]
		self.assertEqual(row["budget_name"], self.budget.name)
		self.assertEqual(row["account"], EXPENSE_ACCOUNT)
		self.assertEqual(row["branch"], BRANCH)
		self.assertEqual(row["month"], "June 2026")
		self.assertAlmostEqual(row["budget_amount"], 1000)
		self.assertEqual(row["target_amount"], 100000)
		self.assertEqual(row["earned_amount"], 50000)
		self.assertEqual(row["target_percentage"], 50)
		self.assertAlmostEqual(row["allowed_amount"], 500)
		self.assertAlmostEqual(row["actual_amount"], 600)
		self.assertAlmostEqual(row["variance_amount"], -100)
		self.assertAlmostEqual(row["variance_percent"], -20)
		self.assertAlmostEqual(row["utilization_percent"], 120)

	def test_columns_include_accounting_dimensions(self):
		columns = report.get_columns(filters())
		fieldnames = [column["fieldname"] for column in columns]
		self.assertEqual(fieldnames[:2], ["budget_name", "account"])
		for dimension in frappe.get_all("Accounting Dimension", pluck="name"):
			self.assertIn(frappe.scrub(dimension), fieldnames)
		for fieldname in (
			"month",
			"budget_amount",
			"allowed_amount",
			"actual_amount",
			"variance_amount",
			"utilization_percent",
		):
			self.assertIn(fieldname, fieldnames)

	def test_chart_and_summary(self):
		columns, data, message, chart, summary = self.run_report()
		self.assertEqual(chart["type"], "bar")
		self.assertEqual(chart["data"]["labels"], ["June 2026"])
		values = [dataset["values"][0] for dataset in chart["data"]["datasets"]]
		self.assertAlmostEqual(values[0], 1000)
		self.assertAlmostEqual(values[1], 500)
		self.assertAlmostEqual(values[2], 600)
		labels = [item["label"] for item in summary]
		self.assertEqual(
			labels,
			[
				"Total Budget Amount",
				"Total Allowed Amount",
				"Total Actual Amount",
				"Total Variance",
				"Overall Utilization %",
			],
		)
		self.assertEqual(summary[3]["indicator"], "red")
		self.assertEqual(summary[4]["value"], "120.00%")
		self.assertEqual(summary[4]["indicator"], "orange")
		self.assertEqual(message, "Report includes 1 entries from 1 Multi-Dimensional Budget(s).")

	def test_empty_result(self):
		columns, data, message, chart, summary = self.run_report(company=OTHER_COMPANY)
		self.assertEqual(data, [])
		self.assertIsNone(chart)
		self.assertEqual(summary, [])
		self.assertEqual(message, "No budget data found for the selected criteria.")

	def test_mandatory_filters(self):
		self.assertRaisesRegex(frappe.ValidationError, "Company is mandatory", report.execute, {})
		self.assertRaisesRegex(
			frappe.ValidationError, "From Fiscal Year is mandatory", report.execute, {"company": COMPANY}
		)
		self.assertRaisesRegex(
			frappe.ValidationError,
			"To Fiscal Year is mandatory",
			report.execute,
			{"company": COMPANY, "from_fiscal_year": fiscal_year_name()},
		)

	def test_fiscal_year_order(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			"cannot be greater",
			report.execute,
			{
				"company": COMPANY,
				"from_fiscal_year": fiscal_year_name("2027-06-15"),
				"to_fiscal_year": fiscal_year_name(),
			},
		)
		columns, data, *_ = self.run_report(to_fiscal_year=fiscal_year_name("2027-06-15"))
		self.assertEqual(len([row for row in data if row["budget_name"] == self.budget.name]), 1)

	def test_account_filter(self):
		self.assertEqual(len(self.run_report(account=[EXPENSE_ACCOUNT])[1]), 1)
		self.assertEqual(self.run_report(account=[OTHER_EXPENSE_ACCOUNT])[1], [])

	def test_dimension_filters(self):
		self.assertEqual(len(self.run_report(branch=[BRANCH])[1]), 1)
		self.assertEqual(self.run_report(branch=[OTHER_BRANCH])[1], [])
		self.assertEqual(self.run_report(cost_center=[COST_CENTER])[1], [])

	def test_date_filters(self):
		self.assertEqual(len(self.run_report(from_date="2026-06-20")[1]), 1)
		self.assertEqual(len(self.run_report(to_date="2026-06-10")[1]), 1)
		self.assertEqual(self.run_report(from_date="2026-07-01")[1], [])
		self.assertEqual(self.run_report(to_date="2026-05-31")[1], [])

	def test_quarterly_budget_is_split_per_month(self):
		self.budget.cancel()
		self.target.cancel()
		self.settings.db_set("frequency", "Quarterly")
		make_target_revenue(start_date="2026-03-01", override_earned_amount=1, actual_earned_amount=50000)
		budget = make_budget()
		self.assertEqual(getdate(budget.end_date), getdate("2026-08-31"))
		columns, data, *_ = self.run_report()
		self.assertEqual([row["month"] for row in data], ["June 2026", "July 2026", "August 2026"])
		self.assertAlmostEqual(sum(row["budget_amount"] for row in data), 1000)
		self.assertAlmostEqual(data[1]["budget_amount"], 1000 * 31 / 92)
		self.assertEqual([row["target_percentage"] for row in data], [50, 50, 50])
		self.assertAlmostEqual(data[0]["actual_amount"], 600)
		self.assertAlmostEqual(data[1]["actual_amount"], 0)

	def test_determine_frequency_from_dates(self):
		cases = {
			("2026-06-01", "2026-06-07"): "Weekly",
			("2026-06-01", "2026-06-30"): "Monthly",
			("2026-02-01", "2026-02-28"): "Monthly",
			("2026-06-01", "2026-08-31"): "Quarterly",
			("2026-06-01", "2026-11-30"): "Half-yearly",
			("2026-06-01", "2027-05-31"): "Yearly",
			("2026-06-01", "2026-06-15"): "Monthly",
		}
		for (start, end), expected in cases.items():
			self.assertEqual(report.determine_frequency_from_dates(start, end), expected, (start, end))

	def test_months_between_dates(self):
		months = report.get_months_between_dates("2026-06-15", "2026-08-10")
		self.assertEqual([month["month_name"] for month in months], ["June 2026", "July 2026", "August 2026"])
		self.assertEqual(months[0]["start_date"], getdate("2026-06-15"))
		self.assertEqual(months[0]["end_date"], getdate("2026-06-30"))
		self.assertEqual(months[2]["end_date"], getdate("2026-08-10"))
		self.assertEqual([month["sort_key"] for month in months], [202606, 202607, 202608])

	def test_target_revenue_lookup_and_fallback(self):
		found = report.get_target_revenue_data(COMPANY, BRANCH, "2026-06-01", "2026-06-30", "monthly")
		self.assertEqual(found["target_percentage"], 50)
		fallback = report.get_target_revenue_data(COMPANY, BRANCH, "2026-05-01", "2026-05-31", "monthly")
		self.assertEqual(fallback["target_percentage"], 50)
		missing = report.get_target_revenue_data(COMPANY, OTHER_BRANCH, "2026-06-01", "2026-06-30", None)
		self.assertEqual(missing, {"target_amount": 0, "earned_amount": 0, "target_percentage": 0})

	def test_export_to_excel(self):
		url = report.export_to_excel(frappe.as_json(filters()))
		self.assertIn("/files/multi_dimensional_budget_variance_", url)
		file_name = url.rsplit("/", 1)[-1]
		path = frappe.get_site_path("public", "files", file_name)
		self.assertTrue(os.path.exists(path))
		os.remove(path)
		self.assertIn(report.export_to_excel, frappe.whitelisted)

	def test_export_to_excel_without_data(self):
		self.assertRaisesRegex(
			frappe.ValidationError, "No data found", report.export_to_excel, filters(company=OTHER_COMPANY)
		)

	def test_budget_adjustment_validation(self):
		self.assertRaisesRegex(
			frappe.ValidationError, "Invalid data", report.create_budget_adjustment, [], {}
		)
		self.assertRaisesRegex(
			frappe.ValidationError,
			"greater than zero",
			report.create_budget_adjustment,
			[{"account": EXPENSE_ACCOUNT}],
			{"adjustment_type": "Increase Budget", "adjustment_amount": 0},
		)

	def test_budget_adjustment_creates_journal_entry(self):
		result = report.create_budget_adjustment(
			frappe.as_json([{"account": EXPENSE_ACCOUNT, "cost_center": COST_CENTER, "company": COMPANY}]),
			frappe.as_json(
				{"adjustment_type": "Increase Budget", "adjustment_amount": 100, "reason": "test"}
			),
		)
		self.assertTrue(result["success"])
		self.assertEqual(frappe.db.get_value("Journal Entry", result["journal_entry"], "docstatus"), 1)

	def test_utilization_summary(self):
		columns, data, *_ = self.run_report()
		summary = report.get_budget_utilization_summary(data)
		self.assertEqual(summary["total_items"], 1)
		self.assertEqual(summary["over_budget_items"], 1)
		self.assertEqual(summary["under_budget_items"], 0)
		self.assertAlmostEqual(summary["utilization_rate"], 60)
		self.assertEqual(report.get_budget_utilization_summary([]), {})

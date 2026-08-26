# Copyright (c) 2025, elius mgani and Contributors
# See license.txt

import re

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from flexible_budget.flexible_budget.doctype.multi_dimensional_budget.multi_dimensional_budget import (
	MultiDimensionalBudget,
	get_acc_dimensions,
)
from flexible_budget.tests.utils import (
	BRANCH,
	BUDGET_END,
	BUDGET_START,
	CASH_ACCOUNT,
	COMPANY,
	COST_CENTER,
	EXPENSE_ACCOUNT,
	GROUP_EXPENSE_ACCOUNT,
	OTHER_BRANCH,
	OTHER_COMPANY,
	OTHER_EXPENSE_ACCOUNT,
	make_budget,
	make_company_budget_control,
)


class TestMultiDimensionalBudget(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.settings = make_company_budget_control()

	def tearDown(self):
		frappe.db.rollback()

	def test_naming_series(self):
		budget = make_budget(submit=False)
		self.assertRegex(budget.name, r"^MDB-\d{4}-\d+$")

	def test_end_date_from_monthly_frequency(self):
		budget = make_budget(submit=False)
		self.assertEqual(getdate(budget.end_date), getdate(BUDGET_END))

	def test_end_date_per_frequency(self):
		expectations = {
			"Weekly": "2026-06-07",
			"Quarterly": "2026-08-31",
			"Half-Yearly": "2026-11-30",
			"Yearly": "2027-05-31",
		}
		for frequency, expected in expectations.items():
			self.settings.db_set("frequency", frequency)
			budget = make_budget(submit=False)
			self.assertEqual(getdate(budget.end_date), getdate(expected), frequency)
			budget.delete()

	def test_whitelisted_end_date_helper(self):
		doc = frappe.new_doc("Multi-Dimensional Budget")
		doc.company = COMPANY
		doc.start_date = BUDGET_START
		self.assertEqual(getdate(doc.set_end_date_from_frequency()), getdate(BUDGET_END))
		self.assertIn(MultiDimensionalBudget.set_end_date_from_frequency, frappe.whitelisted)
		self.assertIn(MultiDimensionalBudget.calculate_total_amount, frappe.whitelisted)

	def test_actions_copied_from_settings(self):
		budget = make_budget(submit=False)
		self.assertEqual(budget.applicable_on_purchase_order, 1)
		self.assertEqual(budget.action_if_budget_exceeded_on_po, "Stop")
		self.assertEqual(budget.applicable_on_material_request, 1)
		self.assertEqual(budget.action_if_budget_exceeded_on_mr, "Stop")
		self.assertEqual(budget.applicable_on_booking_actual_expenses, 1)
		self.assertEqual(budget.action_if_budget_exceeded, "Stop")

	def test_total_budget_amount(self):
		budget = make_budget(accounts=[(EXPENSE_ACCOUNT, 1000), (OTHER_EXPENSE_ACCOUNT, 500)], submit=False)
		self.assertEqual(budget.total_budget_amount, 1500)
		budget.accounts[0].budget_amount = 2000
		self.assertEqual(budget.calculate_total_amount(caller="Front End"), 2500)
		self.assertEqual(budget.total_budget_amount, 1500)

	def test_end_date_required_without_settings(self):
		frappe.delete_doc("Company Budget Control", COMPANY, force=1)
		self.assertRaisesRegex(frappe.ValidationError, "End Date is required", make_budget, submit=False)

	def test_company_and_dates_required(self):
		doc = frappe.new_doc("Multi-Dimensional Budget")
		doc.company = None
		self.assertRaisesRegex(frappe.ValidationError, "Company is required", doc.validate_required_fields)
		doc.company = COMPANY
		self.assertRaisesRegex(frappe.ValidationError, "Start Date is required", doc.validate_required_fields)

	def test_rejects_group_account(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			"Group Account",
			make_budget,
			accounts=[(GROUP_EXPENSE_ACCOUNT, 100)],
			submit=False,
		)

	def test_rejects_balance_sheet_account(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			"not an Income or Expense",
			make_budget,
			accounts=[(CASH_ACCOUNT, 100)],
			submit=False,
		)

	def test_rejects_account_of_other_company(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			"does not belong to company",
			make_budget,
			accounts=[("Sales Expenses - _TC1", 100)],
			submit=False,
		)

	def test_rejects_duplicate_account(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			"multiple times",
			make_budget,
			accounts=[(EXPENSE_ACCOUNT, 100), (EXPENSE_ACCOUNT, 200)],
			submit=False,
		)

	def test_rejects_duplicate_dimension(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			"Duplicate accounting dimension",
			make_budget,
			dimensions=[("Branch", BRANCH), ("Branch", OTHER_BRANCH)],
			submit=False,
		)

	def test_rejects_dimension_of_other_company(self):
		other_cost_center = frappe.get_value("Cost Center", {"company": OTHER_COMPANY}, "name")
		self.assertRaisesRegex(
			frappe.ValidationError,
			"does not belong to company",
			make_budget,
			dimensions=[("Branch", BRANCH), ("Cost Center", other_cost_center)],
			submit=False,
		)

	def test_dimensions_validated_on_update(self):
		budget = make_budget(submit=False)
		budget.append(
			"accounting_dimensions",
			{"accounting_dimension": "Branch", "accounting_dimension_name": OTHER_BRANCH},
		)
		self.assertRaisesRegex(frappe.ValidationError, "Duplicate accounting dimension", budget.save)

	def test_branch_dimension_required_on_submit(self):
		budget = make_budget(dimensions=[("Cost Center", COST_CENTER)], submit=False)
		self.assertRaisesRegex(frappe.ValidationError, "Branch dimension is required", budget.submit)

	def test_submit_with_branch_dimension(self):
		budget = make_budget()
		self.assertEqual(budget.docstatus, 1)

	def test_overlap_with_same_dimensions_rejected(self):
		make_budget()
		self.assertRaisesRegex(frappe.ValidationError, "already exists", make_budget, submit=False)

	def test_overlap_with_different_dimensions_allowed(self):
		make_budget()
		second = make_budget(dimensions=[("Branch", OTHER_BRANCH)], submit=False)
		self.assertTrue(second.name)

	def test_no_overlap_when_period_differs(self):
		make_budget()
		second = make_budget(start_date="2026-07-01", submit=False)
		self.assertEqual(getdate(second.end_date), getdate("2026-07-31"))

	def test_cancelled_budget_ignored_for_overlap(self):
		first = make_budget()
		first.cancel()
		second = make_budget(submit=False)
		self.assertTrue(second.name)

	def test_overlap_check_tolerates_empty_dimension_name(self):
		make_budget()
		second = make_budget(dimensions=[("Branch", None)], submit=False)
		self.assertTrue(second.name)

	def test_get_acc_dimensions(self):
		options = get_acc_dimensions()
		for expected in ("Branch", "Cost Center", "Project"):
			self.assertIn(expected, options)
		for dimension in frappe.get_all("Accounting Dimension", pluck="name"):
			self.assertIn(dimension, options)
		self.assertIn(get_acc_dimensions, frappe.whitelisted)

	def test_amend_after_cancel(self):
		first = make_budget()
		first.cancel()
		amended = frappe.copy_doc(first)
		amended.docstatus = 0
		amended.amended_from = first.name
		amended.insert()
		self.assertTrue(re.match(r"^MDB-\d{4}-\d+-1$", amended.name))

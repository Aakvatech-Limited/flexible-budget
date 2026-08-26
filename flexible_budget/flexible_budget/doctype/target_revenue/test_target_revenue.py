# Copyright (c) 2025, Emanuel Fidelis and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from flexible_budget.flexible_budget.doctype.target_revenue.target_revenue import TargetRevenue
from flexible_budget.flexible_budget.utils import get_revenue_per_target_doc, update_revenue
from flexible_budget.tests.utils import (
	BRANCH,
	CASH_ACCOUNT,
	COMPANY,
	INCOME_ACCOUNT,
	OTHER_BRANCH,
	TARGET_START,
	make_company_budget_control,
	make_journal_entry,
	make_target_revenue,
	make_test_user,
)


class TestTargetRevenue(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.settings = make_company_budget_control()

	def tearDown(self):
		frappe.db.rollback()

	def book_revenue(self, amount, branch=BRANCH, posting_date="2026-05-10"):
		return make_journal_entry(
			amount,
			debit_account=CASH_ACCOUNT,
			credit_account=INCOME_ACCOUNT,
			branch=branch,
			posting_date=posting_date,
			submit=True,
		)

	def test_naming_series(self):
		target = make_target_revenue(submit=False)
		self.assertRegex(target.name, r"^TR-\d{4}-\d+$")

	def test_end_date_from_frequency(self):
		target = make_target_revenue(submit=False)
		self.assertEqual(getdate(target.end_date), getdate("2026-05-31"))

	def test_whitelisted_end_date_helper(self):
		doc = frappe.new_doc("Target Revenue")
		doc.company = COMPANY
		doc.start_date = TARGET_START
		self.assertEqual(getdate(doc.set_end_date_from_frequency()), getdate("2026-05-31"))
		self.assertIn(TargetRevenue.set_end_date_from_frequency, frappe.whitelisted)

	def test_fixed_target_amount_from_settings(self):
		target = make_target_revenue(submit=False)
		self.assertEqual(target.target_amount, 100000)
		self.assertEqual(target.earned_amount, 0)
		self.assertEqual(target.target_percentage, 0)

	def test_override_earned_amount_sets_percentage(self):
		target = make_target_revenue(submit=False, override_earned_amount=1, actual_earned_amount=50000)
		self.assertEqual(target.earned_amount, 50000)
		self.assertEqual(target.target_percentage, 50)

	def test_revenue_based_target_equals_earned_amount(self):
		make_company_budget_control(
			target_calculation_method="Revenue-Based Target", fixed_target_revenue_amount=0
		)
		target = make_target_revenue(submit=False, override_earned_amount=1, actual_earned_amount=8000)
		self.assertEqual(target.target_amount, 8000)
		self.assertEqual(target.target_percentage, 100)

	def test_overlap_for_same_branch_rejected(self):
		make_target_revenue()
		self.assertRaisesRegex(frappe.ValidationError, "already exists", make_target_revenue, submit=False)

	def test_overlap_for_other_branch_allowed(self):
		make_target_revenue()
		second = make_target_revenue(branch=OTHER_BRANCH, submit=False)
		self.assertTrue(second.name)

	def test_recalculates_on_update_after_submit(self):
		target = make_target_revenue()
		target.override_earned_amount = 1
		target.actual_earned_amount = 25000
		target.save()
		target.reload()
		self.assertEqual(target.earned_amount, 25000)
		self.assertEqual(target.target_percentage, 25)

	def test_update_revenue_from_gl_entries(self):
		self.book_revenue(5000)
		target = make_target_revenue()
		update_revenue(target)
		self.assertEqual(target.earned_amount, 5000)
		self.assertEqual(target.target_percentage, 5)

	def test_update_revenue_is_idempotent(self):
		self.book_revenue(5000)
		target = make_target_revenue()
		update_revenue(target)
		update_revenue(target)
		self.assertEqual(target.earned_amount, 5000)

	def test_update_revenue_ignores_other_branch_and_period(self):
		self.book_revenue(5000, branch=OTHER_BRANCH)
		self.book_revenue(7000, posting_date="2026-06-10")
		target = make_target_revenue()
		update_revenue(target)
		self.assertEqual(target.earned_amount, 0)

	def test_update_revenue_skips_overridden_target(self):
		self.book_revenue(5000)
		target = make_target_revenue(override_earned_amount=1, actual_earned_amount=100)
		update_revenue(target)
		self.assertEqual(target.earned_amount, 100)

	def test_update_revenue_for_all_submitted_targets(self):
		self.book_revenue(5000)
		target = make_target_revenue()
		draft = make_target_revenue(branch=OTHER_BRANCH, submit=False)
		update_revenue()
		self.assertEqual(frappe.db.get_value("Target Revenue", target.name, "earned_amount"), 5000)
		self.assertEqual(frappe.db.get_value("Target Revenue", draft.name, "earned_amount"), 0)

	def test_update_revenue_without_income_group(self):
		self.settings.db_set("group_income_account", None)
		self.book_revenue(5000)
		target = make_target_revenue()
		get_revenue_per_target_doc(target)
		self.assertEqual(target.earned_amount, 0)

	def test_system_manager_can_submit(self):
		user = make_test_user("fb_manager@example.com", ["System Manager"])
		self.assertTrue(frappe.has_permission("Target Revenue", "submit", user=user))
		self.assertTrue(frappe.has_permission("Target Revenue", "cancel", user=user))

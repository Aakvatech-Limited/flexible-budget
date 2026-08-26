"""Budget enforcement on Purchase Order, Material Request, Purchase Invoice, Journal Entry and Expense Claim."""

import frappe
from erpnext.accounts.doctype.budget.budget import BudgetError
from frappe.tests import IntegrationTestCase

from flexible_budget.flexible_budget import utils
from flexible_budget.tests.utils import (
	BANK_ACCOUNT,
	BRANCH,
	BUDGET_END,
	BUDGET_START,
	COMPANY,
	COST_CENTER,
	EXPENSE_ACCOUNT,
	INCOME_ACCOUNT,
	OTHER_BRANCH,
	POSTING_DATE,
	fiscal_year_name,
	make_budget,
	make_company_budget_control,
	make_expense_claim,
	make_journal_entry,
	make_material_request,
	make_purchase_invoice,
	make_purchase_order,
	make_target_revenue,
)


def budget_exceeded_message_shown():
	return any("Budget Exceeded" in frappe.as_json(message) for message in frappe.local.message_log)


class BudgetValidationTestCase(IntegrationTestCase):
	"""Budget of 1000 for Sales Expenses/_Test Branch in June 2026, target at 50% -> allowed 500."""

	settings_overrides = {}

	def setUp(self):
		super().setUp()
		frappe.clear_messages()
		self.settings = make_company_budget_control(**self.settings_overrides)
		self.target = make_target_revenue(override_earned_amount=1, actual_earned_amount=50000)
		self.budget = make_budget()

	def tearDown(self):
		frappe.db.rollback()


class TestPurchaseOrderBudget(BudgetValidationTestCase):
	def test_within_budget_records_overview(self):
		po = make_purchase_order(400)
		self.assertIn("Remaining Budget", po.budget_overview)
		self.assertIn(EXPENSE_ACCOUNT, po.budget_overview)
		self.assertIn(BRANCH, po.budget_overview)
		self.assertFalse(budget_exceeded_message_shown())

	def test_over_budget_only_warns_on_save(self):
		po = make_purchase_order(600)
		self.assertEqual(po.docstatus, 0)
		self.assertIn("Total Expense", po.budget_overview)
		self.assertTrue(budget_exceeded_message_shown())

	def test_over_budget_blocked_on_submit(self):
		po = make_purchase_order(600)
		self.assertRaises(BudgetError, po.submit)

	def test_existing_orders_count_towards_budget(self):
		make_purchase_order(300, submit=True)
		po = make_purchase_order(300)
		self.assertRaises(BudgetError, po.submit)

	def test_cancelled_orders_do_not_count(self):
		cancelled = make_purchase_order(300, submit=True)
		cancelled.cancel()
		po = make_purchase_order(300, submit=True)
		self.assertEqual(po.docstatus, 1)

	def test_bypass_flag_skips_validation(self):
		po = make_purchase_order(600, bypass_budget_validation=1, submit=True)
		self.assertEqual(po.docstatus, 1)
		self.assertFalse(po.budget_overview)

	def test_other_branch_has_no_budget(self):
		po = make_purchase_order(600, branch=OTHER_BRANCH, submit=True)
		self.assertEqual(po.docstatus, 1)
		self.assertFalse(po.budget_overview)

	def test_outside_budget_period(self):
		po = make_purchase_order(600, posting_date="2026-07-15", submit=True)
		self.assertFalse(po.budget_overview)

	def test_non_expense_account_is_ignored(self):
		po = make_purchase_order(600, account=INCOME_ACCOUNT, submit=True)
		self.assertFalse(po.budget_overview)

	def test_no_target_revenue_allows_nothing(self):
		self.target.cancel()
		po = make_purchase_order(1)
		self.assertRaises(BudgetError, po.submit)


class TestPurchaseOrderWarnAction(BudgetValidationTestCase):
	settings_overrides = {"action_if_budget_exceeded_on_po": "Warn"}

	def test_over_budget_submits_with_warning(self):
		po = make_purchase_order(600, submit=True)
		self.assertEqual(po.docstatus, 1)
		self.assertTrue(budget_exceeded_message_shown())


class TestPurchaseOrderIgnoreAction(BudgetValidationTestCase):
	settings_overrides = {"action_if_budget_exceeded_on_po": "Ignore"}

	def test_over_budget_submits_silently(self):
		po = make_purchase_order(600, submit=True)
		self.assertEqual(po.docstatus, 1)
		self.assertFalse(po.budget_overview)
		self.assertFalse(budget_exceeded_message_shown())


class TestPurchaseOrderNotApplicable(BudgetValidationTestCase):
	settings_overrides = {"applicable_on_purchase_order": 0, "action_if_budget_exceeded_on_po": ""}

	def test_falls_back_to_actual_expense_action(self):
		self.assertEqual(self.budget.applicable_on_purchase_order, 0)
		po = make_purchase_order(600)
		self.assertRaises(BudgetError, po.submit)


class TestMaterialRequestBudget(BudgetValidationTestCase):
	def test_over_budget_blocked_on_submit(self):
		mr = make_material_request(600)
		self.assertIn("Total Expense", mr.budget_overview)
		self.assertRaises(BudgetError, mr.submit)

	def test_within_budget_submits(self):
		mr = make_material_request(400, submit=True)
		self.assertEqual(mr.docstatus, 1)
		self.assertIn("Remaining Budget", mr.budget_overview)

	def test_cancelled_requests_do_not_count(self):
		cancelled = make_material_request(300, submit=True)
		cancelled.cancel()
		po = make_purchase_order(300, submit=True)
		self.assertEqual(po.docstatus, 1)

	def test_pending_requests_count_towards_budget(self):
		make_material_request(300, submit=True)
		po = make_purchase_order(300)
		self.assertRaises(BudgetError, po.submit)


class TestPurchaseInvoiceBudget(BudgetValidationTestCase):
	def test_over_budget_blocked_on_submit(self):
		pi = make_purchase_invoice(600)
		self.assertRaises(BudgetError, pi.submit)

	def test_within_budget_submits(self):
		pi = make_purchase_invoice(400, submit=True)
		self.assertEqual(pi.docstatus, 1)
		self.assertIn("Remaining Budget", pi.budget_overview)

	def test_booked_expense_counts_towards_budget(self):
		make_purchase_invoice(400, submit=True)
		po = make_purchase_order(200)
		self.assertRaises(BudgetError, po.submit)

	def test_invoice_against_purchase_order_is_skipped(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import (
			make_purchase_invoice as invoice_from_order,
		)

		po = make_purchase_order(400, submit=True)
		pi = invoice_from_order(po.name)
		pi.insert()
		self.assertEqual(pi.items[0].purchase_order, po.name)
		self.assertFalse(pi.budget_overview)


class TestJournalEntryBudget(BudgetValidationTestCase):
	def test_over_budget_blocked_on_submit(self):
		je = make_journal_entry(600)
		self.assertRaises(BudgetError, je.submit)

	def test_within_budget_submits(self):
		je = make_journal_entry(400, submit=True)
		self.assertEqual(je.docstatus, 1)
		self.assertIn("Remaining Budget", je.budget_overview)

	def test_bank_entry_is_skipped(self):
		je = make_journal_entry(
			600,
			credit_account=BANK_ACCOUNT,
			voucher_type="Bank Entry",
			cheque_no="E2E-1",
			cheque_date=POSTING_DATE,
			submit=True,
		)
		self.assertEqual(je.docstatus, 1)
		self.assertFalse(je.budget_overview)

	def test_rows_with_same_dimensions_are_summed(self):
		je = make_journal_entry(300)
		je.append(
			"accounts",
			{
				"account": EXPENSE_ACCOUNT,
				"debit_in_account_currency": 300,
				"cost_center": COST_CENTER,
				"branch": BRANCH,
			},
		)
		je.accounts[1].credit_in_account_currency = 600
		je.save()
		self.assertRaises(BudgetError, je.submit)


class TestExpenseClaimBudget(BudgetValidationTestCase):
	def setUp(self):
		super().setUp()
		self.budget.db_set("applicable_on_expense_claim", 1)
		self.budget.db_set("action_if_budget_exceeded_on_ec", "Stop")

	def test_over_budget_blocked_on_submit(self):
		claim = make_expense_claim(600)
		self.assertIn("Total Expense", claim.budget_overview)
		self.assertRaises(BudgetError, claim.submit)

	def test_within_budget_submits(self):
		claim = make_expense_claim(400, submit=True)
		self.assertEqual(claim.docstatus, 1)
		self.assertIn("Remaining Budget", claim.budget_overview)

	def test_pending_claims_count_towards_budget(self):
		make_expense_claim(300)
		po = make_purchase_order(300)
		self.assertRaises(BudgetError, po.submit)

	def test_bypass_flag_skips_validation(self):
		claim = make_expense_claim(600, bypass_budget_validation=1, submit=True)
		self.assertEqual(claim.docstatus, 1)


class TestBudgetHelpers(BudgetValidationTestCase):
	def test_target_revenue_percent(self):
		self.assertEqual(utils.get_target_revenue_percent(COMPANY, POSTING_DATE, BRANCH), 50)
		self.assertEqual(utils.get_target_revenue_percent(COMPANY, POSTING_DATE, OTHER_BRANCH), 0)
		self.assertEqual(utils.get_target_revenue_percent(COMPANY, "2026-09-15", BRANCH), 0)

	def test_get_actions_per_document_type(self):
		budget = frappe._dict(
			action_if_budget_exceeded="Warn",
			applicable_on_material_request=1,
			action_if_budget_exceeded_on_mr="Stop",
			applicable_on_purchase_order=0,
			action_if_budget_exceeded_on_po="Ignore",
			applicable_on_expense_claim=1,
			action_if_budget_exceeded_on_ec="Ignore",
		)
		self.assertEqual(utils.get_actions({"doctype": "Material Request"}, budget), "Stop")
		self.assertEqual(utils.get_actions({"doctype": "Purchase Order"}, budget), "Warn")
		self.assertEqual(utils.get_actions({"doctype": "Expense Claim"}, budget), "Ignore")
		self.assertEqual(utils.get_actions({"doctype": "Purchase Invoice"}, budget), "Warn")

	def test_grouped_item_amounts(self):
		po = make_purchase_order(100)
		po.append("items", {**po.items[0].as_dict(), "name": None, "rate": 50, "amount": 50})
		po.append(
			"items", {**po.items[0].as_dict(), "name": None, "cost_center": "_Test Cost Center 2 - _TC"}
		)
		grouped = utils.get_grouped_item_amounts(po.items)
		self.assertEqual(len(grouped), 2)
		self.assertEqual(sorted(item.amount for item in grouped), [100, 150])
		self.assertEqual(sum(item.amount for item in po.items), 250)

	def test_grouped_item_amounts_skips_unknown_doctype(self):
		row = frappe.get_doc(
			{"doctype": "Multi-Dimensional Budget Account", "account": EXPENSE_ACCOUNT, "budget_amount": 5}
		)
		self.assertEqual(utils.get_grouped_item_amounts([row]), [])

	def test_grouped_amount_field_per_doctype(self):
		je = make_journal_entry(300)
		grouped = utils.get_grouped_item_amounts(je.accounts)
		self.assertEqual({row.account: row.amount for row in grouped}[EXPENSE_ACCOUNT], 300)
		pi = make_purchase_invoice(250)
		self.assertEqual(utils.get_grouped_item_amounts(pi.items)[0].amount, 250)

	def test_pending_amount_queries(self):
		args = frappe._dict(
			account=EXPENSE_ACCOUNT, company=COMPANY, branch=BRANCH, fiscal_year=fiscal_year_name()
		)
		budget = frappe._dict(
			start_date=BUDGET_START,
			end_date=BUDGET_END,
			accounting_dimensions=[
				frappe._dict(accounting_dimension="Branch", accounting_dimension_name=BRANCH)
			],
		)
		make_material_request(110, submit=True)
		make_purchase_order(100, submit=True)
		make_purchase_invoice(120)
		make_journal_entry(130)
		make_expense_claim(140)
		make_purchase_invoice(60, submit=True, bypass_budget_validation=1)
		self.assertEqual(utils.get_ordered_amount(args, budget), 100)
		self.assertEqual(utils.get_requested_amount(args, budget), 110)
		self.assertEqual(utils.get_invoice_amount(args, budget), 120)
		self.assertEqual(utils.get_jv_amount(args, budget), 130)
		self.assertEqual(utils.get_expense_claim_amount(args, budget), 140)
		self.assertEqual(utils.get_actual_expense(args, budget), 60)

	def test_expense_breakup_links_keep_filters(self):
		args = frappe._dict(
			account=EXPENSE_ACCOUNT,
			company=COMPANY,
			actual_expense=1,
			requested_amount=2,
			ordered_amount=3,
			invoice_amount=4,
			jv_amount=5,
			expense_claim_amount=6,
			item_code=None,
		)
		message = utils.get_expense_breakup(args, "INR", self.budget.as_dict())
		for label in (
			"Actual Expenses",
			"Material Requests",
			"Unbilled Orders",
			"Pending Invoices",
			"Pending JVs",
		):
			self.assertIn(label, message)
		self.assertIn("Pending Expense Claims", message)
		self.assertEqual(message.count("<a "), 6)
		self.assertIn("start_date", message)
		self.assertIn("default_account", message)

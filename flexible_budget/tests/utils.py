"""Shared fixtures for the flexible_budget test suite."""

import frappe

COMPANY = "_Test Company"
OTHER_COMPANY = "_Test Company 1"
BRANCH = "_Test Branch"
OTHER_BRANCH = "_Test Branch 2"
COST_CENTER = "_Test Cost Center - _TC"
EXPENSE_ACCOUNT = "Sales Expenses - _TC"
OTHER_EXPENSE_ACCOUNT = "Office Rent - _TC"
GROUP_EXPENSE_ACCOUNT = "Indirect Expenses - _TC"
INCOME_GROUP = "Income - _TC"
INCOME_ACCOUNT = "Sales - _TC"
CASH_ACCOUNT = "Cash - _TC"
BANK_ACCOUNT = "_Test Bank - _TC"
SUPPLIER = "_Test Supplier"
ITEM = "_Test Non Stock Item"
WAREHOUSE = "_Test Warehouse - _TC"

TARGET_START = "2026-05-01"
BUDGET_START = "2026-06-01"
BUDGET_END = "2026-06-30"
POSTING_DATE = "2026-06-15"


def fiscal_year_name(date=POSTING_DATE):
	from erpnext.accounts.utils import get_fiscal_year

	return get_fiscal_year(date, company=COMPANY)[0]


def before_tests():
	"""Build the ERPNext/HRMS master data the suite relies on (company, chart of accounts, dimensions)."""
	frappe.clear_cache()
	if "hrms" in frappe.get_installed_apps():
		from hrms.tests.test_utils import before_tests as hrms_before_tests

		hrms_before_tests()
	import erpnext.tests.utils  # noqa: F401  (importing the module bootstraps ERPNext test records)

	ensure_branch_dimension()
	for branch in (BRANCH, OTHER_BRANCH):
		make_branch(branch)
	ensure_expense_claim_type()
	# before_tests runs outside the per-test transaction; the bootstrap data must persist
	frappe.db.commit()  # nosemgrep


def ensure_branch_dimension():
	if not frappe.db.exists("Accounting Dimension", "Branch"):
		frappe.get_doc({"doctype": "Accounting Dimension", "document_type": "Branch"}).insert()


def ensure_expense_claim_type():
	if not frappe.db.exists("DocType", "Expense Claim Type") or frappe.db.exists(
		"Expense Claim Type", "Travel"
	):
		return
	frappe.get_doc(
		{
			"doctype": "Expense Claim Type",
			"expense_type": "Travel",
			"accounts": [{"company": COMPANY, "default_account": EXPENSE_ACCOUNT}],
		}
	).insert()


def make_branch(name):
	if not frappe.db.exists("Branch", name):
		frappe.get_doc({"doctype": "Branch", "branch": name}).insert()
	return name


def make_company_budget_control(**overrides):
	"""Create (replacing any existing one) the Company Budget Control for the test company."""
	values = {
		"doctype": "Company Budget Control",
		"company": COMPANY,
		"frequency": "Monthly",
		"target_calculation_method": "Fixed Target",
		"fixed_target_revenue_amount": 100000,
		"group_income_account": INCOME_GROUP,
		"applicable_on_material_request": 1,
		"action_if_budget_exceeded_on_mr": "Stop",
		"applicable_on_purchase_order": 1,
		"action_if_budget_exceeded_on_po": "Stop",
		"applicable_on_booking_actual_expenses": 1,
		"action_if_budget_exceeded_on_actual": "Stop",
		"action_if_no_target_revenue": "Warn",
	}
	values.update(overrides)
	if frappe.db.exists("Company Budget Control", values["company"]):
		frappe.delete_doc("Company Budget Control", values["company"], force=1, ignore_permissions=True)
	return frappe.get_doc(values).insert()


def make_budget(accounts=None, dimensions=None, submit=True, **overrides):
	accounts = accounts or [(EXPENSE_ACCOUNT, 1000)]
	dimensions = dimensions or [("Branch", BRANCH)]
	values = {
		"doctype": "Multi-Dimensional Budget",
		"company": COMPANY,
		"start_date": BUDGET_START,
		"accounting_dimensions": [
			{"accounting_dimension": dimension, "accounting_dimension_name": name}
			for dimension, name in dimensions
		],
		"accounts": [{"account": account, "budget_amount": amount} for account, amount in accounts],
	}
	values.update(overrides)
	doc = frappe.get_doc(values).insert()
	if submit:
		doc.submit()
	return doc


def make_target_revenue(start_date=TARGET_START, branch=BRANCH, submit=True, **overrides):
	values = {"doctype": "Target Revenue", "company": COMPANY, "branch": branch, "start_date": start_date}
	values.update(overrides)
	doc = frappe.get_doc(values).insert()
	if submit:
		doc.submit()
	return doc


def make_purchase_order(
	amount, account=EXPENSE_ACCOUNT, branch=BRANCH, posting_date=POSTING_DATE, submit=False, **overrides
):
	values = {
		"doctype": "Purchase Order",
		"company": COMPANY,
		"supplier": SUPPLIER,
		"transaction_date": posting_date,
		"schedule_date": posting_date,
		"currency": "INR",
		"conversion_rate": 1,
		"items": [
			{
				"item_code": ITEM,
				"qty": 1,
				"rate": amount,
				"schedule_date": posting_date,
				"expense_account": account,
				"cost_center": COST_CENTER,
				"branch": branch,
			}
		],
	}
	values.update(overrides)
	doc = frappe.get_doc(values)
	doc.set_missing_values()
	doc.insert()
	if submit:
		doc.submit()
	return doc


def make_material_request(
	amount, account=EXPENSE_ACCOUNT, branch=BRANCH, posting_date=POSTING_DATE, submit=False, **overrides
):
	values = {
		"doctype": "Material Request",
		"material_request_type": "Purchase",
		"company": COMPANY,
		"transaction_date": posting_date,
		"schedule_date": posting_date,
		"items": [
			{
				"item_code": ITEM,
				"qty": 1,
				"uom": "_Test UOM",
				"conversion_factor": 1,
				"rate": amount,
				"schedule_date": posting_date,
				"warehouse": WAREHOUSE,
				"expense_account": account,
				"cost_center": COST_CENTER,
				"branch": branch,
			}
		],
	}
	values.update(overrides)
	doc = frappe.get_doc(values).insert()
	if submit:
		doc.submit()
	return doc


def make_purchase_invoice(
	amount, account=EXPENSE_ACCOUNT, branch=BRANCH, posting_date=POSTING_DATE, submit=False, **overrides
):
	values = {
		"doctype": "Purchase Invoice",
		"company": COMPANY,
		"supplier": SUPPLIER,
		"posting_date": posting_date,
		"set_posting_time": 1,
		"due_date": posting_date,
		"currency": "INR",
		"conversion_rate": 1,
		"items": [
			{
				"item_code": ITEM,
				"qty": 1,
				"rate": amount,
				"expense_account": account,
				"cost_center": COST_CENTER,
				"branch": branch,
			}
		],
	}
	values.update(overrides)
	doc = frappe.get_doc(values)
	doc.set_missing_values()
	doc.insert()
	if submit:
		doc.submit()
	return doc


def make_journal_entry(
	amount,
	debit_account=EXPENSE_ACCOUNT,
	credit_account=CASH_ACCOUNT,
	branch=BRANCH,
	posting_date=POSTING_DATE,
	submit=False,
	**overrides,
):
	values = {
		"doctype": "Journal Entry",
		"voucher_type": "Journal Entry",
		"company": COMPANY,
		"posting_date": posting_date,
		"accounts": [
			{
				"account": debit_account,
				"debit_in_account_currency": amount,
				"cost_center": COST_CENTER,
				"branch": branch,
			},
			{
				"account": credit_account,
				"credit_in_account_currency": amount,
				"cost_center": COST_CENTER,
				"branch": branch,
			},
		],
	}
	values.update(overrides)
	doc = frappe.get_doc(values).insert()
	if submit:
		doc.submit()
	return doc


def make_expense_claim(
	amount, account=EXPENSE_ACCOUNT, branch=BRANCH, posting_date=POSTING_DATE, submit=False, **overrides
):
	from hrms.hr.doctype.expense_claim.test_expense_claim import make_expense_claim as hrms_make_expense_claim

	payable_account = frappe.get_cached_value("Company", COMPANY, "default_payable_account")
	doc = hrms_make_expense_claim(
		payable_account,
		amount,
		amount,
		COMPANY,
		account,
		args={"posting_date": posting_date},
		do_not_submit=True,
	)
	doc.update(overrides)
	doc.expenses[0].branch = branch
	doc.expenses[0].cost_center = COST_CENTER
	doc.insert()
	if submit:
		doc.submit()
	return doc


def make_test_user(email, roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"roles": [{"role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
	return email

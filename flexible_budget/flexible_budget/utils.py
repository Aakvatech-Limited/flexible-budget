import frappe
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import flt, getdate, nowdate, add_days, fmt_money
from erpnext.accounts.doctype.budget.budget import get_item_details, BudgetError


def update_allowed_amount():
    """Update allowed amount for Multi-Dimensional Budget based on Target Revenue."""

    prev_day = add_days(nowdate(), -1)

    multi_budget_docs = frappe.get_all(
        "Multi-Dimensional Budget",
        filters={
            "docstatus": 1,
            "start_date": ["<=", prev_day],
            "end_date": [">=", prev_day],
        },
        pluck="name"
    )

    for budget_id in multi_budget_docs:
        budget_doc = frappe.get_doc("Multi-Dimensional Budget", budget_id)
        budget_doc.set_allowed_amount()
        budget_doc.db_update()
        budget_doc.reload()


def update_revenue(revenue_doc=None):
    if revenue_doc:
        get_revenue_per_target_doc(revenue_doc)
    else:
        prev_day = add_days(nowdate(), -1)

        target_revenues = frappe.db.get_all(
            "Target Revenue",
            filters={
                "docstatus": 1,
                "start_date": ["<=", prev_day],
                "end_date": [">=", prev_day]
            },
            pluck="name"
        )

        for revenue_id in target_revenues:
            revenue_doc = frappe.get_doc("Target Revenue", revenue_id)
            get_revenue_per_target_doc(revenue_doc)


def get_revenue_per_target_doc(doc):
    income_account = frappe.get_cached_value("Company Budget Control", doc.company, "group_income_account")
    if not income_account:
        return
    
    lft, rgt = frappe.get_cached_value("Account", income_account, ["lft", "rgt"])
    accounts = frappe.db.get_all("Account", {
        "company": doc.company,
        "lft": [">=", lft],
        "rgt": ["<=", rgt]
    }, pluck="name")

    gle = frappe.qb.DocType("GL Entry")
    gl_results = (
        frappe.qb.from_(gle)
        .select(gle.account, gle.debit, gle.credit)
        .where(
            (gle.company == doc.company) &
            (gle.account.isin(accounts)) &
            (gle.posting_date >= doc.start_date) &
            (gle.posting_date <= doc.end_date) &
            (gle.is_cancelled == 0) &
            (gle.voucher_type != "Period Closing Voucher")
        )
    ).run(as_dict=True)

    gl_entries_by_account = {}
    for entry in gl_results:
        gl_entries_by_account.setdefault(entry.account, []).append(entry)

    account_settings = frappe.get_cached_doc("Accounts Settings")
    ignore_closing_balance = account_settings.ignore_account_closing_balance

    pcv = None
    if not ignore_closing_balance:
        pcv = frappe.db.get_all("Period Closing Voucher", 
            filters={
                "company": doc.company,
                "docstatus": 1,
                "period_end_date": ["between", [doc.start_date, doc.end_date]]
            },
            fields=["name", "period_end_date"],
            order_by="period_end_date desc",
            limit=1
        )

    if pcv:
        acb = frappe.qb.DocType("Account Closing Balance")
        acb_results = (
            frappe.qb.from_(acb)
            .select(acb.account, acb.debit, acb.credit)
            .where(
                (acb.company == doc.company) &
                (acb.account.isin(accounts)) &
                (acb.period_closing_voucher == pcv[0].name)
            )
        ).run(as_dict=True)

        for entry in acb_results:
            gl_entries_by_account.setdefault(entry.account, []).append(entry)

    total_debit = 0
    total_credit = 0
    for entries in gl_entries_by_account.values():
        for entry in entries:
            total_debit += flt(entry.get("debit", 0))
            total_credit += flt(entry.get("credit", 0))

    net_revenue = total_credit - total_debit

    doc.earned_amount += abs(net_revenue)
    doc.calculate_target_percentage()

    doc.db_update()
    doc.reload()


def validate_budget(doc, method):
    for item in doc.items:
        args = item.as_dict()
        args.update(
            {
                "doctype": doc.doctype,
                "company": doc.company,
                "posting_date": (
                    doc.schedule_date
                    if doc.doctype == "Material Request"
                    else doc.transaction_date
                ),
            }
        )

        validate_expense_against_budget(args)

def validate_expense_against_budget(args, expense_amount=0):
    args = frappe._dict(args)
    
    if args.get("company") and not args.fiscal_year:
        args.fiscal_year = get_fiscal_year(args.get("posting_date"), company=args.get("company"))[0]
        frappe.flags.exception_approver_role = frappe.get_cached_value(
			"Company", args.get("company"), "exception_budget_approver_role"
		)
    
    if not args.account:
        args.account = args.get("expense_account")
    
    if not (args.get("account") and args.get("cost_center")) and args.item_code:
        args.cost_center, args.account = get_item_details(args)

    if (
        not args.account or
        (frappe.get_cached_value("Account", args.account, "root_type") != "Expense")
    ):
        return

    budgets = frappe.db.get_all(
        "Multi-Dimensional Budget",
        {
            "docstatus": 1,
            "start_date": ["<=", args.get("posting_date")],
            "end_date": [">=", args.get("posting_date")],
            "company": args.get("company")
        },
        pluck="name"
    )

    valid_budget = None
    if len(budgets) == 0:
        return

    for budget_id in budgets:
        budget_doc = frappe.get_doc("Multi-Dimensional Budget", budget_id)

        dimensions = []

        count = 0
        no_of_dimensions = len(budget_doc.accounting_dimensions)

        for row in budget_doc.accounting_dimensions:
            if (
                args.get(frappe.scrub(row.accounting_dimension)) and
                args.get(frappe.scrub(row.accounting_dimension)) == row.accounting_dimension_name
            ):
                dimensions.append({
                    "document_type": row.accounting_dimension,
                    "accounting_dimension": row.accounting_dimension_name,
                    "fieldname": "accounting_dimension_name"
                })
                count += 1
        
        if count != no_of_dimensions:
            continue
        else:
            valid_budget = budget_doc
            break
    
    if not valid_budget:
        return
    
    budget_records = [valid_budget]
    if budget_records:
        validate_budget_records(args, budget_records, expense_amount)


def validate_budget_records(args, budget_records, expense_amount):
    for budget in budget_records:
        action = get_actions(args, budget)

        args["for_material_request"] = budget.applicable_on_material_request
        args["for_purchase_order"] = budget.applicable_on_purchase_order

        if action in ("Stop", "Warn"):
            compare_expense_with_budget(
                args,
                action,
                budget,
                expense_amount,
            )
        
        budget.calculate_budget_usage(args.amount)
        budget.db_update()
        budget.reload()


def get_actions(args, budget):
    action = budget.action_if_budget_exceeded

    if args.get("doctype") == "Material Request" and budget.applicable_on_material_request:
        action = budget.action_if_budget_exceeded_on_mr

    elif args.get("doctype") == "Purchase Order" and budget.applicable_on_purchase_order:
        action = budget.action_if_budget_exceeded_on_po

    return action


def compare_expense_with_budget(
    args,
    action,
    budget,
    amount=0
):
    args.actual_expense = get_actual_expense(args, budget)
    args.requested_amount = 0
    args.ordered_amount = 0
    
    if not amount:
        args.requested_amount = get_requested_amount(args, budget)
        args.ordered_amount = get_ordered_amount(args, budget)
        
        if args.get("doctype") == "Material Request" and budget.applicable_on_material_request:
            amount = args.requested_amount + args.ordered_amount
            
        elif args.get("doctype") == "Purchase Order" and budget.applicable_on_purchase_order:
            amount = args.ordered_amount
    
    total_expense = args.actual_expense + amount
    
    if total_expense > budget.allowed_amount:
        if args.actual_expense > budget.allowed_amount:
            error_tense = _("is already")
            diff = args.actual_expense - budget.allowed_amount
        else:
            error_tense = _("will be")
            diff = total_expense - budget.allowed_amount
            
        currency = frappe.get_cached_value("Company", args.company, "default_currency")

        dimension_str = ""
        for dimension in budget.accounting_dimensions:
            dimension_str += f"{dimension.accounting_dimension}: <b>{dimension.accounting_dimension_name}</b>, "
        
        msg = _(f"Budget for Account {frappe.bold(args.account)} against {dimension_str}\
                 is {frappe.bold(fmt_money(budget.allowed_amount, currency=currency))}.\
                     It {error_tense} exceed by {frappe.bold(fmt_money(diff, currency=currency))}"
        )
        msg += get_expense_breakup(
            args,
            currency, 
            budget
        )

        if (
            frappe.flags.exception_approver_role and 
            frappe.flags.exception_approver_role in frappe.get_roles(frappe.session.user)
        ):
            action = "Warn"
        
        if action == "Stop":
            frappe.throw(msg, BudgetError, title=_("Budget Exceeded"))
        else:
            frappe.msgprint(msg, indicator="orange", title=_("Budget Exceeded"))
        

def get_actual_expense(args, budget):
    condition1 = f" and gle.posting_date >= '{budget.start_date}' and gle.posting_date <= '{budget.end_date}' "

    condition2 = ""
    for dimension in budget.get("accounting_dimensions"):
        dim_key = frappe.scrub(dimension.accounting_dimension)
        dim_value = dimension.accounting_dimension_name
        args[dim_key] = dim_value

        if frappe.get_cached_value("DocType", dimension.accounting_dimension, "is_tree"):
            lft_key = f"{dim_key}_lft"
            rgt_key = f"{dim_key}_rgt"
            args[lft_key], args[rgt_key] = frappe.get_cached_value(
                dimension.accounting_dimension,
                dim_value,
                ["lft", "rgt"]
            )
            condition2 += f""" and exists(
                select name from `tab{dimension.accounting_dimension}`
                where lft >= %({lft_key})s and rgt <= %({rgt_key})s
                and name = gle.{dim_key}) """
        else:
            condition2 += f""" and exists(select name from `tab{dimension.accounting_dimension}`
            where name=gle.{dim_key} and gle.{dim_key} = '{args.get(dim_key)}')"""

    query = f""" select sum(gle.debit) - sum(gle.credit)
        from `tabGL Entry` gle
        where
        gle.is_cancelled = 0
        and gle.account = %(account)s
        {condition1}
        and gle.fiscal_year = %(fiscal_year)s
        and gle.company = %(company)s
        and gle.docstatus = 1
        {condition2}
    """

    amount = flt(frappe.db.sql(query, args)[0][0])
    return amount


def get_ordered_amount(args, budget):
    item_code = args.get("item_code")
    condition = get_other_condition(args, budget, "Purchase Order")
    
    data = frappe.db.sql(
        f""" select ifnull(sum(child.amount - child.billed_amt), 0) as amount
        from `tabPurchase Order Item` child, `tabPurchase Order` parent where
        parent.name = child.parent and child.item_code = %s and parent.docstatus = 1 and child.amount > child.billed_amt
        and parent.status != 'Closed' and {condition}""",
        (item_code,),
        as_list=1
    )
    amount = data[0][0] if data else 0
    
    return amount


def get_requested_amount(args, budget):
    item_code = args.get("item_code")
    condition = get_other_condition(args, budget, "Material Request")
    
    data = frappe.db.sql(
        """ select ifnull((sum(child.stock_qty - child.ordered_qty) * rate), 0) as amount
        from `tabMaterial Request Item` child, `tabMaterial Request` parent where parent.name = child.parent and
        child.item_code = %s and parent.docstatus = 1 and child.stock_qty > child.ordered_qty and {} and
        parent.material_request_type = 'Purchase' and parent.status != 'Stopped'""".format(condition),
        (item_code,),
        as_list=1,
    )

    amount = data[0][0] if data else 0
    
    return amount


def get_other_condition(args, budget, for_doc):
    condition = " child.expense_account = '%s'" % (args.expense_account)
    
    for row in budget.get("accounting_dimensions"):
        budget_against_field = frappe.scrub(row.accounting_dimension)

        if budget_against_field and args.get(budget_against_field):
            condition += f" and child.{budget_against_field} = '{args.get(budget_against_field)}'"

        date_field = "schedule_date" if for_doc == "Material Request" else "transaction_date"

        condition += f""" and parent.{date_field}
            between '{budget.start_date}' and '{budget.end_date}' """
    
    return condition


def get_expense_breakup(args, currency, budget):
    msg = "<hr>Total Expenses booked through - <ul>"
    
    filters = {
        "account": args.account,
        "company": args.company,
    }
    
    for row in budget.get("accounting_dimensions"):
        filters[row.accounting_dimension] = row.accounting_dimension_name
    
    common_filters = frappe._dict(filters)

    msg += (
        "<li>"
            + frappe.utils.get_link_to_report(
                "General Ledger",
                label="Actual Expenses",
                filters=common_filters.copy().update(
                {
                    "start_date": budget.start_date,
                    "end_date": budget.end_date,
                    "is_cancelled": 0,
                }
                ),
            )
        
        + " - "
        + frappe.bold(fmt_money(args.actual_expense, currency=currency))
        + "</li>"
    )
    
    msg += (
        "<li>"
            + frappe.utils.get_link_to_report(
                "Material Request",
                label="Material Requests",
                report_type="Report Builder",
                doctype="Material Request",
                filters=common_filters.copy().update({
                    "status": [["!=", "Stopped"]],
                    "docstatus": 1,
                    "material_request_type": "Purchase",
                    "schedule_date": ["between", [str(budget.start_date), str(budget.end_date)]],
                    "item_code": args.item_code,
                    "per_ordered": [["<", 100]],
                }),
            )
        + " - "
        + frappe.bold(fmt_money(args.requested_amount, currency=currency))
        + "</li>"
    )
    
    msg += (
        "<li>"
            + frappe.utils.get_link_to_report(
                "Purchase Order",
                label="Unbilled Orders",
                report_type="Report Builder",
                doctype="Purchase Order",
                filters=common_filters.copy().update({
                    "status": [["!=", "Closed"]],
                    "docstatus": 1,
                    "transaction_date": ["between", [str(budget.start_date), str(budget.end_date)]],
                    "item_code": args.item_code,
                    "per_billed": [["<", 100]],
                }),
            )
        + " - "
        + frappe.bold(fmt_money(args.ordered_amount, currency=currency))
        + "</li></ul>"
    )
    
    return msg

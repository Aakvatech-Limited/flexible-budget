import frappe
from frappe.utils import flt, getdate, nowdate, add_days


def update_allowed_amount():
    """Update allowed amount for Multi Dimensional Budget based on Target Revenue."""

    prev_day = add_days(nowdate(), -1)

    multi_budget_docs = frappe.get_all(
        "Multi Dimensional Budget",
        filters={
            "docstatus": 1,
            "start_date": ["<=", prev_day],
            "end_date": [">=", prev_day],
        },
        pluck="name"
    )

    for budget_id in multi_budget_docs:
        budget_doc = frappe.get_doc("Multi Dimensional Budget", budget_id)
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
                (acb.company == company) &
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

    doc.collected_amount += abs(net_revenue)
    doc.calculate_target_percentage()

    doc.db_update()
    doc.reload()

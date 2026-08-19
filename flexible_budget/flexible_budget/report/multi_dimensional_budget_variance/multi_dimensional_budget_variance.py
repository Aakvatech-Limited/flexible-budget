# Copyright (c) 2025, elius mgani and contributors
# For license information, please see license.txt

import calendar

import frappe
from dateutil.relativedelta import relativedelta
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_accounting_dimensions,
)
from erpnext.accounts.utils import get_fiscal_year
from frappe import _
from frappe.utils import add_days, flt, getdate

from flexible_budget.flexible_budget.utils import get_actual_expense


def execute(filters=None):
    if not filters:
        filters = {}

    validate_filters(filters)
    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart_data(filters, columns, data)
    summary = get_summary_data(data)
    message = get_message(filters, data)

    return columns, data, message, chart, summary


def validate_filters(filters):
    """Validate report filters"""
    if not filters.get("company"):
        frappe.throw(_("Company is mandatory"))

    if not filters.get("from_fiscal_year"):
        frappe.throw(_("From Fiscal Year is mandatory"))

    if not filters.get("to_fiscal_year"):
        frappe.throw(_("To Fiscal Year is mandatory"))

    # Validate fiscal year order
    from_fy_year = int(filters.get("from_fiscal_year").split("-")[0])
    to_fy_year = int(filters.get("to_fiscal_year").split("-")[0])

    if from_fy_year > to_fy_year:
        frappe.throw(_("From Fiscal Year cannot be greater than To Fiscal Year"))


def get_columns(filters):
    """Get report columns"""
    columns = [
        {
            "label": _("Budget ID"),
            "fieldname": "budget_name",
            "fieldtype": "Link",
            "options": "Multi-Dimensional Budget",
            "width": 180,
        },
        {
            "label": _("Account"),
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 200,
        },
    ]

    # Add dimension columns for multi-dimensional budgets
    accounting_dimensions = get_accounting_dimensions()
    for dimension in accounting_dimensions:
        columns.append(
            {
                "label": _(dimension),
                "fieldname": frappe.scrub(dimension).lower(),
                "fieldtype": "Link",
                "options": dimension,
                "width": 120,
            }
        )

    # Add month column
    columns.append({"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 100})

    # Add budget analysis columns
    columns.extend(
        [
            {
                "label": _("Budget Amount"),
                "fieldname": "budget_amount",
                "fieldtype": "Currency",
                "width": 120,
            },
            {
                "label": _("Target Amount"),
                "fieldname": "target_amount",
                "fieldtype": "Currency",
                "width": 120,
            },
            {
                "label": _("Earned Amount"),
                "fieldname": "earned_amount",
                "fieldtype": "Currency",
                "width": 120,
            },
            {
                "label": _("Target Percentage"),
                "fieldname": "target_percentage",
                "fieldtype": "Percent",
                "width": 120,
            },
            {
                "label": _("Allowed Amount"),
                "fieldname": "allowed_amount",
                "fieldtype": "Currency",
                "width": 120,
            },
            {
                "label": _("Actual Amount"),
                "fieldname": "actual_amount",
                "fieldtype": "Currency",
                "width": 120,
            },
            {
                "label": _("Variance Amount"),
                "fieldname": "variance_amount",
                "fieldtype": "Currency",
                "width": 120,
            },
            {
                "label": _("Variance %"),
                "fieldname": "variance_percent",
                "fieldtype": "Percent",
                "width": 100,
            },
            {
                "label": _("Utilization %"),
                "fieldname": "utilization_percent",
                "fieldtype": "Percent",
                "width": 100,
            },
        ]
    )

    return columns


def get_data(filters):
    """Get report data from multi-dimensional budgets only"""
    data = []

    # Get Multi-Dimensional Budget data only
    multi_dim_data = get_multi_dimensional_budget_data(filters)
    data.extend(multi_dim_data)

    # Apply additional filters
    data = apply_additional_filters(data, filters)

    # Sort data chronologically by month
    data.sort(key=lambda x: x.get("month_sort_key", 0))

    return data


def apply_additional_filters(data, filters):
    """Apply additional filters to the data"""
    filtered_data = []

    for row in data:
        # Filter by date range (optional)
        if filters.get("from_date") or filters.get("to_date"):
            month_start = row.get("month_start")
            month_end = row.get("month_end")

            if month_start and month_end:
                month_start = getdate(month_start)
                month_end = getdate(month_end)

                # Check if month overlaps with filter date range
                filter_from_date = getdate(filters.get("from_date")) if filters.get("from_date") else None
                filter_to_date = getdate(filters.get("to_date")) if filters.get("to_date") else None

                # Skip if month is completely before from_date
                if filter_from_date and month_end < filter_from_date:
                    continue

                # Skip if month is completely after to_date
                if filter_to_date and month_start > filter_to_date:
                    continue
        # Filter by account
        if filters.get("account") and row.get("account") not in filters.get("account"):
            continue

        # Filter by cost center
        if filters.get("cost_center") and row.get("cost_center") not in filters.get("cost_center"):
            continue

        # Filter by project
        if filters.get("project") and row.get("project") not in filters.get("project"):
            continue

        # Filter by branch
        if filters.get("branch") and row.get("branch") not in filters.get("branch"):
            continue

        # Filter by department
        if filters.get("department") and row.get("department") not in filters.get("department"):
            continue

        filtered_data.append(row)

    return filtered_data


def determine_frequency_from_dates(start_date, end_date):
    """Determine frequency based on date range of Multi-Dimensional Budget"""
    start_date = getdate(start_date)
    end_date = getdate(end_date)

    # Calculate difference in days
    diff_days = (end_date - start_date).days + 1

    # Weekly: 7 days
    if diff_days == 7:
        return "Weekly"
    # Monthly: 28-31 days
    elif 28 <= diff_days <= 31:
        return "Monthly"
    # Quarterly: 90-92 days
    elif 90 <= diff_days <= 92:
        return "Quarterly"
    # Half-yearly: 180-184 days
    elif 180 <= diff_days <= 184:
        return "Half-yearly"
    # Yearly: 365-366 days
    elif 365 <= diff_days <= 366:
        return "Yearly"
    else:
        # Default to monthly if no clear match
        return "Monthly"


def get_target_revenue_data(company, branch, start_date, end_date, frequency):
    """Get Target Revenue data matching the frequency and date range using utils.py methodology"""

    if not frequency:
        frequency = frappe.db.get_value("Company Budget Control", {"company": company}, "frequency")
        frequency = (frequency or "").strip().lower()

    # Calculate days difference based on frequency (same as utils.py)
    days_diff = 0
    if frequency == "weekly":
        days_diff = 7
    elif frequency == "monthly":
        days_diff = 30
    elif frequency == "quarterly":
        days_diff = 90
    elif frequency == "half-yearly" or frequency == "6 months":
        days_diff = 180
    elif frequency == "yearly":
        days_diff = 365
    else:
        days_diff = 30  # Default to monthly

    # Use the start_date of the period for backward calculation
    lookup_date = add_days(getdate(start_date), 1)
    prev_date = add_days(lookup_date, -days_diff)

    # Find Target Revenue using the utils.py approach
    target_revenue = frappe.db.sql(
        """
        SELECT
            target_amount,
            earned_amount,
            target_percentage
        FROM `tabTarget Revenue`
        WHERE company = %(company)s
            AND branch = %(branch)s
            AND start_date <= %(prev_date)s
            AND end_date >= %(prev_date)s
            AND docstatus = 1
        ORDER BY creation DESC
        LIMIT 1
    """,
        {"company": company, "branch": branch, "prev_date": prev_date},
        as_dict=True,
    )

    if len(target_revenue) > 0:
        return target_revenue[0]

    # Alternative: Try direct period matching as fallback
    target_revenue = frappe.db.sql(
        """
        SELECT
            target_amount,
            earned_amount,
            target_percentage
        FROM `tabTarget Revenue`
        WHERE company = %(company)s
            AND branch = %(branch)s
            AND start_date <= %(start_date)s
            AND end_date >= %(start_date)s
            AND docstatus = 1
        ORDER BY creation DESC
        LIMIT 1
    """,
        {"company": company, "branch": branch, "start_date": start_date},
        as_dict=True,
    )

    if len(target_revenue) > 0:
        return target_revenue[0]

    # Return default values if no Target Revenue found
    return {"target_amount": 0, "earned_amount": 0, "target_percentage": 0}


def get_multi_dimensional_budget_data(filters):
    """Get data for multi-dimensional budgets with monthly breakdown"""
    data = []

    # Get fiscal year date ranges
    from_fy_data = frappe.db.get_value("Fiscal Year", filters["from_fiscal_year"], ["year_start_date", "year_end_date"])
    to_fy_data = frappe.db.get_value("Fiscal Year", filters["to_fiscal_year"], ["year_start_date", "year_end_date"])

    if not from_fy_data or not to_fy_data:
        frappe.throw(_("Invalid fiscal year selection"))

    from_date = from_fy_data[0]
    to_date = to_fy_data[1]

    # Get multi-dimensional budgets within fiscal year range
    mdb = frappe.qb.DocType("Multi-Dimensional Budget")
    query = (
        frappe.qb.from_(mdb)
        .select(mdb.name, mdb.company, mdb.start_date, mdb.end_date)
        .where(mdb.docstatus == 1)
        .where(mdb.company == filters["company"])
        .where((mdb.start_date <= to_date) & (mdb.end_date >= from_date))
        .orderby(mdb.start_date)
    )
    budgets = query.run(as_dict=True)

    for budget in budgets:
        budget_doc = frappe.get_doc("Multi-Dimensional Budget", budget.name)

        # Apply account filter at budget level if specified
        budget_accounts = budget_doc.accounts
        if filters.get("account"):
            budget_accounts = [acc for acc in budget_doc.accounts if acc.account in filters.get("account")]

        # Determine frequency for Target Revenue matching
        frequency = determine_frequency_from_dates(budget.start_date, budget.end_date)

        # Generate monthly breakdown for each budget
        months = get_months_between_dates(budget.start_date, budget.end_date)

        # Get budget accounts
        for account_row in budget_accounts:
            for month_data in months:
                row = {
                    "budget_name": budget.name,
                    "account": account_row.account,
                    "month": month_data["month_name"],
                    "month_start": month_data["start_date"],
                    "month_end": month_data["end_date"],
                    "month_sort_key": month_data["sort_key"],
                }

                # Calculate monthly budget amount (proportional)
                total_days = (getdate(budget.end_date) - getdate(budget.start_date)).days + 1
                month_days = (getdate(month_data["end_date"]) - getdate(month_data["start_date"])).days + 1
                monthly_budget = (account_row.budget_amount * month_days) / total_days if total_days > 0 else 0
                row["budget_amount"] = monthly_budget

                # Add dimension data and build filters
                dimension_filters = {}
                should_include_row = True
                branch_value = None

                for dim_row in budget_doc.accounting_dimensions:
                    dimension_key = frappe.scrub(dim_row.accounting_dimension).lower()
                    row[dimension_key] = dim_row.accounting_dimension_name
                    dimension_filters[frappe.scrub(dim_row.accounting_dimension)] = dim_row.accounting_dimension_name

                    # Store branch value for Target Revenue lookup
                    if dim_row.accounting_dimension.lower() == "branch":
                        branch_value = dim_row.accounting_dimension_name

                    # Apply dimension filters from report filters
                    filter_key = dimension_key
                    if filters.get(filter_key) and dim_row.accounting_dimension_name not in filters.get(filter_key):
                        should_include_row = False
                        break

                # Skip this row if it doesn't match dimension filters
                if not should_include_row:
                    continue

                # Get Target Revenue data
                target_data = get_target_revenue_data(
                    filters["company"],
                    branch_value or "",
                    month_data["start_date"],
                    month_data["end_date"],
                    frequency,
                )

                row["target_amount"] = flt(target_data.get("target_amount", 0))
                row["earned_amount"] = flt(target_data.get("earned_amount", 0))
                row["target_percentage"] = flt(target_data.get("target_percentage", 0))

                # Calculate allowed amount
                allowed_amount = (
                    monthly_budget * (row["target_percentage"] / 100) if row["target_percentage"] else monthly_budget
                )
                row["allowed_amount"] = allowed_amount

                # Calculate actual expense for this month
                # Prepare args for get_actual_expense function
                args = frappe._dict(
                    {
                        "account": account_row.account,
                        "company": filters["company"],
                        "posting_date": month_data["end_date"],  # Use end date for fiscal year calculation
                        "fiscal_year": get_fiscal_year(month_data["end_date"], company=filters["company"])[0],
                    }
                )

                # Add dimension values to args
                for dim_key, dim_value in dimension_filters.items():
                    args[dim_key] = dim_value

                # Prepare budget structure for get_actual_expense function
                budget_args = frappe._dict(
                    {
                        "start_date": month_data["start_date"],
                        "end_date": month_data["end_date"],
                        "accounting_dimensions": [],
                    }
                )

                # Convert dimension_filters to accounting_dimensions format
                for dim_row in budget_doc.accounting_dimensions:
                    budget_args.accounting_dimensions.append(
                        frappe._dict(
                            {
                                "accounting_dimension": dim_row.accounting_dimension,
                                "accounting_dimension_name": dim_row.accounting_dimension_name,
                            }
                        )
                    )

                actual_amount = get_actual_expense(args, budget_args)

                row["actual_amount"] = actual_amount
                row["variance_amount"] = allowed_amount - actual_amount

                # Calculate percentages
                if allowed_amount:
                    row["utilization_percent"] = (actual_amount / allowed_amount) * 100
                    row["variance_percent"] = ((allowed_amount - actual_amount) / allowed_amount) * 100
                else:
                    row["utilization_percent"] = 0
                    row["variance_percent"] = 0

                data.append(row)

    return data


def get_months_between_dates(start_date, end_date):
    """Get list of months between start and end dates"""
    months = []
    current_date = getdate(start_date)
    end_date = getdate(end_date)

    while current_date <= end_date:
        # Calculate month start and end
        month_start = current_date.replace(day=1)
        next_month = month_start + relativedelta(months=1)
        month_end = next_month - relativedelta(days=1)

        # Adjust for actual budget period
        actual_start = max(month_start, getdate(start_date))
        actual_end = min(month_end, end_date)

        if actual_start <= actual_end:
            month_name = calendar.month_name[current_date.month] + " " + str(current_date.year)
            sort_key = current_date.year * 100 + current_date.month  # For proper chronological sorting
            months.append(
                {
                    "month_name": month_name,
                    "start_date": actual_start,
                    "end_date": actual_end,
                    "sort_key": sort_key,
                }
            )

        current_date = next_month

    return months


def get_chart_data(filters, columns, data):
    """Generate chart data for the report"""
    if not data:
        return None

    # Group data by month for chart
    chart_data = {
        "data": {
            "labels": [],
            "datasets": [
                {"name": "Budget Amount", "values": []},
                {"name": "Allowed Amount", "values": []},
                {"name": "Actual Amount", "values": []},
            ],
        },
        "type": "bar",
        "height": 300,
    }

    # Aggregate data by month with sort key
    month_data = {}
    for row in data:
        month = row.get("month", "Unknown")
        sort_key = row.get("month_sort_key", 0)
        if month not in month_data:
            month_data[month] = {
                "budget_amount": 0,
                "allowed_amount": 0,
                "actual_amount": 0,
                "sort_key": sort_key,
            }

        month_data[month]["budget_amount"] += flt(row.get("budget_amount", 0))
        month_data[month]["allowed_amount"] += flt(row.get("allowed_amount", 0))
        month_data[month]["actual_amount"] += flt(row.get("actual_amount", 0))

    # Sort months chronologically and populate chart data
    sorted_months = sorted(month_data.items(), key=lambda x: x[1]["sort_key"])
    for month, amounts in sorted_months:
        chart_data["data"]["labels"].append(month)
        chart_data["data"]["datasets"][0]["values"].append(amounts["budget_amount"])
        chart_data["data"]["datasets"][1]["values"].append(amounts["allowed_amount"])
        chart_data["data"]["datasets"][2]["values"].append(amounts["actual_amount"])

    return chart_data


def get_summary_data(data):
    """Generate summary statistics for the report"""
    if not data:
        return []

    total_budget = sum(flt(row.get("budget_amount", 0)) for row in data)
    total_allowed = sum(flt(row.get("allowed_amount", 0)) for row in data)
    total_actual = sum(flt(row.get("actual_amount", 0)) for row in data)
    total_variance = total_allowed - total_actual

    summary = [
        {
            "label": _("Total Budget Amount"),
            "value": frappe.utils.fmt_money(total_budget),
            "indicator": "blue",
        },
        {
            "label": _("Total Allowed Amount"),
            "value": frappe.utils.fmt_money(total_allowed),
            "indicator": "orange",
        },
        {
            "label": _("Total Actual Amount"),
            "value": frappe.utils.fmt_money(total_actual),
            "indicator": "green",
        },
        {
            "label": _("Total Variance"),
            "value": frappe.utils.fmt_money(total_variance),
            "indicator": "red" if total_variance < 0 else "green",
        },
    ]

    if total_allowed > 0:
        utilization_percent = (total_actual / total_allowed) * 100
        summary.append(
            {
                "label": _("Overall Utilization %"),
                "value": f"{utilization_percent:.2f}%",
                "indicator": "orange" if utilization_percent > 100 else "blue",
            }
        )

    return summary


def get_message(filters, data):
    """Generate report message"""
    if not data:
        return _("No budget data found for the selected criteria.")

    total_entries = len(data)
    unique_budgets = len(set(row.get("budget_name") for row in data))

    message = _("Report includes {0} entries from {1} Multi-Dimensional Budget(s).").format(
        total_entries, unique_budgets
    )

    return message


@frappe.whitelist()
def export_to_excel(filters: dict | str) -> str:
    """Export report data to Excel with formatting"""
    try:
        columns, data, message, chart, summary = execute(filters)

        if not data:
            frappe.throw(_("No data found for the selected filters"))

        # Create Excel file
        from frappe.utils.xlsxutils import make_xlsx

        xlsx_data = []

        # Add headers
        headers = [col.get("label") or col.get("fieldname") for col in columns]
        xlsx_data.append(headers)

        # Add data rows
        for row in data:
            row_data = []
            for col in columns:
                fieldname = col.get("fieldname")
                value = row.get(fieldname, "")
                row_data.append(value)
            xlsx_data.append(row_data)

        # Create Excel file
        xlsx_file = make_xlsx(xlsx_data, "Multi Dimensional Budget Variance")

        # Save to files
        file_name = f"multi_dimensional_budget_variance_{frappe.utils.now()}.xlsx"
        file_path = f"/files/{file_name}"

        with open(  # nosemgrep: security.frappe-security-file-traversal
            frappe.get_site_path("public", "files", file_name), "wb"
        ) as f:
            f.write(xlsx_file.getvalue())

        return frappe.utils.get_url(file_path)

    except Exception as e:
        frappe.log_error(f"Error exporting to Excel: {str(e)}")
        frappe.throw(_("Error exporting to Excel: {0}").format(str(e)))


@frappe.whitelist()
def create_budget_adjustment(selected_data: list | str, adjustment_details: dict | str) -> dict:
    """Create budget adjustment based on selected variance data"""
    try:
        if not selected_data or not adjustment_details:
            frappe.throw(_("Invalid data provided for budget adjustment"))

        adjustment_type = adjustment_details.get("adjustment_type")
        adjustment_amount = flt(adjustment_details.get("adjustment_amount"))
        reason = adjustment_details.get("reason")

        if not adjustment_amount or adjustment_amount <= 0:
            frappe.throw(_("Adjustment amount must be greater than zero"))

        # Create Journal Entry for budget adjustment
        journal_entry = frappe.new_doc("Journal Entry")
        journal_entry.voucher_type = "Journal Entry"
        journal_entry.company = selected_data[0].get("company")
        journal_entry.posting_date = frappe.utils.today()
        journal_entry.user_remark = f"Budget Adjustment - {adjustment_type}: {reason}"

        # Add accounting entries based on adjustment type
        for row in selected_data:
            account = row.get("account")
            cost_center = row.get("cost_center")

            if adjustment_type == "Increase Budget":
                # Debit expense account
                journal_entry.append(
                    "accounts",
                    {
                        "account": account,
                        "cost_center": cost_center,
                        "debit_in_account_currency": adjustment_amount,
                        "credit_in_account_currency": 0,
                    },
                )
            elif adjustment_type == "Decrease Budget":
                # Credit expense account
                journal_entry.append(
                    "accounts",
                    {
                        "account": account,
                        "cost_center": cost_center,
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": adjustment_amount,
                    },
                )

        # Add balancing entry (temporary account)
        temp_account = frappe.db.get_value(
            "Account",
            {
                "account_name": "Budget Adjustment Account",
                "company": journal_entry.company,
            },
            "name",
        )

        if not temp_account:
            # Create temporary account if it doesn't exist
            temp_account_doc = frappe.new_doc("Account")
            temp_account_doc.account_name = "Budget Adjustment Account"
            temp_account_doc.parent_account = frappe.db.get_value(
                "Account",
                {"account_type": "Temporary", "company": journal_entry.company},
                "name",
            )
            temp_account_doc.company = journal_entry.company
            temp_account_doc.account_type = "Temporary"
            temp_account_doc.insert()
            temp_account = temp_account_doc.name

        # Add balancing entry
        total_adjustment = adjustment_amount * len(selected_data)
        if adjustment_type == "Increase Budget":
            journal_entry.append(
                "accounts",
                {
                    "account": temp_account,
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": total_adjustment,
                },
            )
        else:
            journal_entry.append(
                "accounts",
                {
                    "account": temp_account,
                    "debit_in_account_currency": total_adjustment,
                    "credit_in_account_currency": 0,
                },
            )

        journal_entry.insert()
        journal_entry.submit()

        return {
            "success": True,
            "journal_entry": journal_entry.name,
            "message": f"Budget adjustment created successfully: {journal_entry.name}",
        }

    except Exception as e:
        frappe.log_error(f"Error creating budget adjustment: {str(e)}")
        frappe.throw(_("Error creating budget adjustment: {0}").format(str(e)))


def get_budget_utilization_summary(data):
    """Get summary statistics for budget utilization"""
    if not data:
        return {}

    total_budget = sum(flt(row.get("budget_amount", 0)) for row in data)
    total_actual = sum(flt(row.get("actual_amount", 0)) for row in data)
    total_variance = total_budget - total_actual

    utilization_rate = (total_actual / total_budget * 100) if total_budget > 0 else 0

    over_budget_count = len([row for row in data if flt(row.get("variance", 0)) < 0])
    under_budget_count = len([row for row in data if flt(row.get("variance", 0)) > 0])

    return {
        "total_budget": total_budget,
        "total_actual": total_actual,
        "total_variance": total_variance,
        "utilization_rate": utilization_rate,
        "over_budget_items": over_budget_count,
        "under_budget_items": under_budget_count,
        "total_items": len(data),
    }

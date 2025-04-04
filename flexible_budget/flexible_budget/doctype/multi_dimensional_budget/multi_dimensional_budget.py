# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days, add_months
from datetime import timedelta


class MultiDimensionalBudget(Document):
    def before_insert(self):
        self.validate_date_overlap()


    def validate(self):
        self.set_end_date_from_frequency()
        self.validate_required_fields()
        self.validate_date_overlap()
        self.set_allowed_amount()
    

    def before_submit(self):
        self.validate_allowed_amount()

    
    def validate_required_fields(self):
        if not self.company:
            frappe.throw("Company is required.")

        if not self.start_date:
            frappe.throw("Start Date is required.")

        if not self.end_date:
            frappe.throw("End Date is required.")

        if not self.planned_amount:
            frappe.throw("Planned Amount is required.")

    
    def set_allowed_amount(self):
        """Set allowed budget based on previous Target Revenue target percentage."""

        if (
            not self.start_date
            or not self.end_date
            or not self.company
        ):
            return
        
        settings =  frappe.get_cached_value(
            "Company Budget Control",
            {"company": self.company},
            ["frequency", "target_calculation_method", "fixed_target_revenue_amount"],
            as_dict=True
        )
        if not settings:
            frappe.throw("Company Budget Control settings not found for this company.")
        
        prev_target_start_date, prev_target_end_date = self.get_target_dates(settings)
        if not prev_target_start_date or not prev_target_end_date:
            return
        
        targets = frappe.db.get_all(
            "Target Revenue",
            filters={
                "company": self.company,
                "start_date": ["<=", prev_target_end_date],
                "end_date": [">=", prev_target_start_date],
            },
            fields=["name", "collected_amount"],
            order_by="end_date desc",
            limit=1
        )

        if not len(targets) == 0:
            frappe.throw("No Target Revenue found for the previous period.")
        
        collected_amount = targets[0].collected_amount
        if self.planned_amount == collected_amount:
            return
        
        self.allowed_amount = targets[0].collected_amount
        self.calculate_budget_usage()


    def get_target_dates(self, settings):
        if not settings.frequency:
            return None, None

        prev_target_start_date = None
        prev_target_end_date = None

        start_date = getdate(self.start_date)

        if settings.frequency == "Weekly":
            prev_target_start_date = add_days(start_date, -7)
            prev_target_end_date = add_days(start_date, -1)

        elif settings.frequency == "Monthly":
            prev_target_start_date = add_months(start_date, -1)
            prev_target_end_date = add_days(start_date, -1)

        elif settings.frequency == "Quarterly":
            prev_target_start_date = add_months(start_date, -3)
            prev_target_end_date = add_days(start_date, -1)

        elif settings.frequency in ["Half-yearly", "6 Months"]:
            prev_target_start_date = add_months(start_date, -6)
            prev_target_end_date = add_days(start_date, -1)

        elif settings.frequency == "Yearly":
            prev_target_start_date = add_months(start_date, -12)
            prev_target_end_date = add_days(start_date, -1)

        else:
            frappe.throw("Invalid frequency. Please select a valid frequency.")

        return prev_target_start_date, prev_target_end_date


    def validate_allowed_amount(self):
        if self.allowed_amount <= 0:
            frappe.throw("Allowed Amount must be greater than zero.")

    def validate_date_overlap(self):

        existing_budgets = frappe.get_all(
            "Multi-Dimensional Budget",
            filters={
                "company": self.company,
                "name": ["!=", self.name],  # Exclude current doc in case of edit
                "start_date": ["<=", self.end_date],
                "end_date": [">=", self.start_date]
            },
            fields=["name"]
        )

        if not existing_budgets:
            return


        for budget in existing_budgets:
            other = frappe.get_doc("Multi-Dimensional Budget", budget.name)

            current_set = {
                (row.accounting_dimension.strip(), row.accounting_dimension_name.strip())
                for row in self.accounting_dimensions
            }
            other_set = {
                (row.accounting_dimension.strip(), row.accounting_dimension_name.strip())
                for row in other.accounting_dimensions
            }

            if current_set == other_set:
                frappe.throw(
                    ("A Multi-Dimensional Budget with the same accounting dimension composition already exists for this period (Overlap with: <a href='/app/multi-dimensional-budget/{0}'>{0}</a>)").format(other.name),
                    title=("Duplicate Budget Not Allowed")
                )

    def set_end_date_from_frequency(self):
        if self.start_date and not self.end_date:
            start_date = getdate(self.start_date)
            frequency = self.frequency

            if frequency == "Weekly":
                self.end_date = add_days(start_date, 6)
            elif frequency == "Monthly":
                self.end_date = add_months(start_date, 1) - timedelta(days=1)
            elif frequency == "Quarterly":
                self.end_date = add_months(start_date, 3) - timedelta(days=1)
            elif frequency == "Bi-Annually":
                self.end_date = add_months(start_date, 6) - timedelta(days=1)
            elif frequency == "Yearly":
                self.end_date = add_months(start_date, 12) - timedelta(days=1)             


    def calculate_budget_usage(self, expense_amount=0):
        """Calculate unspent_budget and percentage_used for this budget period."""

        if self.planned_amount == self.allowed_amount:
            return
        
        self.percentage_used = 0
        self.amount_used += expense_amount
        self.unspent = self.allowed_amount - self.amount_used
        if self.allowed_amount > 0 and self.amount_used > 0:
            self.percentage_used = (self.amount_used / self.allowed_amount) * 100
    

@frappe.whitelist()
def custom_doctype_query(doctype, txt, searchfield, start, page_len, filters):
    # Get all Doctype names from your custom Accounting Dimension records
    dim_names = frappe.get_all("Accounting Dimension", pluck="name")

    # Add custom hardcoded doctypes
    extra = ["Cost Center", "Project"]

    # Merge and de-duplicate
    all_doctypes = list(set(dim_names + extra))

    # Filter by search text
    filtered = [dt for dt in all_doctypes if txt.lower() in dt.lower()]
    filtered.sort()

    # Format for Frappe autocomplete [(value, label)]
    return [(dt, dt) for dt in filtered[start:start + page_len]]



# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days, add_months, flt
from datetime import timedelta


class MultiDimensionalBudget(Document):
    def before_insert(self):
        settings = frappe.db.get_value(
            "Company Budget Control",
            {"company": self.company},
            [
                "frequency",
                "applicable_on_material_request",
                "action_if_budget_exceeded_on_mr",
                "applicable_on_purchase_order",
                "action_if_budget_exceeded_on_po",
                "applicable_on_booking_actual_expenses",
                "action_if_budget_exceeded_on_actual"
            ],
            as_dict=True
        )
        self.validate_date_overlap()
        self.set_end_date_from_frequency(settings)
        self.set_budget_actions_from_settings(settings)


    def before_save(self):
        self.validate_required_fields()
        self.validate_date_overlap()
        self.set_allowed_amount()
    

    def before_submit(self):
        self.set_allowed_amount(caller="submit")

    
    def validate_required_fields(self):
        if not self.company:
            frappe.throw("Company is required.")

        if not self.start_date:
            frappe.throw("Start Date is required.")

        if not self.end_date:
            frappe.throw("End Date is required.")

        if not self.planned_amount:
            frappe.throw("Planned Amount is required.")
    

    @frappe.whitelist()
    def set_end_date_from_frequency(self, settings=None):
        if not settings:
            settings = frappe.db.get_value(
                "Company Budget Control",
                {"company": self.company},
                ["frequency"],
                as_dict=True
            )
        
        if self.start_date:
            start_date = getdate(self.start_date)
            
            frequency = (settings.get("frequency") or "").strip().lower() if settings else ""

            if frequency == "weekly":
                self.end_date = add_days(start_date, 6)
            elif frequency == "monthly":
                self.end_date = add_months(start_date, 1) - timedelta(days=1)
            elif frequency == "quarterly":
                self.end_date = add_months(start_date, 3) - timedelta(days=1)
            elif frequency == "half-yearly" or frequency == "6 months":
                self.end_date = add_months(start_date, 6) - timedelta(days=1)
            elif frequency == "yearly":
                self.end_date = add_months(start_date, 12) - timedelta(days=1)
        
        return self.end_date
    
    def set_budget_actions_from_settings(self, settings=None):
        if not settings:
            settings = frappe.db.get_value(
                "Company Budget Control",
                {"company": self.company},
                [
                    "applicable_on_material_request",
                    "action_if_budget_exceeded_on_mr",
                    "applicable_on_purchase_order",
                    "action_if_budget_exceeded_on_po",
                    "applicable_on_booking_actual_expenses",
                    "action_if_budget_exceeded_on_actual"
                ],
                as_dict=True
            )
        
        if settings:
            self.applicable_on_material_request = settings.get("applicable_on_material_request")
            self.action_if_budget_exceeded_on_mr = settings.get("action_if_budget_exceeded_on_mr")
            self.applicable_on_purchase_order = settings.get("applicable_on_purchase_order")
            self.action_if_budget_exceeded_on_po = settings.get("action_if_budget_exceeded_on_po")
            self.applicable_on_booking_actual_expenses = settings.get("applicable_on_booking_actual_expenses")
            self.action_if_budget_exceeded = settings.get("action_if_budget_exceeded_on_actual")

    
    def set_allowed_amount(self, caller=None):
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

        if len(targets) == 0:
            if not caller:
                return
            
            frequency_str = ""
            if settings.frequency == "Weekly":
                frequency_str = "Week"
            elif settings.frequency == "Monthly":
                frequency_str = "Month"
            elif settings.frequency == "Quarterly":
                frequency_str = "Quarter"
            elif settings.frequency in ["Half-yearly", "6 Months"]:
                frequency_str = "Half Year"
            elif settings.frequency == "Yearly":
                frequency_str = "Year"
            
            frappe.throw(f"No Target Revenue found for the previous <b>{frequency_str}</b>.")
        
        collected_amount = targets[0].collected_amount
        # if self.planned_amount == collected_amount:
        #     return
        
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
    

    def validate_date_overlap(self):

        existing_budgets = frappe.db.get_all(
            "Multi-Dimensional Budget",
            filters={
                "company": self.company,
                "name": ["!=", self.name],
                "start_date": ["<=", self.end_date],
                "end_date": [">=", self.start_date]
            },
            fields=["name"]
        )

        if len(existing_budgets) == 0:
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
def get_acc_dimensions():
    documents = frappe.get_all("Accounting Dimension", fields=["name"])

    options = [doc["name"] for doc in documents]

    options.extend(["Cost Center", "Project"])
    
    return options

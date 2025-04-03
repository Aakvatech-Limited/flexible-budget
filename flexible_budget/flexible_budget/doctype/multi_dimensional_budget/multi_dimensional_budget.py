# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days
from datetime import date


class MultiDimensionalBudget(Document):
    def validate(self):
        frappe.msgprint("Validate triggered!")
        if not self.company or not self.from_date or not self.to_date:
            return    
        frappe.msgprint("Validate triggered! 1")
        self.validate_date_overlap()

    def validate_date_overlap(self):
        frappe.msgprint("Validate triggered! 2")

        existing_budgets = frappe.get_all(
            "Multi-Dimensional Budget",
            filters={
                "company": self.company,
                "name": ["!=", self.name],  # Exclude current doc in case of edit
                "from_date": ["<=", self.to_date],
                "to_date": [">=", self.from_date]
            },
            fields=["name"]
        )

        if not existing_budgets:
            return

        frappe.msgprint("Validate triggered! 3")

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

@frappe.whitelist()
def get_acc_dimensions():
		# Fetch all records from "Accounting Dimension"
		documents = frappe.get_all("Accounting Dimension", fields=["name"])

		# Extract names into a list
		options = [doc["name"] for doc in documents]

		#Append Cost Center and Project to the list
		options.extend(["Cost Center", "Project"])
		
		return options
def before_save(self):
        """Set allowed budget based on previous week's Weekly Target Revenue target percentage."""
        if not self.company or not self.week_start_date:
            frappe.throw("Company and Start Date must be set.")

        # Get the date of the previous week's end
        prev_end_date = add_days(date.today(), -1)

        # Fetch the Weekly Target Revenue document
        targets = frappe.get_all(
            "Target Revenue",
            filters={
                "company": self.company,
                "end_date": prev_end_date
            },
            fields=["name"]
        )

        if not targets:
            frappe.throw("No Target Revenue found for the previous week.")

        # Load the full Weekly Target Revenue document
        target = frappe.get_doc("Target Revenue", targets[0]["name"])

        # Use the target_percentage from the class
        target_percentage = target.target_percentage or 0

        # Calculate and set allowed budget
        self.allowed_amount = (self.planned_amount or 0) * ((target_percentage)/100)

        # # Optionally, store a reference to the pulled document
        # self.referenced_weekly_target = weekly_target.name  # optional link field

        # Log for debug
        frappe.logger().info(f"Allowed Amount set to {self.allowed_amount} using {target_percentage}% from {target.name}")


@frappe.whitelist()
def calculate_budget_usage(docname):
    """Calculate unspent_budget and percentage_used for this budget period."""
    doc = frappe.get_doc("Multi-Dimensional Budget", docname)

    total_expenses = 30  # Replace with actual logic

    unspent = (doc.allowed_amount or 0) - total_expenses
    percentage_used = 0
    if (doc.allowed_amount or 0) > 0:
        percentage_used = (total_expenses / float(doc.allowed_amount)) * 100

    # Optionally update the doc (in memory, unless saved later)
    doc.unspent_amount = unspent
    doc.percentage_used = percentage_used

    return {
        "unspent_amount": unspent,
        "spent_amount": total_expenses,
        "percentage_used": percentage_used
    }

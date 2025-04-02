# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days
from datetime import date


class MultiDimensionalBudget(Document):
	pass

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
@frappe.whitelist()
def custom_doctype_query(doctype, txt, searchfield, start, page_len, filters):
    # Get all installed Doctypes
    all_doctypes = frappe.get_all("DocType", pluck="name")

    # Get values from your Accounting Dimension records
    dim_names = frappe.get_all("Accounting Dimension", pluck="name")

    # Add hardcoded extras
    extra = ["Cost Center", "Project"]

    # Merge and filter only those that actually exist
    allowed = list(set(dim_names + extra))
    valid_doctypes = [d for d in allowed if d in all_doctypes]

    # Apply search text
    filtered = [dt for dt in valid_doctypes if txt.lower() in dt.lower()]
    filtered.sort()

    return [(dt, dt) for dt in filtered[start:start + page_len]]

@frappe.whitelist()
def get_dynamic_link_target_for_dimension(dimension):
    """Return the Doctype that should be used as the dynamic link target."""
    if not dimension:
        return ""

    # Hardcoded direct mappings for manually added options
    if dimension in ["Cost Center", "Project"]:
        return dimension

    # Otherwise, fetch from the Accounting Dimension doctype
    try:
        return frappe.db.get_value("Accounting Dimension", dimension, "document_type") or ""
    except Exception as e:
        frappe.log_error(f"Error resolving dynamic link for dimension: {dimension}", title="Dynamic Link Error")
        return ""


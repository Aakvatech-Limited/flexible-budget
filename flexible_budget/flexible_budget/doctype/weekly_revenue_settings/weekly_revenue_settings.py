# Copyright (c) 2025, elius mgani and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WeeklyRevenueSettings(Document):

    def validate(self):
        self.validate_required_fields()
        self.validate_fixed_target_dependencies()
        self.validate_unique_branch_entries()

    def validate_required_fields(self):
        if not self.target_calculation_method:
            frappe.throw("Please select a <b>Target Calculation Method</b>.")

        if not self.default_start_of_the_week:
            frappe.throw("Please select a <b>Default Start of the Week</b>.")

    def validate_fixed_target_dependencies(self):
        if self.target_calculation_method == "Fixed Target":
            if not self.fixed_target_revenue_amount and not self.specifics:
                frappe.throw("You must either set a global <b>Fixed Target Revenue Amount</b> or add at least one branch-specific target in the table.")

            if self.fixed_target_revenue_amount and self.fixed_target_revenue_amount < 0:
                frappe.throw("Fixed Target Revenue Amount cannot be negative.")

    def validate_unique_branch_entries(self):
        """Ensure each branch (or branch + dept/cost center) appears only once in the child table."""
        seen = set()
        for row in self.specifics:
            key = (row.branch, row.department, row.cost_center)
            if key in seen:
                frappe.throw(f"Duplicate target entry found for Branch: <b>{row.branch}</b>, Department: <b>{row.department}</b>, Cost Center: <b>{row.cost_center}</b>.")
            seen.add(key)


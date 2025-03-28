# Copyright (c) 2025, elius mgani and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class FlexibleBudgetSetting(Document):

    def validate(self):
        self.validate_required_fields()
        self.validate_fixed_target_logic()
        self.validate_unique_company()

    def validate_required_fields(self):
        if self.target_calculation_method in ["Fixed Target", "Revenue-Based Target"] and not self.frequency:
            frappe.throw("Please select a <b>Frequency</b> for revenue calculations.")

    def validate_fixed_target_logic(self):
        if self.target_calculation_method == "Fixed Target":
            if not self.fixed_target_revenue_amount:
                frappe.throw("You must set a <b>Fixed Target Revenue Amount</b> or provide values in the <b>Specifics</b> table.")

            if self.fixed_target_revenue_amount and self.fixed_target_revenue_amount < 0:
                frappe.throw("<b>Fixed Target Revenue Amount</b> cannot be Negative.")

    def validate_unique_company(self):
        if frappe.db.exists("Flexible Budget Setting", {"company": self.company, "name": ["!=", self.name]}):
            frappe.throw(f"A Flexible Budget Setting already exists for the company <b>{self.company}</b>.")


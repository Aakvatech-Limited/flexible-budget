# Copyright (c) 2025, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from datetime import timedelta
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from frappe.utils import add_days, add_months, getdate
from flexible_budget.flexible_budget.utils import update_revenue

class TargetRevenue(Document):
    def before_insert(self):
        settings = frappe.db.get_value(
            "Company Budget Control",
            {"company": self.company},
            ["frequency", "target_calculation_method", "fixed_target_revenue_amount"],
            as_dict=True
        )
        self.set_end_date_from_frequency(settings)
        self.set_target_amount_from_settings(settings)
    

    def before_save(self):
        self.check_existing_target_revenue()
        self.calculate_target_percentage()

    
    def on_submit(self):
        enqueue(
            method=update_revenue,
            revenue_doc=self
        )
        

    def check_existing_target_revenue(self):
        existing_target = frappe.db.exists(
            "Target Revenue",
            {
                "company": self.company,
                "name": ["!=", self.name],
                "end_date": (">=", self.start_date),
                "docstatus": ["<", 2]
            }
        )
        if existing_target:
            frappe.throw(f"A Target Revenue already exists for the company <b>'{self.company}'</b> that overlaps with the selected period.")


    def calculate_target_percentage(self):
        settings = frappe.db.get_value(
            "Company Budget Control",
            {"company": self.company},
            ["target_calculation_method"],
            as_dict=True
        )
        if settings:
            method = (settings.get("target_calculation_method") or "").strip().lower()

            if method == "revenue-based target":
                if self.override_earned_amount == 1:
                    self.earned_amount = self.actual_earned_amount

                self.target_amount = self.earned_amount or 0

            if self.target_amount:
                if self.override_earned_amount == 1:
                    self.earned_amount = self.actual_earned_amount

                self.target_percentage = ((self.earned_amount or 0) / (self.target_amount)) * 100


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


    def set_target_amount_from_settings(self, settings):
        if not settings:
            return

        method = (settings.get("target_calculation_method") or "").strip().lower()

        if method == "fixed target":
            self.target_amount = settings.get("fixed_target_revenue_amount") or 0


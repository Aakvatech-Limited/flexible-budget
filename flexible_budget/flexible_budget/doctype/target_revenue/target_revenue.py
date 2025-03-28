# # Copyright (c) 2025, Emanuel Fidelis and contributors
# # For license information, please see license.txt

# import frappe
# from frappe.model.document import Document
# from frappe.utils import add_days, add_months, getdate, nowdate  # Import nowdate for getting the current date
# from datetime import timedelta

# class TargetRevenue(Document):

#     def validate(self):
#         if self.is_new():
#           self.check_existing_target_revenue()

#         self.set_end_date_from_frequency()
#         self.set_target_amount_from_settings()
#         self.calculate_target_percentage()

#     def check_existing_target_revenue(self):
#         # Check if there is an active Target Revenue for the same company
#         existing_target = frappe.db.exists(
#             "Target Revenue",
#             {
#                 "company": self.company,
#                 "end_date": (">=", self.start_date)
#             }
#         )
#         if existing_target:
#             frappe.throw(f"A Target Revenue already exists for the company <b>'{self.company}'</b> that overlaps with the selected period.")

#     def calculate_target_percentage(self):
#         settings = frappe.db.get_value(
#             "Flexible Budget Setting",
#             {"company": self.company},
#             ["enable_auto_calculation"],
#             as_dict=True
#         )
#         if settings and settings.get("enable_auto_calculation") and self.target_amount:
#             self.target_percentage = (self.collected_amount / self.target_amount) * 100

#     def set_end_date_from_frequency(self):
#         if self.start_date and not self.end_date:  
#             start_date = getdate(self.start_date)
#             settings = frappe.db.get_value(
#                 "Flexible Budget Setting",
#                 {"company": self.company},
#                 ["frequency"],
#                 as_dict=True
#             )
#             frequency = (settings.get("frequency") or "").strip().lower() if settings else ""

#             if frequency == "weekly":
#                 self.end_date = add_days(start_date, 6)
#             elif frequency == "monthly":
#                 self.end_date = add_months(start_date, 1) - timedelta(days=1)
#             elif frequency == "quarterly":
#                 self.end_date = add_months(start_date, 3) - timedelta(days=1)
#             elif frequency == "half-yearly":
#                 self.end_date = add_months(start_date, 6) - timedelta(days=1)
#             elif frequency == "yearly":
#                 self.end_date = add_months(start_date, 12) - timedelta(days=1)
                
#     def set_target_amount_from_settings(self):
#         settings = frappe.db.get_value(
#             "Flexible Budget Setting",
#             {"company": self.company},
#             ["target_calculation_method", "fixed_target_revenue_amount"],
#             as_dict=True
#         )

#         if not settings:
#             return

#         method = (settings.get("target_calculation_method") or "").strip().lower()

#         if method == "fixed target":
#             self.target_amount = settings.get("fixed_target_revenue_amount") or 0

#         elif method == "revenue-based target":
#             self.target_amount = self.collected_amount or 0



# Copyright (c) 2025, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_months, getdate
from datetime import timedelta

class TargetRevenue(Document):

    def validate(self):
        if self.is_new():
            self.check_existing_target_revenue()

        self.set_end_date_from_frequency()
        self.set_target_amount_from_settings()
        self.calculate_target_percentage()

    def check_existing_target_revenue(self):
        # Check if there is an active Target Revenue for the same company
        existing_target = frappe.db.exists(
            "Target Revenue",
            {
                "company": self.company,
                "end_date": (">=", self.start_date)
            }
        )
        if existing_target:
            frappe.throw(f"A Target Revenue already exists for the company <b>'{self.company}'</b> that overlaps with the selected period.")

    def calculate_target_percentage(self):
        settings = frappe.db.get_value(
            "Flexible Budget Setting",
            {"company": self.company},
            ["enable_auto_calculation", "target_calculation_method"],
            as_dict=True
        )
        if settings and settings.get("enable_auto_calculation"):
            method = (settings.get("target_calculation_method") or "").strip().lower()

            # If revenue-based, target_amount should match collected_amount
            if method == "revenue-based target":
                self.target_amount = self.collected_amount or 0

            if self.target_amount:
                self.target_percentage = (self.collected_amount or 0 / self.target_amount) * 100

    def set_end_date_from_frequency(self):
        if self.start_date and not self.end_date:
            start_date = getdate(self.start_date)
            settings = frappe.db.get_value(
                "Flexible Budget Setting",
                {"company": self.company},
                ["frequency"],
                as_dict=True
            )
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

    def set_target_amount_from_settings(self):
        settings = frappe.db.get_value(
            "Flexible Budget Setting",
            {"company": self.company},
            ["target_calculation_method", "fixed_target_revenue_amount"],
            as_dict=True
        )

        if not settings:
            return

        method = (settings.get("target_calculation_method") or "").strip().lower()

        if method == "fixed target":
            self.target_amount = settings.get("fixed_target_revenue_amount") or 0

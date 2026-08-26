# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, getdate


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
				"action_if_budget_exceeded_on_actual",
			],
			as_dict=True,
		)
		self.validate_date_overlap()
		self.validate_accounting_dimensions()
		self.validate_accounts()
		self.set_end_date_from_frequency(settings)
		self.set_budget_actions_from_settings(settings)

	def before_save(self):
		self.validate_required_fields()
		self.validate_date_overlap()
		self.validate_accounting_dimensions()
		self.validate_accounts()
		self.calculate_total_amount()

	def before_submit(self):
		self.validate_branch_dimension()

	def validate_required_fields(self):
		if not self.company:
			frappe.throw(_("Company is required."))

		if not self.start_date:
			frappe.throw(_("Start Date is required."))

		if not self.end_date:
			frappe.throw(_("End Date is required."))

	@frappe.whitelist()
	def set_end_date_from_frequency(self, settings: dict | None = None):
		if not settings:
			settings = frappe.db.get_value(
				"Company Budget Control",
				{"company": self.company},
				["frequency"],
				as_dict=True,
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
					"action_if_budget_exceeded_on_actual",
				],
				as_dict=True,
			)

		if settings:
			self.applicable_on_material_request = settings.get("applicable_on_material_request")
			self.action_if_budget_exceeded_on_mr = settings.get("action_if_budget_exceeded_on_mr")
			self.applicable_on_purchase_order = settings.get("applicable_on_purchase_order")
			self.action_if_budget_exceeded_on_po = settings.get("action_if_budget_exceeded_on_po")
			self.applicable_on_booking_actual_expenses = settings.get("applicable_on_booking_actual_expenses")
			self.action_if_budget_exceeded = settings.get("action_if_budget_exceeded_on_actual")

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
			frappe.throw(_("Invalid frequency. Please select a valid frequency."))

		return prev_target_start_date, prev_target_end_date

	def validate_date_overlap(self):
		filters = {
			"company": self.company,
			# "name": ["!=", self.name],
			"start_date": ["<=", self.end_date],
			"end_date": [">=", self.start_date],
			"docstatus": ["<", 2],
		}

		if self.name:
			filters["name"] = ["!=", self.name]

		existing_budgets = frappe.db.get_all("Multi-Dimensional Budget", filters=filters, fields=["name"])

		if len(existing_budgets) == 0:
			return

		for budget in existing_budgets:
			other = frappe.get_doc("Multi-Dimensional Budget", budget.name)

			current_set = self.get_dimension_set()
			other_set = other.get_dimension_set()

			if current_set == other_set:
				frappe.throw(
					_(
						"A Multi-Dimensional Budget with the same accounting dimension composition already exists for this period (Overlap with: {0})"
					).format(frappe.utils.get_link_to_form("Multi-Dimensional Budget", other.name)),
					title=_("Duplicate Budget Not Allowed"),
				)

	def get_dimension_set(self):
		return {
			((row.accounting_dimension or "").strip(), (row.accounting_dimension_name or "").strip())
			for row in self.accounting_dimensions
		}

	def validate_accounts(self):
		account_list = []
		for d in self.get("accounts"):
			if d.account:
				account_details = frappe.get_cached_value(
					"Account",
					d.account,
					["is_group", "company", "report_type"],
					as_dict=1,
				)
				if account_details.is_group:
					frappe.throw(_("Budget cannot be assigned against Group Account {0}").format(d.account))

				elif account_details.company != self.company:
					frappe.throw(
						_("Account {0} does not belong to company {1}").format(d.account, self.company)
					)
				elif account_details.report_type != "Profit and Loss":
					frappe.throw(
						_(
							"Budget cannot be assigned against {0}, as it's not an Income or Expense account"
						).format(d.account)
					)

				if d.account in account_list:
					frappe.throw(_("Account {0} has been entered multiple times").format(d.account))
				else:
					account_list.append(d.account)

	def validate_accounting_dimensions(self):
		"""Validate if the same accounting dimension is selected multiple times and if it belong to the same company."""

		dimensions = []
		for row in self.accounting_dimensions:
			if row.accounting_dimension not in dimensions:
				dimensions.append(row.accounting_dimension)
			else:
				frappe.throw(_("Duplicate accounting dimension found: {0}").format(row.accounting_dimension))

			if frappe.get_meta(row.accounting_dimension).get_field("company"):
				if row.accounting_dimension_name:
					company = frappe.get_cached_value(
						row.accounting_dimension,
						row.accounting_dimension_name,
						"company",
					)
					if company != self.company:
						frappe.throw(
							_("Accounting Dimension {0} does not belong to company {1}").format(
								row.accounting_dimension_name, self.company
							)
						)

	def validate_branch_dimension(self):
		"""Validate if the branch dimension is selected and if it belongs to the same company."""

		has_branch = False
		for row in self.accounting_dimensions:
			if row.accounting_dimension == "Branch":
				has_branch = True
				break

		if not has_branch:
			frappe.throw(
				_("Branch dimension is required. <br><b>Branch</b> as accounting dimension must be selected")
			)

	@frappe.whitelist()
	def calculate_total_amount(self, caller: str | None = None) -> float:
		"""Calculate the total budget amount from all accounts in the child table."""

		total_amount = 0.0

		for account_row in self.get("accounts", []):
			if account_row.budget_amount:
				total_amount += account_row.budget_amount

		if caller:
			return total_amount

		self.total_budget_amount = total_amount


@frappe.whitelist()
def get_acc_dimensions():
	documents = frappe.get_all("Accounting Dimension", fields=["name"])

	options = [doc["name"] for doc in documents]

	options.extend(["Cost Center", "Project"])

	return options

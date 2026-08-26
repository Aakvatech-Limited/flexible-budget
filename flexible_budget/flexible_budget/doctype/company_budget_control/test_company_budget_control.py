# Copyright (c) 2025, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from flexible_budget.tests.utils import COMPANY, make_company_budget_control


class TestCompanyBudgetControl(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_autoname_is_company(self):
		doc = make_company_budget_control()
		self.assertEqual(doc.name, COMPANY)

	def test_frequency_is_required(self):
		self.assertRaisesRegex(frappe.ValidationError, "Frequency", make_company_budget_control, frequency="")

	def test_fixed_target_requires_amount(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			"Fixed Target Revenue Amount",
			make_company_budget_control,
			fixed_target_revenue_amount=0,
		)

	def test_fixed_target_rejects_negative_amount(self):
		self.assertRaisesRegex(
			frappe.ValidationError, "Negative", make_company_budget_control, fixed_target_revenue_amount=-1
		)

	def test_revenue_based_target_needs_no_fixed_amount(self):
		doc = make_company_budget_control(
			target_calculation_method="Revenue-Based Target", fixed_target_revenue_amount=0
		)
		self.assertEqual(doc.target_calculation_method, "Revenue-Based Target")

	def test_one_control_per_company(self):
		make_company_budget_control()
		duplicate = frappe.get_doc(
			{
				"doctype": "Company Budget Control",
				"company": COMPANY,
				"frequency": "Monthly",
				"target_calculation_method": "Revenue-Based Target",
			}
		)
		self.assertRaisesRegex(frappe.ValidationError, "already exists", duplicate.insert)

	def test_update_keeps_same_company(self):
		doc = make_company_budget_control()
		doc.frequency = "Weekly"
		doc.save()
		self.assertEqual(frappe.db.get_value("Company Budget Control", COMPANY, "frequency"), "Weekly")

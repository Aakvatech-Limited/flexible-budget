"""Framework wiring: hooks, patches, custom fields, scheduler, permissions."""

import os

import frappe
from frappe.desk.form.meta import get_meta as get_form_meta
from frappe.tests import IntegrationTestCase

from flexible_budget import hooks
from flexible_budget.patches import create_custom_fields, create_property_setter
from flexible_budget.tests.utils import make_test_user

BUDGET_FIELDS = ("budget_remarks", "budget_overview", "bypass_budget_validation")
TRANSACTION_DOCTYPES = (
	"Purchase Order",
	"Material Request",
	"Purchase Invoice",
	"Journal Entry",
	"Expense Claim",
)


class TestHooks(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_doc_event_handlers_resolve(self):
		for doctype, events in hooks.doc_events.items():
			self.assertTrue(frappe.db.exists("DocType", doctype), doctype)
			for event, handler in events.items():
				self.assertTrue(callable(frappe.get_attr(handler)), f"{doctype}.{event}")

	def test_install_and_migrate_hooks_resolve(self):
		self.assertEqual(hooks.after_install, hooks.after_migrate)
		for handler in hooks.after_migrate:
			self.assertTrue(callable(frappe.get_attr(handler)))
		self.assertTrue(callable(frappe.get_attr(hooks.before_tests)))

	def test_scheduler_event_is_valid_and_synced(self):
		from croniter import croniter
		from frappe.core.doctype.scheduled_job_type.scheduled_job_type import sync_jobs

		cron = hooks.scheduler_events["cron"]
		self.assertEqual(list(cron), ["30 0 * * *"])
		self.assertTrue(croniter.is_valid("30 0 * * *"))
		method = cron["30 0 * * *"][0]
		self.assertTrue(callable(frappe.get_attr(method)))
		sync_jobs()
		job = frappe.get_doc("Scheduled Job Type", {"method": method})
		self.assertEqual(job.frequency, "Cron")
		self.assertEqual(job.cron_format, "30 0 * * *")

	def test_list_view_scripts_exist(self):
		for doctype, path in hooks.doctype_list_js.items():
			self.assertTrue(frappe.db.exists("DocType", doctype))
			resolved = frappe.get_app_path("flexible_budget", *path.strip("/").split("/"))
			self.assertTrue(os.path.exists(resolved), resolved)
			self.assertIn("listview_settings", get_form_meta(doctype).get("__list_js") or "")

	def test_custom_fields_installed(self):
		for doctype in TRANSACTION_DOCTYPES:
			meta = frappe.get_meta(doctype)
			for fieldname in BUDGET_FIELDS:
				self.assertTrue(meta.has_field(fieldname), f"{doctype}.{fieldname}")
			self.assertEqual(meta.get_field("bypass_budget_validation").fieldtype, "Check")
			self.assertEqual(meta.get_field("budget_overview").fieldtype, "Text Editor")

	def test_custom_field_patch_is_idempotent(self):
		before = frappe.db.count("Custom Field", {"fieldname": ["in", BUDGET_FIELDS]})
		create_custom_fields.execute()
		self.assertEqual(frappe.db.count("Custom Field", {"fieldname": ["in", BUDGET_FIELDS]}), before)
		self.assertEqual(before, len(TRANSACTION_DOCTYPES) * len(BUDGET_FIELDS))

	def test_custom_field_patch_recreates_missing_field(self):
		name = frappe.db.get_value("Custom Field", {"dt": "Purchase Order", "fieldname": "budget_remarks"})
		frappe.delete_doc("Custom Field", name, force=1)
		self.assertFalse(
			frappe.db.exists("Custom Field", {"dt": "Purchase Order", "fieldname": "budget_remarks"})
		)
		create_custom_fields.execute()
		self.assertTrue(
			frappe.db.exists("Custom Field", {"dt": "Purchase Order", "fieldname": "budget_remarks"})
		)

	def test_property_setter_patch(self):
		before = frappe.db.count("Property Setter")
		create_property_setter.execute()
		self.assertEqual(frappe.db.count("Property Setter"), before)
		create_property_setter.create_property_setter_from_json(
			[
				{
					"name": "Purchase Order-budget_remarks-bold",
					"doctype_or_field": "DocField",
					"doc_type": "Purchase Order",
					"field_name": "budget_remarks",
					"property": "bold",
					"property_type": "Check",
					"value": "1",
				}
			]
		)
		self.assertEqual(
			frappe.db.get_value(
				"Property Setter",
				{"doc_type": "Purchase Order", "field_name": "budget_remarks", "property": "bold"},
				"value",
			),
			"1",
		)

	def test_export_custom_fields(self):
		names = frappe.get_all(
			"Custom Field", {"dt": "Purchase Order", "fieldname": ["in", BUDGET_FIELDS]}, pluck="name"
		)
		exported = create_custom_fields.export_custom_fields(frappe.as_json(names))
		self.assertIsInstance(exported, str)
		for fieldname in BUDGET_FIELDS:
			self.assertIn(fieldname, exported)
		self.assertIn(create_custom_fields.export_custom_fields, frappe.whitelisted)

	def test_module_and_doctypes_registered(self):
		self.assertTrue(frappe.db.exists("Module Def", "Flexible Budget"))
		doctypes = set(frappe.get_all("DocType", {"module": "Flexible Budget"}, pluck="name"))
		self.assertEqual(
			doctypes,
			{
				"Multi-Dimensional Budget",
				"Multi-Dimensional Budget Account",
				"Multi-Dimensional Budget Detail",
				"Target Revenue",
				"Company Budget Control",
			},
		)
		self.assertTrue(frappe.db.exists("Report", "Multi-Dimensional Budget Variance"))

	def test_role_permissions(self):
		accounts_manager = make_test_user("fb_accounts_manager@example.com", ["Accounts Manager"])
		system_manager = make_test_user("fb_system_manager@example.com", ["System Manager"])
		accounts_user = make_test_user("fb_accounts_user@example.com", ["Accounts User"])
		for ptype in ("read", "write", "create", "submit", "cancel", "amend"):
			self.assertTrue(
				frappe.has_permission("Multi-Dimensional Budget", ptype, user=accounts_manager), ptype
			)
		self.assertFalse(frappe.has_permission("Multi-Dimensional Budget", "read", user=accounts_user))
		for ptype in ("read", "write", "create"):
			self.assertTrue(
				frappe.has_permission("Company Budget Control", ptype, user=system_manager), ptype
			)
			self.assertTrue(frappe.has_permission("Target Revenue", ptype, user=system_manager), ptype)
		report_roles = {
			row.role for row in frappe.get_doc("Report", "Multi-Dimensional Budget Variance").roles
		}
		self.assertEqual(report_roles, {"Accounts Manager", "Accounts User", "Auditor"})

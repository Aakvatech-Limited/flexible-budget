"""Desk UI checks (client scripts, list views, query report) with Playwright against a live site."""

import json
import os
import unittest

from flexible_budget.tests.e2e.client import (
	BASE_URL,
	BRANCH,
	BUDGET_START,
	COMPANY,
	EXPENSE_ACCOUNT,
	Client,
	ensure_fixtures,
	purchase_order,
	requires_live_site,
)

COVERAGE_FILE = os.environ.get("FB_E2E_JS_COVERAGE")
SCRIPT_MARKERS = {
	"multi_dimensional_budget.js": 'frappe.ui.form.on("Multi-Dimensional Budget"',
	"target_revenue.js": 'frappe.ui.form.on("Target Revenue"',
	"company_budget_control.js": 'frappe.ui.form.on("Company Budget Control"',
	"multi_dimensional_budget_variance.js": 'frappe.query_reports["Multi-Dimensional Budget Variance"]',
	"custom_field.js": 'frappe.listview_settings["Custom Field"]',
	"property_setter.js": 'frappe.listview_settings["Property Setter"]',
}


@requires_live_site
class TestDeskUi(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		from playwright.sync_api import sync_playwright

		cls.client = Client()
		cls.budget = ensure_fixtures(cls.client)
		cls.playwright = sync_playwright().start()
		cls.browser = cls.playwright.chromium.launch(headless=True)
		cls.context = cls.browser.new_context(viewport={"width": 1400, "height": 960}, accept_downloads=True)
		cls.context.add_cookies([{"name": "sid", "value": cls.client.sid, "url": BASE_URL}])
		cls.js_coverage = {}
		cls.created = []

	@classmethod
	def tearDownClass(cls):
		cls.browser.close()
		cls.playwright.stop()
		for doctype, name in reversed(cls.created):
			cls.client.delete(doctype, name)
		if COVERAGE_FILE:
			with open(COVERAGE_FILE, "w") as handle:
				json.dump(cls.js_coverage, handle, indent=1)

	def setUp(self):
		self.page = self.context.new_page()
		self.cdp = self.context.new_cdp_session(self.page)
		self.cdp.send("Debugger.enable")
		self.cdp.send("Profiler.enable")
		self.cdp.send("Profiler.startPreciseCoverage", {"callCount": True, "detailed": True})

	def tearDown(self):
		for entry in self.cdp.send("Profiler.takePreciseCoverage")["result"]:
			self.record_coverage(entry)
		self.cdp.detach()
		self.page.close()

	def record_coverage(self, entry):
		"""Keep V8 function counts for the app's own (eval'd, URL-less) client scripts."""
		if "/assets/" in entry.get("url", ""):
			return
		try:
			source = self.cdp.send("Debugger.getScriptSource", {"scriptId": entry["scriptId"]})[
				"scriptSource"
			]
		except Exception:
			return
		for script, marker in SCRIPT_MARKERS.items():
			if marker not in source:
				continue
			functions = self.js_coverage.setdefault(script, {})
			for function in entry["functions"]:
				start = function["ranges"][0]["startOffset"]
				line = source.count("\n", 0, start) + 1
				name = function["functionName"] or "anonymous"
				key = f"{name}@L{line}"
				covered = function["ranges"][0]["count"] > 0
				functions[key] = functions.get(key, False) or covered

	def open(self, route):
		self.page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
		self.page.wait_for_selector(".page-container:visible, .layout-main", timeout=20000)

	def wait_for_js(self, expression, timeout=15000):
		self.page.wait_for_function(expression, timeout=timeout)
		return self.page.evaluate(expression)

	def test_budget_form_sets_end_date_from_frequency(self):
		self.open("/app/multi-dimensional-budget/new")
		self.page.evaluate(f"cur_frm.set_value('company', {COMPANY!r})")
		self.page.evaluate("cur_frm.set_value('start_date', '2027-05-01')")
		self.assertEqual(self.wait_for_js("cur_frm.doc.end_date"), "2027-05-31")

	def test_budget_form_dimension_options_and_account_query(self):
		self.open("/app/multi-dimensional-budget/new")
		self.page.evaluate(f"cur_frm.set_value('company', {COMPANY!r})")
		options = self.wait_for_js(
			"(cur_frm.fields_dict.accounting_dimensions.grid.docfields.find(f => f.fieldname == 'accounting_dimension') || {}).options"
		)
		for expected in ("Branch", "Cost Center", "Project"):
			self.assertIn(expected, options.split("\n"))
		query = self.page.evaluate("cur_frm.fields_dict.accounts.grid.get_field('account').get_query()")
		self.assertEqual(
			query["filters"], {"company": COMPANY, "report_type": "Profit and Loss", "is_group": 0}
		)

	def test_budget_form_total_amount_follows_rows(self):
		self.open("/app/multi-dimensional-budget/new")
		self.page.evaluate(f"cur_frm.set_value('company', {COMPANY!r})")
		self.page.evaluate(
			f"""(() => {{
				const row = cur_frm.add_child('accounts', {{account: {EXPENSE_ACCOUNT!r}, budget_amount: 0}});
				cur_frm.refresh_field('accounts');
				frappe.model.set_value(row.doctype, row.name, 'budget_amount', 1500);
			}})()"""
		)
		self.assertEqual(self.wait_for_js("cur_frm.doc.total_budget_amount == 1500 ? 1500 : null"), 1500)
		self.page.evaluate(
			"frappe.model.set_value(cur_frm.doc.accounts[0].doctype, cur_frm.doc.accounts[0].name, 'budget_amount', 250)"
		)
		self.assertEqual(self.wait_for_js("cur_frm.doc.total_budget_amount == 250 ? 250 : null"), 250)

	def test_budget_form_validate_dedupes_dimensions(self):
		for row in self.client.get_list(
			"Multi-Dimensional Budget", {"start_date": "2027-06-01", "docstatus": 0}
		):
			self.client.delete("Multi-Dimensional Budget", row["name"])
		self.open("/app/multi-dimensional-budget/new")
		self.page.evaluate(f"cur_frm.set_value('company', {COMPANY!r})")
		self.page.evaluate("cur_frm.set_value('start_date', '2027-06-01')")
		self.wait_for_js("cur_frm.doc.end_date")
		self.page.evaluate(
			f"""(() => {{
				cur_frm.add_child('accounting_dimensions', {{accounting_dimension: 'Branch', accounting_dimension_name: {BRANCH!r}}});
				cur_frm.add_child('accounting_dimensions', {{accounting_dimension: 'Branch', accounting_dimension_name: {BRANCH!r}}});
				cur_frm.add_child('accounts', {{account: {EXPENSE_ACCOUNT!r}, budget_amount: 10}});
				cur_frm.refresh();
			}})()"""
		)
		self.page.evaluate("cur_frm.save()")
		self.wait_for_js(
			"!cur_frm.is_new() && !cur_frm.is_dirty() || document.querySelector('.modal.show .msgprint')"
		)
		self.assertIsNone(
			self.page.query_selector(".modal.show .msgprint"),
			self.page.evaluate("(document.querySelector('.modal.show .msgprint') || {}).innerText"),
		)
		name = self.page.evaluate("cur_frm.doc.name")
		self.created.append(("Multi-Dimensional Budget", name))
		self.assertEqual(self.page.evaluate("cur_frm.doc.accounting_dimensions.length"), 1)
		self.assertEqual(self.client.get("Multi-Dimensional Budget", name)["total_budget_amount"], 10)

	def test_target_revenue_form_sets_end_date(self):
		self.open("/app/target-revenue/new")
		self.page.evaluate(f"cur_frm.set_value('company', {COMPANY!r})")
		self.page.evaluate("cur_frm.set_value('start_date', '2027-05-01')")
		self.assertEqual(self.wait_for_js("cur_frm.doc.end_date"), "2027-05-31")

	def test_company_budget_control_income_account_query(self):
		self.open(f"/app/company-budget-control/{COMPANY}")
		query = self.page.evaluate("cur_frm.fields_dict.group_income_account.get_query()")
		self.assertEqual(query["filters"], {"root_type": "Income", "is_group": 1, "company": COMPANY})

	def test_purchase_order_form_shows_budget_section(self):
		po = self.client.insert(purchase_order(600))
		self.created.append(("Purchase Order", po["name"]))
		self.open(f"/app/purchase-order/{po['name']}")
		self.wait_for_js(
			f"window.cur_frm && cur_frm.doc.name === {po['name']!r} && Boolean(cur_frm.fields_dict.budget_overview)"
		)
		self.assertTrue(
			self.page.evaluate(
				"Boolean(cur_frm.fields_dict.bypass_budget_validation && cur_frm.fields_dict.flexible_budget)"
			)
		)
		self.assertIn("Total Expense", self.page.evaluate("cur_frm.doc.budget_overview"))
		self.assertEqual(self.page.evaluate("cur_frm.fields_dict.flexible_budget.df.collapsible"), 1)
		self.page.evaluate("cur_frm.fields_dict.flexible_budget.collapse(false)")
		self.assertTrue(
			self.page.locator(".frappe-control[data-fieldname='budget_overview']").first.is_visible()
		)

	def test_variance_report_renders_rows_chart_and_colors(self):
		fiscal_year = self.client.get_list(
			"Fiscal Year", {"year_start_date": ["<=", BUDGET_START], "year_end_date": [">=", BUDGET_START]}
		)[0]["name"]
		self.open("/app/query-report/Multi-Dimensional Budget Variance")
		self.wait_for_js("frappe.query_report && frappe.query_report.filters.length > 0")
		filters = {
			"company": COMPANY,
			"from_fiscal_year": fiscal_year,
			"to_fiscal_year": fiscal_year,
			"branch": [BRANCH],
		}
		self.page.evaluate(f"frappe.query_report.set_filter_value({json.dumps(filters)})")
		self.page.evaluate("frappe.query_report.refresh()")
		self.page.wait_for_selector(".dt-row-0", timeout=30000)
		rows = self.page.evaluate("frappe.query_report.data.length")
		self.assertGreaterEqual(rows, 1)
		self.assertEqual(self.page.evaluate("frappe.query_report.data[0].month"), "February 2027")
		self.assertTrue(self.page.locator(".chart-container svg, .frappe-chart").count() >= 1)
		self.assertGreaterEqual(
			self.page.locator(".report-summary .summary-item, .report-summary [class*=summary]").count(), 4
		)
		self.assertGreaterEqual(self.page.locator(".dt-cell__content span[style*='color']").count(), 1)

	def check_export_menu(self, doctype, download_name):
		self.open(f"/app/{doctype}")
		self.page.wait_for_selector(".list-row-container", timeout=20000)
		self.assertTrue(
			self.page.evaluate(
				"cur_list.page.menu.find('a').filter((i, a) => a.innerText.includes('Export Selected')).length == 1"
			)
		)
		self.page.evaluate(
			"cur_list.page.menu.find('a').filter((i, a) => a.innerText.includes('Export Selected')).click()"
		)
		self.page.wait_for_selector(".modal.show .msgprint", timeout=10000)
		self.assertIn(
			"Please select at least one document",
			self.page.locator(".modal.show .msgprint").first.inner_text(),
		)
		for _attempt in range(10):  # bootstrap ignores hide() while the fade-in is still running
			self.page.wait_for_timeout(400)
			self.page.keyboard.press("Escape")
			if not self.page.query_selector(".modal.show") and not self.page.query_selector(
				".modal-backdrop"
			):
				break
		self.assertIsNone(self.page.query_selector(".modal.show"))
		self.page.locator(".list-row-checkbox").first.check(force=True)
		with self.page.expect_download(timeout=20000) as download_info:
			self.page.evaluate(
				"cur_list.page.menu.find('a').filter((i, a) => a.innerText.includes('Export Selected')).click()"
			)
		download = download_info.value
		self.assertEqual(download.suggested_filename, download_name)
		with open(download.path()) as handle:
			data = json.load(handle)
		self.assertEqual(len(data), 1)
		self.assertIn("doctype", data[0])

	def test_custom_field_list_export(self):
		self.check_export_menu("custom-field", "exported_custom_fields.json")

	def test_property_setter_list_export(self):
		self.check_export_menu("property-setter", "exported_property_setters.json")

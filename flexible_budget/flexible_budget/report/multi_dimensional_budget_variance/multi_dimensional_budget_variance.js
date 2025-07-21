// Copyright (c) 2025, elius mgani and contributors
// For license information, please see license.txt

frappe.query_reports["Multi-Dimensional Budget Variance"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 0
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 0
		},
		{
			"fieldname": "from_fiscal_year",
			"label": __("From Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"reqd": 1,
		},
		{
			"fieldname": "to_fiscal_year",
			"label": __("To Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"reqd": 1,
		},
		{
			"fieldname": "account",
			"label": __("Account"),
			"fieldtype": "MultiSelectList",
			"options": "Account",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Account', txt, {
					"company": frappe.query_report.get_filter_value('company'),
					// "account_type": ["in", ["Expense Account", "Income Account"]]
				});
			}
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "MultiSelectList",
			"options": "Cost Center",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Cost Center', txt, {
					"company": frappe.query_report.get_filter_value('company')
				});
			}
		},
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "MultiSelectList",
			"options": "Project",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Project', txt, {
					"company": frappe.query_report.get_filter_value('company')
				});
			}
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "MultiSelectList",
			"options": "Branch",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Branch', txt, {
					// "company": frappe.query_report.get_filter_value('company')
				});
			}
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "MultiSelectList",
			"options": "Department",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Department', txt, {
					"company": frappe.query_report.get_filter_value('company')
				});
			}
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Color code variance columns
		if (column.fieldname && column.fieldname.includes('variance_amount') && data) {
			const numValue = parseFloat(data[column.fieldname]);
			if (!isNaN(numValue)) {
				if (numValue < 0) {
					// Negative variance (over budget) - red
					value = `<span style="color: #d73925; font-weight: bold;">${value}</span>`;
				} else if (numValue > 0) {
					// Positive variance (under budget) - green
					value = `<span style="color: #27ae60; font-weight: bold;">${value}</span>`;
				}
			}
		}
		
		// Color code variance percentage columns
		if (column.fieldname && column.fieldname.includes('variance_percent') && data) {
			const numValue = parseFloat(data[column.fieldname]);
			if (!isNaN(numValue)) {
				if (numValue < -10) {
					// Significantly over budget - red
					value = `<span style="color: #d73925; font-weight: bold;">${value}</span>`;
				} else if (numValue < 0) {
					// Slightly over budget - orange
					value = `<span style="color: #f39c12; font-weight: bold;">${value}</span>`;
				} else if (numValue > 0) {
					// Under budget - green
					value = `<span style="color: #27ae60; font-weight: bold;">${value}</span>`;
				}
			}
		}

		// Color code utilization percentage
		if (column.fieldname && column.fieldname.includes('utilization_percent') && data) {
			const numValue = parseFloat(data[column.fieldname]);
			if (!isNaN(numValue)) {
				if (numValue > 100) {
					// Over-utilized - red
					value = `<span style="color: #d73925; font-weight: bold;">${value}</span>`;
				} else if (numValue > 90) {
					// High utilization - orange
					value = `<span style="color: #f39c12; font-weight: bold;">${value}</span>`;
				} else if (numValue > 50) {
					// Good utilization - green
					value = `<span style="color: #27ae60; font-weight: bold;">${value}</span>`;
				}
			}
		}

		return value;
	}
};

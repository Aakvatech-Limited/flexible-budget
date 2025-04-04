// Copyright (c) 2025, elius mgani and contributors
// For license information, please see license.txt

frappe.ui.form.on("Multi-Dimensional Budget", {
    onload(frm) {
        frm.fields_dict["accounting_dimensions"].grid.get_field("accounting_dimension").get_query = function(doc, cdt, cdn) {
            const used_dimensions = new Set();

            // Collect dimensions already selected in other rows
            (frm.doc.accounting_dimensions || []).forEach(row => {
                if (row.accounting_dimension && row.name !== cdn) {
                    used_dimensions.add(row.accounting_dimension);
                }
            });

            return {
                query: "flexible_budget.flexible_budget.doctype.multi_dimensional_budget.multi_dimensional_budget.custom_dimension_query",
                filters: {
                    exclude_dimensions: Array.from(used_dimensions)
                }
            };
        };
    },

validate: function(frm) {
    frm.set_df_property('frequency', 'read_only', 1);
}
})

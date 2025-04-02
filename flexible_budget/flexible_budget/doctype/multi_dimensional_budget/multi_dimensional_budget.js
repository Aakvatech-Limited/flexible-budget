// Copyright (c) 2025, elius mgani and contributors
// For license information, please see license.txt

frappe.ui.form.on("Multi-Dimensional Budget", {
	onload(frm) {
        frm.call({
            method: "flexible_budget.flexible_budget.doctype.multi_dimensional_budget.multi_dimensional_budget.get_acc_dimensions",  // Update with your app path
            callback: function(response) {
                if (response.message) {
                    let options = response.message;  // The response is already a list
                    
                    // Loop through each row in the child table and update the Select field
                    frm.fields_dict["accounting_dimensions"].grid.update_docfield_property(
                        "accounting_dimension", "options", options.join("\n")
                    );
                    frm.refresh_field("accounting_dimensions");  // Refresh the child table
                }
            }
        });
        frm.toggle_reqd('planned_amount', true);
        frm.set_df_property('percentage_used', 'read_only', 1);
        frm.set_df_property('allowed_amount', 'read_only', 1);
        frm.set_df_property('spent_amount', 'read_only', 1);
        frm.set_df_property('unspent_amount', 'read_only', 1); 
	},
    
    before_save: function(frm) {
        let seen = new Set();
        let unique_rows = [];
    
        // Loop through the current child table rows
        frm.doc.accounting_dimensions.forEach(row => {
            // Create a unique key based on both fields
            const key = `${row.accounting_dimension}||${row.specific}`;
    
            if (!seen.has(key)) {
                seen.add(key);
                unique_rows.push({
                    accounting_dimension: row.accounting_dimension,
                    specific: row.specific
                });
            }
        });
    
        // Replace child table with unique rows
        frm.doc.accounting_dimensions = [];
    
        unique_rows.forEach(row => {
            let new_row = frm.add_child('accounting_dimensions');
            new_row.accounting_dimension = row.accounting_dimension;
            new_row.specific = row.specific;
        });
    
        frm.refresh_field('accounting_dimensions');
    },
    

    on_save: function(frm) {
        // On form load/refresh, fetch and display the calculated unspent budget and percentage used
        frappe.call({
            method: "flexible_budget.flexible_budget.doctype.multi_dimensional_budget.multi_dimensional_budget.calculate_budget_usage",
            args: {
                docname: frm.doc.name
            },
            callback: function(r) {
                if (r.message) {
                    // Update the form fields with the values returned from the server
                    frm.set_value('unspent_amount', r.message.unspent_amount);
                    frm.set_value('spent_amount', r.message.spent_amount);
                    frm.set_value('percentage_used', r.message.percentage_used);
                    // Optionally, you could refresh the field UI or display a message
                }
            }
        });
    },
});

frappe.ui.form.on("Multi-Dimensional Budget Detail", {
    accounting_dimension(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const dimension = row.accounting_dimension;

        if (!dimension) {
            frappe.model.set_value(cdt, cdn, "specific", "");
            return;
        }

        frappe.call({
            method: "flexible_budget.flexible_budget.doctype.multi_dimensional_budget.multi_dimensional_budget.get_specific_options_for_dimension",
            args: {
                dimension: dimension
            },
            callback: function(r) {
                if (r.message) {
                    const options = r.message;

                    // Update 'specific' field in the child table with fetched options
                    frm.fields_dict["accounting_dimensions"].grid.update_docfield_property(
                        "specific", "options", options.join("\n")
                    );

                    // Clear the old value
                    frappe.model.set_value(cdt, cdn, "specific", "");
                }
            }
        });
    }
});

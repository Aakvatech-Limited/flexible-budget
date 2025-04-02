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
    },

validate: function(frm) {
        let seen = new Set();
        let unique_rows = [];

        // Loop through the current child table rows
        frm.doc.accounting_dimensions.forEach(row => {
             // Create a unique key based on both fields
        const key = `${row.accounting_dimension}`;
    
            if (!seen.has(key)) {
                seen.add(key);
                unique_rows.push({
                    accounting_dimension: row.accounting_dimension,
                    accounting_dimension_name: row.accounting_dimension_name
               });
            }
        });

        // let removed = frm.doc.accounting_dimensions.length - unique_rows.length;

        // Replace child table with unique rows
        frm.doc.accounting_dimensions = [];

        unique_rows.forEach(row => {
            let new_row = frm.add_child('accounting_dimensions');
            new_row.accounting_dimension = row.accounting_dimension;
            new_row.accounting_dimension_name = row.accounting_dimension_name;
        });

        frm.refresh_field('accounting_dimensions');

        // if (removed > 0) {
        //     frappe.msgprint(${removed} duplicate Accounting Dimension(s) removed.);
        // }    
    }
})

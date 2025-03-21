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
    
        before_save: function(frm) {
        let seen = new Set();
        let unique_rows = [];

        // Loop through the current child table rows
        frm.doc.accounting_dimensions.forEach(row => {
            if (!seen.has(row.accounting_dimension)) {
                seen.add(row.accounting_dimension);
                unique_rows.push(row);
            }
        });

        // let removed = frm.doc.accounting_dimensions.length - unique_rows.length;

        // Replace child table with unique rows
        frm.doc.accounting_dimensions = [];

        unique_rows.forEach(row => {
            let new_row = frm.add_child('accounting_dimensions');
            new_row.accounting_dimension = row.accounting_dimension;

            // Copy other fields if needed
            // Example: new_row.amount = row.amount;
        });

        frm.refresh_field('accounting_dimensions');

        // if (removed > 0) {
        //     frappe.msgprint(`${removed} duplicate Accounting Dimension(s) removed.`);
        // }
    }
});

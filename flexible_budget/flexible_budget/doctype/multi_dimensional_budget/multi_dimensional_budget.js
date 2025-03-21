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
    
});

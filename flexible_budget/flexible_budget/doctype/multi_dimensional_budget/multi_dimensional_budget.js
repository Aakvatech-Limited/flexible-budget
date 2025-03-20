// Copyright (c) 2025, elius mgani and contributors
// For license information, please see license.txt

frappe.ui.form.on("Multi-Dimensional Budget", {
	onload(frm) {
        frm.call({
            method: "csf_tz.csf_tz.doctype.multi_dimensional_budget.multi_dimensional_budget.get_acc_dimensions",  // Update with your app path
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
    
    onchange: function(frm) {
        frm.fields_dict["accounting_dimensions"].grid.get_field("accounting_dimension").get_query = function(doc, cdt, cdn) {
            let selected_options = [];

            // Collect all selected options from previous rows
            (frm.doc.accounting_dimensions || []).forEach(row => {
                if (row.accounting_dimension) {
                    selected_options.push(row.accounting_dimension);
                    console.log(selected_options);
                }
            });
                
                // Apply filters dynamically to each row in the child table
            frm.fields_dict["accounting_dimensions"].grid.grid_rows.forEach(row => {
                let field = row.get_field("accounting_dimension");
                if (field) {
                    field.get_query = function() {
                        return {
                            filters: [["name", "not in", selected_options]] // Exclude selected values
                        };
                    };
                }
            });
            
            frm.refresh_field("accounting_dimensions"); // Refresh the child table
        };
    }

});

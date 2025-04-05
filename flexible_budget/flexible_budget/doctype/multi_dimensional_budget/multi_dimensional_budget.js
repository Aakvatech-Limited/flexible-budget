// Copyright (c) 2025, elius mgani and contributors
// For license information, please see license.txt

frappe.ui.form.on("Multi-Dimensional Budget", {
	onload(frm) {
        set_dimension_options(frm);
    },

    validate: function(frm) {
        let seen = new Set();
        let unique_rows = [];

        frm.doc.accounting_dimensions.forEach(row => {
        const key = `${row.accounting_dimension}`;
    
            if (!seen.has(key)) {
                seen.add(key);
                unique_rows.push({
                    accounting_dimension: row.accounting_dimension,
                    accounting_dimension_name: row.accounting_dimension_name
               });
            }
        });


        // Replace child table with unique rows
        frm.doc.accounting_dimensions = [];

        unique_rows.forEach(row => {
            let new_row = frm.add_child('accounting_dimensions');
            new_row.accounting_dimension = row.accounting_dimension;
            new_row.accounting_dimension_name = row.accounting_dimension_name;
        });

        frm.refresh_field('accounting_dimensions');
    },
    start_date: (frm) => {
        if (frm.doc.start_date) {
            frm.call("set_end_date_from_frequency", {})
                .then((r) => {
                    if (r.message) {
                        frm.refresh_field("end_date");
                    }
                });
        }
    }
});

frappe.ui.form.on("Multi-Dimensional Budget Detail", {
    accounting_dimensions_add(frm, cdt, cdn) {
        set_dimension_options(frm);
    },
    before_accounting_dimension_remove(frm, cdt, cdn) {
        set_dimension_options(frm);
    }
});

let set_dimension_options = (frm) => {
    frm.call({
        method: "flexible_budget.flexible_budget.doctype.multi_dimensional_budget.multi_dimensional_budget.get_acc_dimensions",
        callback: function(response) {
            if (response.message) {
                let options = response.message; 
                
                frm.fields_dict["accounting_dimensions"].grid.update_docfield_property(
                    "accounting_dimension", "options", options.join("\n")
                );
                frm.refresh_field("accounting_dimensions");
            }
        }
    });
}

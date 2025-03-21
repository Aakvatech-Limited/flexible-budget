// Copyright (c) 2025, elius mgani and contributors
// For license information, please see license.txt

frappe.ui.form.on("Weekly Target Revenue", {
  onload(frm) {
    frm.call({
      method:
        "flexible_budget.flexible_budget.doctype.weekly_target_revenue.weekly_target_revenue.get_acc_dimensions", // Update with your app path
      callback: function (response) {
        if (response.message) {
          let options = response.message; // The response is already a list

          // Loop through each row in the child table and update the Select field
          frm.fields_dict[
            "accounting_dimensions"
          ].grid.update_docfield_property(
            "accounting_dimension",
            "options",
            options.join("\n")
          );
          frm.refresh_field("accounting_dimensions"); // Refresh the child table
        }
      },
    });
  },

  before_save: function (frm) {
    let seen = new Set();
    let unique_rows = [];

    frm.doc.accounting_dimensions.forEach((row) => {
      if (!seen.has(row.accounting_dimension)) {
        seen.add(row.accounting_dimension);
        unique_rows.push(row);
      }
    });

    frm.doc.accounting_dimensions = [];

    unique_rows.forEach((row) => {
      let new_row = frm.add_child("accounting_dimensions");
      new_row.accounting_dimension = row.accounting_dimension;
    });

    frm.refresh_field("accounting_dimensions");
  },
});

// Copyright (c) 2025, elius mgani and contributors
// For license information, please see license.txt

frappe.ui.form.on("Company Budget Control", {
  setup(frm) {
    frm.set_query("group_income_account", () => {
      return {
        filters: {
          root_type: "Income",
          is_group: 1,
          company: frm.doc.company,
        },
      };
    });
  },
});

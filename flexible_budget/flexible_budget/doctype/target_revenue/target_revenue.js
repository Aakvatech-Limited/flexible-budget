frappe.ui.form.on("Target Revenue", {
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
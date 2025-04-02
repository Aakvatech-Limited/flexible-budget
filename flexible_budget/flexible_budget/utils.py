import frappe
from frappe.utils import getdate

def update_target_revenue_from_invoice(doc, method):
    posting_date = getdate(doc.posting_date)
    company = doc.company

    settings = frappe.db.get_value(
        "Company Budget Control",
        {"company": company},
        ["enable_auto_calculation", "target_calculation_method", "action_if_no_target_revenue"],
        as_dict=True
    )


    if not settings:
        frappe.msgprint(f"No Company Budget Control found for company <b>{company}</b>.")
        return

    target_name = frappe.db.sql("""
        SELECT name FROM `tabTarget Revenue`
        WHERE company = %s
        AND %s BETWEEN start_date AND end_date
        AND docstatus = 1
        LIMIT 1
    """, (company, posting_date), as_dict=True)

    if not target_name:
        action = (settings.get("action_if_no_target_revenue") or "Warn").strip().lower()

        if action == "stop":
            frappe.throw("No Target Revenue found for this company and period. Submission stopped as per budget policy.")
        elif action == "warn":
            frappe.msgprint("No Target Revenue found for this company and period. Proceeding with caution.")
        return    
    

    target_doc = frappe.get_doc("Target Revenue", target_name[0].name)

    # Update collected amount based on whether it's a return
    if doc.is_return:
        target_doc.collected_amount -= abs(doc.grand_total)
    else:
        target_doc.collected_amount += doc.grand_total

    target_doc.calculate_target_percentage()    

    target_doc.save(ignore_permissions=True)
    
    frappe.msgprint(
        msg=f"Target Revenue '{target_doc.name}' updated.",
        alert=True,
        indicator='green'
    )

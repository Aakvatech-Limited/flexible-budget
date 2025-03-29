import frappe
from frappe.utils import getdate

def update_target_revenue_from_invoice(doc, method):
    posting_date = getdate(doc.posting_date)
    company = doc.company

    frappe.msgprint("Triggered hook: updating collected amount...")

    target_name = frappe.db.sql("""
        SELECT name FROM `tabTarget Revenue`
        WHERE company = %s
        AND %s BETWEEN start_date AND end_date
        AND docstatus = 0
        LIMIT 1
    """, (company, posting_date), as_dict=True)

    if not target_name:
        frappe.msgprint("No active Target Revenue found for this date and company.")
        return

    target_doc = frappe.get_doc("Target Revenue", target_name[0].name)

    # Update collected amount based on whether it's a return
    if doc.is_return:
        target_doc.collected_amount -= abs(doc.grand_total)
    else:
        target_doc.collected_amount += doc.grand_total

    # Check for auto calculation
    settings = frappe.db.get_value(
        "Flexible Budget Setting",
        {"company": company},
        ["enable_auto_calculation"],
        as_dict=True
    )

    target_doc.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.msgprint(f"Target Revenue <b>{target_doc.name}</b> updated.")


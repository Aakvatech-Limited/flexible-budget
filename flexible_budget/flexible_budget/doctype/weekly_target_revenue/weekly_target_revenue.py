# Copyright (c) 2025, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WeeklyTargetRevenue(Document):
    pass

@frappe.whitelist()
def get_acc_dimensions():
    # Fetch all records from "Accounting Dimension"
    documents = frappe.get_all("Accounting Dimension", fields=["name"])

    # Extract names into a list
    options = [doc["name"] for doc in documents]

    #Append Cost Center and Project to the list
    options.extend(["Cost Center", "Project"])
    
    return options

@frappe.whitelist()
def remove_duplicate_dimensions(doc, method):

    # Remove duplicate Accounting Dimensions in the child table before saving.
    
    seen = set()  # To track unique accounting dimensions
    unique_rows = []  # To store unique rows
    removed_count = 0  # Counter for duplicates removed

    for row in doc.accounting_dimensions:  # Loop through child table
        if row.accounting_dimension not in seen:
            seen.add(row.accounting_dimension)  # Mark as seen
            unique_rows.append(row)  # Keep the row
        else:
            removed_count += 1  # Track removed duplicates

    # Update child table with unique rows
    doc.accounting_dimensions = unique_rows

    # Show message if duplicates were removed
    if removed_count > 0:
        frappe.msgprint(f"{removed_count} Accounting Dimension Duplicate(s) Found and Removed")
				

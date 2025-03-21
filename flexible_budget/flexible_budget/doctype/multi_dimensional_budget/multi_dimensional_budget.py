# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document



class MultiDimensionalBudget(Document):
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

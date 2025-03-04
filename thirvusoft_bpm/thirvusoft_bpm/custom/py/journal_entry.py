import frappe
from thirvusoft_bpm.thirvusoft_bpm.custom.py.fees import update_advance_payments
from thirvusoft_bpm.thirvusoft_bpm.custom.py.sales_invoice import fetch_previous_outstanding_amount

def update_fees(doc,event):
    for acc in doc.accounts:
        if acc.reference_type == "Fees" and acc.reference_name and acc.debit_in_account_currency > 0 and acc.credit_in_account_currency == 0 and acc.party_type == 'Student' and acc.party:
            fees = frappe.get_doc('Fees',acc.reference_name)
            fees.append('advance_payments',{
                    'account':acc.account,
                    'amount':acc.debit_in_account_currency
                })
            fees.total_advance_payment += acc.debit_in_account_currency
            update_advance_payments(acc.reference_name)
            # fees.save()
def update_sales_invoice_allocated_amount(doc, method):
    allocation_map = {}

    # Loop through Journal Entry Accounts child table
    for account in doc.accounts:
        if account.reference_type == "Sales Invoice" and account.reference_name:
            if account.reference_name in allocation_map:
                allocation_map[account.reference_name] = allocation_map[account.reference_name] + account.credit
            else:
                allocation_map[account.reference_name] = account.credit

    # Update each Sales Invoice with the total allocated amount
    for invoice_name, allocated_amount in allocation_map.items():
        sales_invoice = frappe.get_doc("Sales Invoice", invoice_name)

        # Add to the existing allocated amount
        existing_allocated_amount = sales_invoice.custom_allocated_amount or 0
        sales_invoice.custom_allocated_amount = existing_allocated_amount + allocated_amount
        sales_invoice.save(ignore_permissions=True)

    frappe.db.commit()
import frappe
# from frappe.utils import getdate
# @frappe.whitelist(allow_guest= True)
# def check_expiry_date(token):
#     if getdate(frappe.db.get_value('Integration Request',token,'expiry_date')) >= getdate() :
#         return True
#     else:
#         message = ''
#         if frappe.db.get_value('Integration Request',token,'reference_doctype') == 'Payment Request' and frappe.db.get_value('Integration Request',token,'reference_docname'):
#             if frappe.db.get_value('Payment Request',frappe.db.get_value('Integration Request',token,'reference_docname'),'payment_gateway_account'):
#                 doc_name = frappe.db.get_value('Payment Request',frappe.db.get_value('Integration Request',token,'reference_docname'),'payment_gateway_account')
#                 doc = frappe.get_doc('Payment Gateway Account',doc_name)
#                 message = doc.default_message_for_expiry_date_remainder
#         return message,False
    
    
# from frappe.utils import getdate, nowdate
# import frappe

# @frappe.whitelist(allow_guest=True)
# def check_expiry_date(token):
#     expiry_date = frappe.db.get_value('Integration Request', token, 'expiry_date')
#     reference_doctype = frappe.db.get_value('Integration Request', token, 'reference_doctype')
#     reference_docname = frappe.db.get_value('Integration Request', token, 'reference_docname')
#     status = frappe.db.get_value('Integration Request', token, 'status')

#     # Check if payment already completed
#     if status == 'Completed':
#         return ["Payment already made.", "Paid"]
#     elif status == 'Failed':
#         return ["Payment failed.", "Failed"]

#     # Check expiry
#     if expiry_date and getdate(expiry_date) < getdate(nowdate()):
#         # Expired but not completed or failed
#         message = "This payment link has expired."

#         # Try to fetch custom message from Payment Gateway Account
#         if reference_doctype == 'Payment Request' and reference_docname:
#             gateway_account = frappe.db.get_value('Payment Request', reference_docname, 'payment_gateway_account')
#             if gateway_account:
#                 doc = frappe.get_doc('Payment Gateway Account', gateway_account)
#                 if doc.default_message_for_expiry_date_remainder:
#                     message = doc.default_message_for_expiry_date_remainder

#         return [message, "Expired"]

#     # Not expired and not used yet
#     return True

from frappe.utils import getdate, nowdate
import frappe

@frappe.whitelist(allow_guest=True)
def check_expiry_date(token):
    doc = frappe.get_doc("Integration Request", token)
    expiry_date = doc.expiry_date
    status = doc.status
    reference_doctype = doc.reference_doctype
    reference_docname = doc.reference_docname

    # Completed payment
    if status == "Completed":
        return ["Payment already made.", "Paid"]

    # Authorized but not captured
    elif status == "Authorized":
        return ["Your payment has been authorized and is being processed.", "Authorized"]

    # Failed payment
    elif status == "Failed":
        return ["Payment failed.", "Failed"]

    # Expired link
    if expiry_date and getdate(expiry_date) < getdate(nowdate()):
        message = "This payment link has expired."

        # Optional: get custom expiry message from Payment Gateway Account
        if reference_doctype == 'Payment Request' and reference_docname:
            gateway_account = frappe.db.get_value('Payment Request', reference_docname, 'payment_gateway_account')
            if gateway_account:
                gateway_doc = frappe.get_doc('Payment Gateway Account', gateway_account)
                if gateway_doc.default_message_for_expiry_date_remainder:
                    message = gateway_doc.default_message_for_expiry_date_remainder

        return [message, "Expired"]

    # Valid and unpaid
    return True

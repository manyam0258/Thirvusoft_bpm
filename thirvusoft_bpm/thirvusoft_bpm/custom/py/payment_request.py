import frappe
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote
from erpnext.accounts.doctype.payment_request.payment_request import (
    PaymentRequest , get_existing_payment_request_amount , get_amount , get_gateway_details,get_dummy_message,
    )
from erpnext.accounts.party import get_party_account, get_party_bank_account
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
# from frappe.core.doctype.communication.email import get_attach_link
from frappe import _
from frappe.utils import flt, nowdate
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file
from frappe.utils.background_jobs import enqueue
submit = False

class CustomPaymentRequest(PaymentRequest):
    def validate(self):
        super().validate()
        if self.reference_doctype == "Sales Invoice" and self.reference_name and self.is_new():
            self.set_gateway_account()     

    def get_message(self):
        """return message with payment gateway link"""
        if self.party_type == 'Student':
            context = {
                "doc": frappe.get_doc(self.reference_doctype, self.reference_name),
                "payment_url": self.payment_url,
                'student_balance':self.student_balance,
                'virtual_account':frappe.get_value('Student',self.party,'virtual_account') or "--"
            }
        elif self.party_type == 'Customer':
            context = {
                "doc": frappe.get_doc(self.reference_doctype, self.reference_name),
                "payment_url": self.payment_url,
                'student_balance':self.student_balance,
                'virtual_account':frappe.get_value(self.reference_doctype, self.reference_name,'virtual_account') or "--"
            }
        else:
            context = {
                "doc": frappe.get_doc(self.reference_doctype, self.reference_name),
                "payment_url": self.payment_url,
                'student_balance':self.student_balance,
            }
        if self.message:
            return frappe.render_template(self.message, context)

    # def send_email(self):
    #     """send email with payment link"""
    #     if self.reference_doctype == "Fees" and self.reference_name:
    #         fees = frappe.db.get_value("Fees", {"name":self.reference_name}, "company")
    #         if fees:
    #             default_mail=frappe.db.get_value("Company", {"name":fees}, "default_email")
    #     if self.reference_doctype == "Sales Invoice" and self.reference_name:
    #         invoice = frappe.db.get_value("Sales Invoice", {"name":self.reference_name}, "company")
    #         if invoice:
    #             default_mail=frappe.db.get_value("Company", {"name":invoice}, "default_email")
    #     if not self.bulk_transaction:
    #         args = {
    #         "recipients": self.email_to,
    #         "sender": None,
    #         "bcc": default_mail or None,
    #         "subject": self.subject,
    #         "message": self.get_message(),
    #         "now": True,
    #         "attachments": [
    #             frappe.attach_print(
    #                     self.reference_doctype,
    #                     self.reference_name,
    #                     file_name=self.reference_name,
    #                     print_format=self.print_format,
    #                 )
    #             ],
    #         }
    #     else:
    #         args = {
    #         "recipients": self.email_to,
    #         "sender": None,
    #         "bcc": default_mail or None,
    #         "subject": self.subject,
    #         "message": self.get_message(),
    #         "now": True
    #         }
            
    #     email_args = args
    #     print("email_args",email_args)
    #     enqueue(method=frappe.sendmail, queue="short", timeout=300, is_async=True, **email_args)

import frappe

def send_email(self):
    """Send email with payment link and company default_email as sole recipient (BCC)"""

    # 1. Identify Company from reference document
    company = None
    if self.reference_doctype == "Fees" and self.reference_name:
        company = frappe.db.get_value("Fees", self.reference_name, "company")
    elif self.reference_doctype == "Sales Invoice" and self.reference_name:
        company = frappe.db.get_value("Sales Invoice", self.reference_name, "company")

    # 2. Get BCC email from Company.default_email, this will be the sole recipient
    bcc_email = frappe.db.get_value("Company", company, "default_email") if company else None
    if not bcc_email:
        frappe.throw("No BCC email found in Company to send the Payment Request.")

    recipients = [self.email_to,bcc_email]

    # 3. Prepare email content
    subject = self.subject
    message = "This is a test message."  # Override message to test

    # 4. Attach document if not bulk
    attachments = []
    if not self.bulk_transaction:
        try:
            attachments = [
                frappe.attach_print(
                    self.reference_doctype,
                    self.reference_name,
                    file_name=self.reference_name,
                    print_format=self.print_format,
                )
            ]
        except Exception as e:
            frappe.log_error(f"Attachment generation failed for {self.name}: {str(e)}", "PaymentRequest Email")

    # 5. Prepare email args
    email_args = {
        "recipients": recipients,
        "sender": None,
        "subject": subject,
        "message": message,
        "now": True,
        "attachments": attachments
    }

    # 6. Send email
    try:
        frappe.sendmail(**email_args)

    except Exception as e:
        frappe.log_error(f"Failed to send Payment Request email {self.name}: {str(e)}", "PaymentRequest Email")






    # def set_gateway_account(self):
    #     company = frappe.db.get_value(self.reference_doctype,self.reference_name,"company")
    #     payment_gateway_aacount , payment_account , message = frappe.db.get_value("Payment Gateway Account",{"company":company},["name","payment_account","message"])
    #     self.payment_gateway_account = payment_gateway_aacount
    #     self.payment_account = payment_account 
    #     self.message = message
    def set_gateway_account(self):
        # 1. Get company from reference doc
        reference_company = frappe.db.get_value(self.reference_doctype, self.reference_name, "company")
        frappe.msgprint(_("Fetched Company from reference doc: {0}").format(reference_company))

        if not reference_company:
            frappe.throw(_("Company not found for {0}: {1}").format(self.reference_doctype, self.reference_name))

        # 2. Verify all Payment Gateway Accounts have valid company field
        all_accounts = frappe.get_all("Payment Gateway Account", fields=["name", "company"])
        invalid_accounts = [acc for acc in all_accounts if not acc.company]
        if invalid_accounts:
            invalid_names = ", ".join([acc.name for acc in invalid_accounts])
            frappe.throw(_("Found Payment Gateway Account(s) with empty or invalid company: {0}").format(invalid_names))

        # 3. Find the Payment Gateway Account for the reference company (NO is_default check)
        payment_gateway_account_doc = frappe.get_all(
            "Payment Gateway Account",
            filters={"company": reference_company},
            fields=["name", "payment_account", "message"],
            order_by="creation ASC",
            limit=1
        )

        if not payment_gateway_account_doc:
            frappe.throw(_("No Payment Gateway Account found for company {0}").format(reference_company))

        payment_gateway_account = payment_gateway_account_doc[0].name
        payment_account = payment_gateway_account_doc[0].payment_account
        message = payment_gateway_account_doc[0].message

        frappe.msgprint(_("Selected Payment Gateway Account: {0}, Payment Account: {1}").format(payment_gateway_account, payment_account))

        # 4. Assign to current doc
        self.company = reference_company
        self.payment_gateway_account = payment_gateway_account
        self.payment_account = payment_account
        self.message = message or ""

        # 5. Set payment gateway details
        self.set_payment_gateway_details()




    # def validate_payment_request_amount(self):
    #     existing_payment_request_amount = flt(
    #         get_existing_payment_request_amount(self.reference_doctype, self.reference_name)
    #     )

    #     ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
    #     if not hasattr(ref_doc, "order_type") or ref_doc.order_type != "Shopping Cart":
    #         ref_amount = get_amount(ref_doc, self.payment_account)

    #         if self.reference_doctype not in ["Sales Invoice","Fees"] and existing_payment_request_amount + flt(self.grand_total) > ref_amount:
    #             frappe.throw(
    #                 _("Total Payment Request amount cannot be greater than {0} amount").format(
    #                     self.reference_doctype
    #                 )
    #             )    


from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest

def custom_validate_payment_request_amount(self):
    if self.reference_doctype and self.reference_name:
        ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
        existing_payment_request_amount = get_existing_payment_request_amount(ref_doc)

    ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
    if not hasattr(ref_doc, "order_type") or ref_doc.order_type != "Shopping Cart":
        ref_amount = get_amount(ref_doc, self.payment_account)

        if self.reference_doctype not in ["Sales Invoice", "Fees"] and existing_payment_request_amount + flt(self.grand_total) > ref_amount:
            frappe.msgprint(
                _("Note: Total Payment Request amount exceeds {0} amount. Please verify if this is intentional.").format(
                    self.reference_doctype
                )
            )

# Monkey patch
PaymentRequest.validate_payment_request_amount = custom_validate_payment_request_amount





def get_advance_entries(doc,event):
    # if doc.party_type == "Student" and doc.party and frappe.db.get_value('Student',doc.party,'virtual_account'):
    #     doc.virtual_account  = frappe.db.get_value('Student',doc.party,'virtual_account')
    if doc.reference_doctype == 'Fees' and doc.reference_name:
        fees = frappe.get_doc('Fees',doc.reference_name)
        gl_entry = frappe.get_all('GL Entry',{'debit':['>',0],'is_cancelled':0,'credit':0,'party_type':doc.party_type,'party':doc.party,'against_voucher':doc.reference_name,'voucher_no':['!=',doc.reference_name]},['account','debit'])
        doc.advance_payments = []
        doc.total_advance_payment = 0
        fees.advance_payments = []
        fees.total_advance_payment = 0
        for entry in gl_entry:
            doc.append('advance_payments',{
                'account':entry['account'],
                'amount':entry['debit']
            })
            fees.append('advance_payments',{
                'account':entry['account'],
                'amount':entry['debit']
            })
            doc.total_advance_payment += entry['debit']
            fees.total_advance_payment += entry['debit']
        fees.save()
        invoice_doc = fees
    elif doc.reference_doctype == 'Sales Invoice' and doc.reference_name:
        invoice = frappe.get_doc('Sales Invoice',doc.reference_name)
        gl_entry = frappe.get_all('GL Entry',{'debit':['>',0],'is_cancelled':0,'credit':0,'party_type':doc.party_type,'party':doc.party,'against_voucher':doc.reference_name,'voucher_no':['!=',doc.reference_name]},['account','debit'])
        doc.advance_payments = []
        doc.total_advance_payment = 0
        invoice.advance_payments = []
        invoice.total_advance_payment = 0
        for entry in gl_entry:
            doc.append('advance_payments',{
                'account':entry['account'],
                'amount':entry['debit']
            })
            invoice.append('advance_payments',{
                'account':entry['account'],
                'amount':entry['debit']
            })
            doc.total_advance_payment += entry['debit']
            invoice.total_advance_payment += entry['debit']
        invoice.save()
        invoice_doc = invoice

    
    if doc.reference_doctype  in  ["Sales Invoice","Fees"]:
        #1.5 discount percentage
        if doc.grand_total > 0 and frappe.db.get_value('Company',invoice_doc.company,'charges_applicable') and not doc.without_charges:
            doc.without_charges = doc.grand_total
            doc.grand_total =  ( doc.without_charges * (frappe.db.get_value('Company',invoice_doc.company,'razorpay_charges')/100)) + doc.without_charges
        elif doc.grand_total > 0 and not frappe.db.get_value('Company',invoice_doc.company,'charges_applicable') and doc.without_charges:
            doc.grand_total =  doc.without_charges
        #Non Payment Message
        if doc.grand_total <= 0 and doc.payment_gateway_account:
            doc.message = frappe.db.get_value('Payment Gateway Account',doc.payment_gateway_account,'non_payment_message')
        elif doc.bulk_transaction:
            doc.message = frappe.db.get_value('Payment Gateway Account',doc.payment_gateway_account,'default_message_for_bulk_payment_remainder')


def background_submit(doc,event):
    global submit
    if not submit:
        frappe.msgprint('Submission has been moved to Background.. Kindly check after some time..')
        submit = True
    frappe.enqueue(whatsapp_message, doc=doc, queue="long")


def whatsapp_message(doc):
    if frappe.db.get_single_value('Whatsapp Settings','enable') == 1 and doc.reference_doctype == 'Fees' and doc.reference_name:
        html = CustomPaymentRequest.get_message(doc)
        v=(" ".join("".join(re.sub("\<[^>]*\>", "<br>",html ).split("<br>")).split(' ') ))
        v = v.replace('click here to pay', f'click here to pay: {doc.payment_url}')
        encoded_s = quote(v)

        guardians=frappe.db.sql(""" select phone_number,guardian_name from `tabStudent Guardian` md where enable_whatsapp_message = 1 and parent='{0}'""".format(doc.party),as_dict=1)
        instance_id =  frappe.db.get_single_value('Whatsapp Settings','instance_id')
        access_token =  frappe.db.get_single_value('Whatsapp Settings','access_token')
        company = frappe.get_value('Fees',doc.reference_name,'company')

        for i in guardians:
            def_message  = frappe.db.get_value('Payment Gateway Account',{'company':company,'is_default':1},'default_header_for_whatsapp_mail_message')
            def_context = {
                'doc':frappe.get_doc('Student',doc.party),
                'guardian':i['guardian_name']
            }
                
            html2 = frappe.render_template(def_message, def_context)
            def_v =(" ".join("".join(re.sub("\<[^>]*\>", "<br>",html2 ).split("<br>")).split(' ') ))


            fees_doc  = frappe.get_doc('Fees',doc.reference_name)
            pdf_bytes = frappe.get_print(doc.reference_doctype, doc.reference_name, doc=fees_doc, print_format=doc.print_format)
            pdf_name = doc.reference_name + '.pdf'
            pdf_url = frappe.utils.file_manager.save_file(pdf_name, get_pdf(pdf_bytes), doc.doctype, doc.name)           
            urls = f'https://{frappe.local.site}{pdf_url.file_url}'
            try:
                if urls and i["phone_number"]:
                    mobile_number = i["phone_number"].replace("+", "")
                    api_url = frappe.db.get_single_value('Whatsapp Settings','url')
                    if not doc.bulk_transaction:
                        url = f'{api_url}send.php?number=91{mobile_number}&type=media&message={def_v+encoded_s}&media_url={urls}&filename={pdf_name}&instance_id={instance_id}&access_token={access_token}'
                    else:
                        url = f'{api_url}send.php?number=91{mobile_number}&type=text&message={def_v+encoded_s}&instance_id={instance_id}&access_token={access_token}'
                    payload={}
                    headers = {}
                    response = requests.request("GET", url, headers=headers, data=payload)
                    #frappe.printerr(response.__dict__)
                    log_doc = frappe.new_doc("Whatsapp Log")
                    log_doc.update({
                        "mobile_no": mobile_number,
                        "status":"Success",
                        "payload": f"{url}",
                        "response" : response,
                        "last_execution": frappe.utils.now()
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.reference_doctype = "Payment Request"
                    log_doc.reference_name = doc.name
                    log_doc.insert()
                frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)
            except Exception as e:
                if urls and i["phone_number"]:
                    mobile_number = i["phone_number"].replace("+", "")
                    api_url = frappe.db.get_single_value('Whatsapp Settings','url')
                    if not doc.bulk_transaction:
                        url = f'{api_url}send.php?number=91{mobile_number}&type=media&message={def_v+encoded_s}&media_url={urls}&filename={pdf_name}&instance_id={instance_id}&access_token={access_token}'
                    else:
                        url = f'{api_url}send.php?number=91{mobile_number}&type=text&message={def_v+encoded_s}&instance_id={instance_id}&access_token={access_token}'
                    payload={}
                    headers = {}
                    log_doc = frappe.new_doc("Whatsapp Log")
                    log_doc.update({
                        "mobile_no": mobile_number,
                        
                        "status":"Failed",
                        "payload": f"{url}",
                        "response" : e,
                        "last_execution": frappe.utils.now()
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.reference_doctype = "Payment Request"
                    log_doc.reference_name = doc.name
                    log_doc.insert()
                frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)

# def custom_get_amount(ref_doc, payment_account=None):
#     """get amount based on doctype"""
#     dt = ref_doc.doctype
#     if dt in ["Sales Order", "Purchase Order"]:
#         grand_total = flt(ref_doc.rounded_total) or flt(ref_doc.grand_total)
#     elif dt in ["Purchase Invoice"]:
#         if not ref_doc.get("is_pos"):
#             if ref_doc.party_account_currency == ref_doc.currency:
#                 grand_total = flt(ref_doc.grand_total)
#             else:
#                 grand_total = flt(ref_doc.base_grand_total) / ref_doc.conversion_rate
#         elif dt == "POS Invoice":
#             for pay in ref_doc.payments:
#                 if pay.type == "Phone" and pay.account == payment_account:
#                     grand_total = pay.amount
#                     break
#     elif dt == "Fees":
#         grand_total = ref_doc.outstanding_amount

#     elif dt == "Sales Invoice":
#         # grand_total = ref_doc.outstanding_amount
#         return ref_doc.custom_net_payable

#     if grand_total > 0:
#         return grand_total
#     else:
#         frappe.throw(_("Payment Entry is already created"))
def custom_get_amount(ref_doc, payment_account=None):
    """Get amount based on doctype, ensuring custom_net_payable is used when applicable."""
    dt = ref_doc.doctype

    if dt == "Sales Invoice":
        custom_amount = flt(ref_doc.get("custom_net_payable", 0))
        if custom_amount != 0:
            return custom_amount  # Use custom_net_payable if it exists
        return flt(ref_doc.get("outstanding_amount", 0))  # Default to outstanding amount

    elif dt in ["Sales Order", "Purchase Order"]:
        return flt(ref_doc.rounded_total) or flt(ref_doc.grand_total)

    elif dt == "Purchase Invoice":
        if not ref_doc.get("is_pos"):
            if ref_doc.party_account_currency == ref_doc.currency:
                return flt(ref_doc.grand_total)
            return flt(ref_doc.base_grand_total) / ref_doc.conversion_rate
        elif dt == "POS Invoice":
            for pay in ref_doc.payments:
                if pay.type == "Phone" and pay.account == payment_account:
                    return pay.amount

    elif dt == "Fees":
        return flt(ref_doc.outstanding_amount)

    frappe.throw(_("Payment Entry is already created or no payable amount available"))






# @frappe.whitelist(allow_guest=True)
# def custom_make_payment_request(**args):
#     """Make payment request"""

#     args = frappe._dict(args)

#     ref_doc = frappe.get_doc(args.dt, args.dn)
#     gateway_account = get_gateway_details(args) or frappe._dict()

#     grand_total = custom_get_amount(ref_doc, gateway_account.get("payment_account"))

#     if args.loyalty_points and args.dt == "Sales Order":
#         from erpnext.accounts.doctype.loyalty_program.loyalty_program import validate_loyalty_points

#         loyalty_amount = validate_loyalty_points(ref_doc, int(args.loyalty_points))
#         frappe.db.set_value(
#             "Sales Order", args.dn, "loyalty_points", int(args.loyalty_points), update_modified=False
#         )
#         frappe.db.set_value("Sales Order", args.dn, "loyalty_amount", loyalty_amount, update_modified=False)
#         grand_total = grand_total - loyalty_amount

#     bank_account = (
#         get_party_bank_account(args.get("party_type"), args.get("party")) if args.get("party_type") else ""
#     )

#     draft_payment_request = frappe.db.get_value(
#         "Payment Request",
#         {"reference_doctype": args.dt, "reference_name": args.dn, "docstatus": 0},
#     )

#     # existing_payment_request_amount = get_existing_payment_request_amount(args.dt, args.dn)
#     # ref_doc = frappe.get_doc(args.dt, args.dn)
#     existing_payment_request_amount = get_existing_payment_request_amount(ref_doc)
#     ref_doc = frappe.get_doc(args.dt, args.dn)

#     if existing_payment_request_amount:
#         grand_total -= existing_payment_request_amount

#     if draft_payment_request:
#         frappe.db.set_value(
#             "Payment Request", draft_payment_request, "grand_total", grand_total, update_modified=False
#         )
#         pr = frappe.get_doc("Payment Request", draft_payment_request)
#     else:
#         pr = frappe.new_doc("Payment Request")
#         if args.get("dt") == "Sales Invoice":
#             args.recipient_id = ref_doc.student_email

#         if not args.get("payment_request_type"):
#             args["payment_request_type"] = (
#                 "Outward" if args.get("dt") in ["Purchase Order", "Purchase Invoice"] else "Inward"
#             )

#         pr.update(
#             {
#                 "payment_gateway_account": gateway_account.get("name"),
#                 "payment_gateway": gateway_account.get("payment_gateway"),
#                 "payment_account": gateway_account.get("payment_account"),
#                 "payment_channel": gateway_account.get("payment_channel"),
#                 "payment_request_type": args.get("payment_request_type"),
#                 "currency": ref_doc.currency,
#                 "grand_total": grand_total,
#                 "mode_of_payment": args.mode_of_payment,
#                 "email_to": args.recipient_id or ref_doc.owner,
#                 "subject": _("Payment Request for {0}").format(args.dn),
#                 "message": gateway_account.get("message") or get_dummy_message(ref_doc),
#                 "reference_doctype": args.dt,
#                 "reference_name": args.dn,
#                 "party_type": args.get("party_type") or "Customer",
#                 "party": args.get("party") or ref_doc.get("customer"),
#                 "bank_account": bank_account,
#             }
#         )

#         # Update dimensions
#         pr.update(
#             {
#                 "cost_center": ref_doc.get("cost_center"),
#                 "project": ref_doc.get("project"),
#             }
#         )

#         for dimension in get_accounting_dimensions():
#             pr.update({dimension: ref_doc.get(dimension)})

#         if args.order_type == "Shopping Cart" or args.mute_email:
#             pr.flags.mute_email = True

#         pr.insert(ignore_permissions=True)
#         if args.submit_doc:
#             pr.submit()

#     if args.order_type == "Shopping Cart":
#         frappe.db.commit()
#         frappe.local.response["type"] = "redirect"
#         frappe.local.response["location"] = pr.get_payment_url()

#     if args.return_doc:
#         return pr

#     return pr.as_dict()                

@frappe.whitelist(allow_guest=True)
def custom_make_payment_request(**args):
    from frappe.utils import flt
    from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions
    from erpnext.accounts.doctype.payment_request.payment_request import get_party_bank_account
    from erpnext.accounts.doctype.payment_request.payment_request import get_dummy_message

    args = frappe._dict(args or {})
    ref_doc = frappe.get_doc(args.dt, args.dn)
    args.company = ref_doc.company

    # Get payment gateway account
    gateway_account_doc = frappe.get_all(
        "Payment Gateway Account",
        filters={"company": ref_doc.company},
        fields=["name", "payment_gateway", "payment_account", "payment_channel", "message"],
        order_by="creation ASC",
        limit=1
    )
    if not gateway_account_doc:
        frappe.throw(_("No Payment Gateway Account found for company {0}").format(ref_doc.company))

    gateway_account = frappe._dict(gateway_account_doc[0])

    # # Cancel/delete only unpaid and unprocessed PRs (skip partially paid or completed)
    # existing_prs = frappe.get_all(
    #     "Payment Request",
    #     filters={
    #         "reference_doctype": args.dt,
    #         "reference_name": args.dn,
    #         "docstatus": ["<", 2],  # Draft or Submitted
    #         "status": ["!=", "Paid"]
    #     },
    #     fields=["name", "docstatus", "status"]
    # )
    # for pr in existing_prs:
    #     pr_doc = frappe.get_doc("Payment Request", pr.name)

    #     # Skip partially paid or processed requests
    #     if pr_doc.status in ["Partially Paid", "Completed", "Authorized"]:
    #         continue

    #     # Cancel or delete only fully unused drafts or submitted
    #     if pr_doc.docstatus == 1:
    #         pr_doc.cancel()
    #     else:
    #         pr_doc.delete()

    # Determine payment amount: prioritize args.amount, then custom_net_payable, then outstanding_amount
    payment_amount = (
        flt(args.get("amount"))
        or flt(ref_doc.get("custom_net_payable"))
        or flt(ref_doc.get("outstanding_amount"))
    )


    # Prepare new PR
    pr = frappe.new_doc("Payment Request")

    args["payment_request_type"] = args.get("payment_request_type") or (
        "Outward" if args.get("dt") in ["Purchase Order", "Purchase Invoice"] else "Inward"
    )

    recipient = ref_doc.get("student_email") or ref_doc.get("email_id") or ref_doc.owner

    pr.update({
        "payment_gateway_account": gateway_account.name,
        "payment_gateway": gateway_account.payment_gateway,
        "payment_account": gateway_account.payment_account,
        "payment_channel": gateway_account.payment_channel,
        "payment_request_type": args.payment_request_type,
        "currency": ref_doc.currency,
        "grand_total": payment_amount,
        "mode_of_payment": args.get("mode_of_payment"),
        "email_to": recipient,
        "subject": _("Payment Request for {0}").format(args.dn),
        "message": gateway_account.message or get_dummy_message(ref_doc),
        "reference_doctype": args.dt,
        "reference_name": args.dn,
        "party_type": args.get("party_type") or "Customer",
        "party": args.get("party") or ref_doc.get("customer"),
        "bank_account": get_party_bank_account(args.get("party_type"), args.get("party")) if args.get("party_type") else "",
        "company": ref_doc.company,
        "cost_center": ref_doc.get("cost_center"),
        "project": ref_doc.get("project"),
    })

    for dim in get_accounting_dimensions():
        pr.update({dim: ref_doc.get(dim)})

    if args.get("mute_email") or args.get("order_type") == "Shopping Cart":
        pr.flags.mute_email = True

    pr.insert(ignore_permissions=True)
    if args.get("submit_doc"):
        pr.submit()

    if args.get("order_type") == "Shopping Cart":
        frappe.db.commit()
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = pr.get_payment_url()

    return pr if args.get("return_doc") else pr.as_dict()




    

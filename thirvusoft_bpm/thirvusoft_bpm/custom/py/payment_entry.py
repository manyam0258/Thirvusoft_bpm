import frappe
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest
from bs4 import BeautifulSoup
import re
from urllib.parse import quote
# from frappe.core.doctype.communication.email import get_attach_link
import requests
from frappe.utils.file_manager import save_file
from frappe.utils.pdf import get_pdf
from frappe.utils.background_jobs import enqueue
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from hrms.overrides.employee_payment_entry import EmployeePaymentEntry

from erpnext.accounts.party import get_party_account

from erpnext.accounts.party import get_party_advance_account
import frappe
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest
from bs4 import BeautifulSoup
import re
from urllib.parse import quote
import requests
from frappe.utils.file_manager import save_file
from frappe.utils.pdf import get_pdf
from frappe.utils.background_jobs import enqueue
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from hrms.overrides.employee_payment_entry import EmployeePaymentEntry
from erpnext.accounts.party import get_party_account, get_party_advance_account
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry as ERPNextPaymentEntry





import frappe
from erpnext.accounts.doctype import payment_entry

def custom_get_valid_reference_doctypes(self):
    if self.party_type == "Customer":
        return ("Sales Order", "Sales Invoice", "Journal Entry", "Dunning", "Payment Entry", "Delivery Note")
    elif self.party_type in ["Shareholder", "Employee"]:
        return ("Journal Entry", "Expense Claim","Employee Advance", "Leave Encashment", "Gratuity",)
    elif self.party_type == "Supplier":
        return ("Purchase Order", "Purchase Invoice", "Journal Entry", "Payment Entry", "Purchase Receipt")
    # default fallback
    return ()

class CustomPayment(EmployeePaymentEntry):
    def validate_transaction_reference(self):
        bank_account = self.paid_to if self.payment_type == "Receive" else self.paid_from
        bank_account_type = frappe.db.get_value("Account", bank_account, "account_type")

        # if bank_account_type == "Bank":
        # 	if not self.reference_no or not self.reference_date:
        # 		frappe.throw(_("Reference No and Reference Date is mandatory for Bank transaction"))
    
def set_liability_account(self):
	# Auto setting liability account should only be done during 'draft' status
	if self.docstatus > 0 or self.payment_type == "Internal Transfer":
		return

	self.book_advance_payments_in_separate_party_account = False

	if self.party_type not in ("Customer", "Supplier"):
		self.is_opening = "No"
		return

	# Only apply logic if Customer Group is 'Student'
	if self.party_type == "Customer":
		customer_group = frappe.db.get_value("Customer", self.party, "customer_group")
		if customer_group != "Student":
			self.is_opening = "No"
			return

	# Company setting check
	if not frappe.db.get_value(
		"Company", self.company, "book_advance_payments_in_separate_party_account"
	):
		self.is_opening = "No"
		return

	# Important to set this flag for the gl building logic to work properly
	self.book_advance_payments_in_separate_party_account = True

	account_type = frappe.get_value(
		"Account", {"name": self.party_account, "company": self.company}, "account_type"
	)

	if (account_type == "Payable" and self.party_type == "Customer") or (
		account_type == "Receivable" and self.party_type == "Supplier"
	):
		self.is_opening = "No"
		return

	if self.references:
		allowed_types = frozenset(["Sales Order", "Purchase Order"])
		reference_types = set([x.reference_doctype for x in self.references])

		# If there are references other than `allowed_types`, treat this as a normal payment entry
		if reference_types - allowed_types:
			self.book_advance_payments_in_separate_party_account = False
			self.is_opening = "No"
			return

	accounts = get_party_account(self.party_type, self.party, self.company, include_advance=True)

	liability_account = accounts[1] if len(accounts) > 1 else None
	fieldname = (
		"default_advance_received_account"
		if self.party_type == "Customer"
		else "default_advance_paid_account"
	)

	if not liability_account:
		throw(
			_("Please set default {0} in Company {1}").format(
				frappe.bold(frappe.get_meta("Company").get_label(fieldname)), frappe.bold(self.company)
			)
		)

	self.set(self.party_account_field, liability_account)

	frappe.msgprint(
		_(
			"Book Advance Payments as Liability option is chosen. Paid From account changed from {0} to {1}."
		).format(
			frappe.bold(self.party_account),
			frappe.bold(liability_account),
		),
		alert=True,
	)


def update_letter_head(doc,event):
    doc.letter_head = frappe.get_value('Payment Letter Head',{'parent':doc.company,'party_type':doc.party_type},'letter_head')
    

def on_submit(doc, method=None):
    send_payment_mail(doc)
    send_message_confirmation(doc,method)

@frappe.whitelist()
def send_message_confirmation(doc,event):
    for ref in doc.references:
        if ref.reference_doctype == 'Fees' and ref.reference_name and frappe.db.get_value('Company',doc.company,'enable_payment_confirmation_message') ==1:
            def_v = ''
            encoded_s = ''
            html = ''
            html2 = ''
            fees_doc = frappe.get_doc('Fees',ref.reference_name)

            message  = frappe.db.get_value('Payment Gateway Account',{'company':doc.company,'is_default':1},'confirmation_message')
            if message:
                context = {
                    'doc':doc
                }
                
                html = frappe.render_template(message, context)
                v=(" ".join("".join(re.sub("\<[^>]*\>", "<br>",html ).split("<br>")).split(' ') ))
                encoded_s = quote(v)

            guardians=frappe.db.sql(""" select phone_number,guardian_name from `tabStudent Guardian` md where enable_whatsapp_message = 1 and parent='{0}'""".format(doc.party),as_dict=1)
            instance_id =  frappe.db.get_single_value('Whatsapp Settings','instance_id')
            access_token =  frappe.db.get_single_value('Whatsapp Settings','access_token')
            default_print_format = frappe.db.get_value(
                    "Property Setter",
                    dict(property="default_print_format", doc_type=doc.doctype),
                    "value",
                )
            for i in guardians:
                def_message  = frappe.db.get_value('Payment Gateway Account',{'company':fees_doc.company,'is_default':1},'default_header_for_whatsapp_mail_message')
                if def_message:
                    def_context = {
                        'doc':frappe.get_doc('Student',fees_doc.student),
                        'guardian':i['guardian_name']
                    }
                        
                    html2 = frappe.render_template(def_message, def_context)
                    def_v =(" ".join("".join(re.sub("\<[^>]*\>", "<br>",html2 ).split("<br>")).split(' ') ))

                pdf_bytes = frappe.get_print(doc.doctype, doc.name, doc=doc, print_format=default_print_format)
                pdf_name = doc.name + '.pdf'
                pdf_url = frappe.utils.file_manager.save_file(pdf_name, get_pdf(pdf_bytes), doc.doctype, doc.name)           
                urls = f'https://{frappe.local.site}{pdf_url.file_url}'
                try:
                    if urls and i["phone_number"] and frappe.db.get_single_value('Whatsapp Settings','enable') == 1:
                        mobile_number = i["phone_number"].replace("+", "")
                        api_url = frappe.db.get_single_value('Whatsapp Settings','url')
                        url = f'{api_url}send.php?number=91{mobile_number}&type=media&message={def_v + encoded_s}&media_url={urls}&filename={pdf_name}&instance_id={instance_id}&access_token={access_token}'
                        payload={}
                        headers = {}
                        response = requests.request("GET", url, headers=headers, data=payload)
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
                        log_doc.reference_doctype = "Payment Entry"
                        log_doc.reference_name = doc.name
                        log_doc.insert()
                    frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)
                except Exception as e:
                    if urls and i["phone_number"] and frappe.db.get_single_value('Whatsapp Settings','enable') == 1:
                        mobile_number = i["phone_number"].replace("+", "")
                        api_url = frappe.db.get_single_value('Whatsapp Settings','url')
                        url = f'{api_url}send.php?number=91{mobile_number}&type=media&message={def_v + encoded_s}&media_url={urls}&filename={pdf_name}&instance_id={instance_id}&access_token={access_token}'
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
                        log_doc.reference_doctype = "Payment Entry"
                        log_doc.reference_name = doc.name
                        log_doc.insert()
                    frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)

            final_msg = def_v + encoded_s
            final_msg.replace('%',' ')
            """send email with payment link"""
            default_mail=frappe.db.get_value("Company", {"name":doc.company}, "default_email")
            email_args = {
                "recipients": fees_doc.student_email,
                "sender": None,
                "bcc": default_mail or None,
                "subject": f'Payment Entry for {doc.name}',
                "message": html2 + html,
                "now": True,
                "attachments": [
                    frappe.attach_print(
                        doc.doctype,
                        doc.name,
                        file_name=doc.name,
                        print_format=default_print_format,
                    )
                ],
            }
            enqueue(method=frappe.sendmail, queue="short", timeout=300, is_async=True, **email_args)

    send_purchase_msg(doc)


# Supplier Whatsapp Message
def send_purchase_msg(doc):
    if doc.party_type == 'Supplier' and doc.party and frappe.db.get_single_value('Whatsapp Settings','enable') == 1 and frappe.db.get_single_value('Whatsapp Settings','enable_message_for_payment_entry') == 1:
        if not frappe.db.get_single_value('Whatsapp Settings','payment_entry'):
            frappe.throw("Kindly fill the Message Template for Payment Entry")
        else:   
            supplier_no = frappe.db.get_value('Supplier',doc.party,'mobile_no')
            def_v = ''
            encoded_s = ''
            html = ''
            html2 = ''
            instance_id =  frappe.db.get_single_value('Whatsapp Settings','instance_id')
            access_token =  frappe.db.get_single_value('Whatsapp Settings','access_token')
            default_print_format = frappe.db.get_value(
                    "Property Setter",
                    dict(property="default_print_format", doc_type=doc.doctype),
                    "value",
                )
            pay_message  = frappe.db.get_single_value('Whatsapp Settings','payment_entry')
            if pay_message:
                context = {
                    'doc':doc
                }
                
                html = frappe.render_template(pay_message, context)
                v=(" ".join("".join(re.sub("\<[^>]*\>", "<br>",html ).split("<br>")).split(' ') ))
                encoded_s = quote(v)


            pdf_bytes = frappe.get_print(doc.doctype, doc.name, doc=doc, print_format=default_print_format)
            pdf_name = doc.name + '.pdf'
            pdf_url = frappe.utils.file_manager.save_file(pdf_name, get_pdf(pdf_bytes), doc.doctype, doc.name)           
            urls = f'https://{frappe.local.site}{pdf_url.file_url}'               
            try:
                if urls and supplier_no:
                    mobile_number = supplier_no.replace("+", "")
                    api_url = frappe.db.get_single_value('Whatsapp Settings','url')
                    url = f'{api_url}send.php?number=91{mobile_number}&type=media&message={def_v + encoded_s}&media_url={urls}&filename={pdf_name}&instance_id={instance_id}&access_token={access_token}'
                    payload={}
                    headers = {}
                    response = requests.request("GET", url, headers=headers, data=payload)
                    
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
                    log_doc.reference_doctype = "Payment Entry"
                    log_doc.reference_name = doc.name
                    log_doc.insert()
                frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)
            except Exception as e:
                if urls and supplier_no:
                    mobile_number = supplier_no.replace("+", "")
                    api_url = frappe.db.get_single_value('Whatsapp Settings','url')
                    url = f'{api_url}send.php?number=91{mobile_number}&type=media&message={def_v + encoded_s}&media_url={urls}&filename={pdf_name}&instance_id={instance_id}&access_token={access_token}'
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
                    log_doc.reference_doctype = "Payment Entry"
                    log_doc.reference_name = doc.name
                    log_doc.insert()
                frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)



# import frappe
# from frappe.utils.background_jobs import enqueue
# from frappe import _
# def send_payment_mail(doc, method=None):
#     # Fetch Payment Gateway Account using the company
#     payment_gateway_account = frappe.db.get_value(
#         "Payment Gateway Account",
#         {"company": doc.company},
#         ["name", "confirmation_message"],
#         as_dict=True
#     )

#     if not payment_gateway_account:
#         frappe.log_error(f"Payment Gateway Account not found for company {doc.company}", "send_payment_mail")
#         return  # Exit if no gateway settings exist

#     # Fetch Email Recipients
#     student_email = frappe.get_value("Student", doc.party, "student_email_id")
#     guardian_emails = frappe.db.sql("""
#         SELECT g.email_address as guardian_email 
#         FROM `tabStudent Guardian` sg
#         JOIN `tabGuardian` g ON sg.guardian = g.name
#         WHERE sg.parent = %s
#         GROUP BY g.name
#     """, (doc.party,), as_dict=True)

#     guardian_email_list = [entry["guardian_email"] for entry in guardian_emails if entry["guardian_email"]]

#     # Prepare email recipients
#     recipients = guardian_email_list if guardian_email_list else []
#     if not recipients:
#         return  # Exit if no valid emails found

#     # Set Subject and Message
#     subject = _("Thanks for Payment - Payment Entry {0}").format(doc.name)
#     message = _("We acknowledge the receipt of {0} paid by you.").format(doc.paid_amount)

#     # ✅ Get Print Format ONLY from Company Doctype
#     print_format = frappe.db.get_value("Company", doc.company, "custom_payment_print_format") or doc.meta.default_print_format or "Standard"

#     try:
#         attachments = [
#             frappe.attach_print(
#                 doc.doctype,
#                 doc.name,
#                 doc=doc,
#                 print_format=print_format,
#                 letterhead=doc.letter_head or None
#             )
#         ]
#     except Exception as e:
#         frappe.log_error(f"Failed to generate attachment for {doc.name}: {str(e)}", "send_payment_mail")
#         attachments = []

#     email_args = {
#         "recipients": recipients,
#         "sender": None,
#         "subject": subject,
#         "message": message,
#         "now": True,
#         "attachments": attachments,
#     }

#     # Enqueue email sending
#     try:
#         enqueue(method=frappe.sendmail, queue="short", timeout=300, is_async=True, **email_args)
#     except Exception as e:
#         frappe.log_error(f"Failed to send email for {doc.name}: {str(e)}", "send_payment_mail")


import frappe
from frappe.utils.background_jobs import enqueue
from frappe import _

def send_payment_mail(doc, method=None):
    # Fetch Payment Gateway Account using the company
    payment_gateway_account = frappe.db.get_value(
        "Payment Gateway Account",
        {"company": doc.company},
        ["name", "confirmation_message"],
        as_dict=True
    )

    if not payment_gateway_account:
        frappe.log_error(f"Payment Gateway Account not found for company {doc.company}", "send_payment_mail")
        return  # Exit if no gateway settings exist

    # Fetch Email Recipients
    student_email = frappe.get_value("Student", doc.party, "student_email_id")
    guardian_emails = frappe.db.sql("""
        SELECT g.email_address as guardian_email 
        FROM `tabStudent Guardian` sg
        JOIN `tabGuardian` g ON sg.guardian = g.name
        WHERE sg.parent = %s
        GROUP BY g.name
    """, (doc.party,), as_dict=True)

    guardian_email_list = [entry["guardian_email"] for entry in guardian_emails if entry["guardian_email"]]

    # Prepare email recipients
    recipients = guardian_email_list if guardian_email_list else []
    if not recipients:
        return  # Exit if no valid emails found

    # ✅ Add BCC email from Company
    bcc_email = frappe.db.get_value("Company", doc.company, "default_email")
    bcc_list = [bcc_email] if bcc_email else []

    # Set Subject and Message
    subject = _("Thanks for Payment - Payment Entry {0}").format(doc.name)
    message = _("We acknowledge the receipt of {0} paid by you.").format(doc.paid_amount)

    # ✅ Get Print Format ONLY from Company Doctype
    print_format = frappe.db.get_value("Company", doc.company, "custom_payment_print_format") or doc.meta.default_print_format or "Standard"

    try:
        attachments = [
            frappe.attach_print(
                doc.doctype,
                doc.name,
                doc=doc,
                print_format=print_format,
                letterhead=doc.letter_head or None
            )
        ]
    except Exception as e:
        frappe.log_error(f"Failed to generate attachment for {doc.name}: {str(e)}", "send_payment_mail")
        attachments = []

    # ✅ Include BCC in email arguments
    email_args = {
        "recipients": recipients,
        "bcc": bcc_list,  # Add BCC
        "sender": None,
        "subject": subject,
        "message": message,
        "now": True,
        "attachments": attachments,
    }

    # Enqueue email sending
    try:
        enqueue(method=frappe.sendmail, queue="short", timeout=300, is_async=True, **email_args)
    except Exception as e:
        frappe.log_error(f"Failed to send email for {doc.name}: {str(e)}", "send_payment_mail")


import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry as BasePaymentEntry
from erpnext.accounts.doctype.payment_entry.payment_entry import get_party_account


class CustomPaymentEntry(BasePaymentEntry):
    def set_liability_account(self):
        # Auto setting liability account should only be done during 'draft' status
        if self.docstatus > 0 or self.payment_type == "Internal Transfer":
            return

        self.book_advance_payments_in_separate_party_account = False

        if self.party_type not in ("Customer", "Supplier"):
            self.is_opening = "No"
            return

        # Only apply logic if Customer Group is 'Student'
        if self.party_type == "Customer":
            customer_group = frappe.db.get_value("Customer", self.party, "customer_group")
            if customer_group != "Student":
                self.is_opening = "No"
                return

        
        if not frappe.db.get_value(
            "Company", self.company, "book_advance_payments_in_separate_party_account"
        ):
            self.is_opening = "No"
            return

        # Important to set this flag for the GL building logic to work properly
        self.book_advance_payments_in_separate_party_account = True

        account_type = frappe.get_value(
            "Account", {"name": self.party_account, "company": self.company}, "account_type"
        )

        if (account_type == "Payable" and self.party_type == "Customer") or (
            account_type == "Receivable" and self.party_type == "Supplier"
        ):
            self.is_opening = "No"
            return

        if self.references:
            allowed_types = frozenset(["Sales Order", "Purchase Order"])
            reference_types = set([x.reference_doctype for x in self.references])

            # If there are references other than `allowed_types`, treat this as a normal payment entry
            if reference_types - allowed_types:
                self.book_advance_payments_in_separate_party_account = False
                self.is_opening = "No"
                return

        accounts = get_party_account(self.party_type, self.party, self.company, include_advance=True)
        liability_account = accounts[1] if len(accounts) > 1 else None

        fieldname = (
            "default_advance_received_account"
            if self.party_type == "Customer"
            else "default_advance_paid_account"
        )

        if not liability_account:
            frappe.throw(
                _("Please set default {0} in Company {1}").format(
                    frappe.bold(frappe.get_meta("Company").get_label(fieldname)),
                    frappe.bold(self.company)
                )
            )

        self.set(self.party_account_field, liability_account)

        frappe.msgprint(
            _(
                "Book Advance Payments as Liability option is chosen. "
                "Paid From account changed from {0} to {1}."
            ).format(
                frappe.bold(self.party_account),
                frappe.bold(liability_account),
            ),
            alert=True,
        )




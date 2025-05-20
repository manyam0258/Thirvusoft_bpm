# transfer_certificate_request.py
# import frappe
# from frappe.model.document import Document

# class TransferCertificateRequest(Document):
#     def before_save(self):
#         if not self.admission_no:
#             return

#         student = frappe.get_doc('Student', self.admission_no)

#         self.name_of_the_student = student.student_name
#         self.gender = student.gender
#         self.udise_pen = student.pen
#         self.dob_figures = student.date_of_birth
#         self.dob_words = self.convert_date_to_words(student.date_of_birth)
#         self.nationality = student.nationality
#         self.category = student.category
#         self.date_of_joining = student.joining_date
#         self.transfer_certificate_request_no = self.name

#         # Student Logs
#         if student.student_logs:
#             latest_log = student.student_logs[-1]
#             self.previous_school_attended = latest_log.prvious_school_attended
#             self.course_attended_in_the_previous_school = latest_log.grade_qualified

#         # Guardians
#         for g in student.guardians:
#             if g.relation == 'Father':
#                 self.name_of_father = g.guardian_name
#             if g.relation == 'Mother':
#                 self.name_of_mother = g.guardian_name

#         # Program Enrollment
#         pe_list = frappe.get_all('Program Enrollment',
#             filters={'student': student.name},
#             fields=['name', 'academic_year', 'program'],
#             order_by='creation desc',
#             limit=1
#         )

#         if pe_list:
#             pe = pe_list[0]
#             self.ay_figures = pe.academic_year
#             self.course_last_attended = pe.program
#             self.ay_words = self.convert_year_to_full_words(pe.academic_year)

#             full_pe = frappe.get_doc('Program Enrollment', pe.name)

#             # Clear and add subjects studied
#             self.set('subjects_studied', [])
#             for course in full_pe.courses:
#                 self.append('subjects_studied', {
#                     'course': course.course,
#                     'course_name': course.course_name
#                 })
#      # ✅ Set transfer_certificate_no if workflow_state is Awaiting Final Settlement
#         if self.workflow_state == "Awaiting Final Settlement" and not self.transfer_certificate_no:
#             self.transfer_certificate_no = self.transfer_certificate_request_no

#     def convert_date_to_words(self, date):
#         if not date:
#             return ""
#         day = date.day
#         month = date.strftime("%B").upper()
#         year = date.year
#         return f"{self.convert_day_to_words(day)} {month} {self.convert_year_to_words(year)}"

#     def convert_day_to_words(self, day):
#         words = [
#             'FIRST', 'SECOND', 'THIRD', 'FOURTH', 'FIFTH', 'SIXTH', 'SEVENTH', 'EIGHTH', 'NINTH', 'TENTH',
#             'ELEVENTH', 'TWELFTH', 'THIRTEENTH', 'FOURTEENTH', 'FIFTEENTH', 'SIXTEENTH', 'SEVENTEENTH',
#             'EIGHTEENTH', 'NINETEENTH', 'TWENTIETH', 'TWENTY FIRST', 'TWENTY SECOND', 'TWENTY THIRD',
#             'TWENTY FOURTH', 'TWENTY FIFTH', 'TWENTY SIXTH', 'TWENTY SEVENTH', 'TWENTY EIGHTH', 'TWENTY NINTH',
#             'THIRTIETH', 'THIRTY FIRST'
#         ]
#         return words[day - 1]

#     def convert_year_to_words(self, year):
#         ones = ['', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE']
#         teens = ['TEN', 'ELEVEN', 'TWELVE', 'THIRTEEN', 'FOURTEEN', 'FIFTEEN', 'SIXTEEN', 'SEVENTEEN', 'EIGHTEEN', 'NINETEEN']
#         tens = ['', '', 'TWENTY', 'THIRTY', 'FORTY', 'FIFTY', 'SIXTY', 'SEVENTY', 'EIGHTY', 'NINETY']

#         str_year = str(year)
#         words = f"{ones[int(str_year[0])]} THOUSAND "
#         second_pair = int(str_year[1:3])

#         if second_pair < 10:
#             words += f"{ones[second_pair]} "
#         elif second_pair < 20:
#             words += f"{teens[second_pair - 10]} "
#         else:
#             words += f"{tens[second_pair // 10]} "
#             if second_pair % 10 != 0:
#                 words += f"{ones[second_pair % 10]} "

#         words += ones[int(str_year[3])]
#         return words.strip()

#     def convert_year_to_full_words(self, year):
#         ones = ['', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE']
#         teens = ['TEN', 'ELEVEN', 'TWELVE', 'THIRTEEN', 'FOURTEEN', 'FIFTEEN', 'SIXTEEN', 'SEVENTEEN', 'EIGHTEEN', 'NINETEEN']
#         tens = ['', '', 'TWENTY', 'THIRTY', 'FORTY', 'FIFTY', 'SIXTY', 'SEVENTY', 'EIGHTY', 'NINETY']

#         num = int(year)
#         words = ''

#         if 2000 <= num < 3000:
#             words = 'TWO THOUSAND'
#             last_two = num % 100

#             if last_two > 0:
#                 words += ' '
#                 if last_two < 10:
#                     words += ones[last_two]
#                 elif last_two < 20:
#                     words += teens[last_two - 10]
#                 else:
#                     words += tens[last_two // 10]
#                     if last_two % 10 != 0:
#                         words += f' {ones[last_two % 10]}'
#         return words
# 0.00

import frappe
from frappe.model.document import Document

class TransferCertificateRequest(Document):
    def before_save(self):
        if not self.admission_no:
            return

        student = frappe.get_doc('Student', self.admission_no)

        self.name_of_the_student = student.student_name
        self.gender = student.gender
        self.udise_pen = student.pen
        self.dob_figures = student.date_of_birth
        self.dob_words = self.convert_date_to_words(student.date_of_birth)
        self.nationality = student.nationality
        self.category = student.category
        self.date_of_joining = student.joining_date
        self.transfer_certificate_request_no = self.name

        # Student Logs
        if student.student_logs:
            latest_log = student.student_logs[-1]
            self.previous_school_attended = latest_log.prvious_school_attended
            self.course_attended_in_the_previous_school = latest_log.grade_qualified

        # Guardians
        for g in student.guardians:
            if g.relation == 'Father':
                self.name_of_father = g.guardian_name
            if g.relation == 'Mother':
                self.name_of_mother = g.guardian_name

        # Program Enrollment (set only if not already filled)
        if not self.course_last_attended or not self.ay_figures:
            pe_list = frappe.get_all('Program Enrollment',
                filters={'student': student.name},
                fields=['name', 'academic_year', 'program'],
                order_by='creation desc',
                limit=1
            )

            if pe_list:
                pe = pe_list[0]
                self.ay_figures = pe.academic_year
                self.course_last_attended = pe.program
                self.ay_words = self.convert_year_to_full_words(pe.academic_year)

                full_pe = frappe.get_doc('Program Enrollment', pe.name)

                # Add subjects_studied only if not already set
                if not self.subjects_studied:
                    self.set('subjects_studied', [])
                    for course in full_pe.courses:
                        self.append('subjects_studied', {
                            'course': course.course,
                            'course_name': course.course_name
                        })

        # ✅ Set transfer_certificate_no if workflow_state is Awaiting Final Settlement
        if self.workflow_state == "Awaiting Final Settlement" and not self.transfer_certificate_no:
            self.transfer_certificate_no = self.transfer_certificate_request_no

    def convert_date_to_words(self, date):
        if not date:
            return ""
        day = date.day
        month = date.strftime("%B").upper()
        year = date.year
        return f"{self.convert_day_to_words(day)} {month} {self.convert_year_to_words(year)}"

    def convert_day_to_words(self, day):
        words = [
            'FIRST', 'SECOND', 'THIRD', 'FOURTH', 'FIFTH', 'SIXTH', 'SEVENTH', 'EIGHTH', 'NINTH', 'TENTH',
            'ELEVENTH', 'TWELFTH', 'THIRTEENTH', 'FOURTEENTH', 'FIFTEENTH', 'SIXTEENTH', 'SEVENTEENTH',
            'EIGHTEENTH', 'NINETEENTH', 'TWENTIETH', 'TWENTY FIRST', 'TWENTY SECOND', 'TWENTY THIRD',
            'TWENTY FOURTH', 'TWENTY FIFTH', 'TWENTY SIXTH', 'TWENTY SEVENTH', 'TWENTY EIGHTH', 'TWENTY NINTH',
            'THIRTIETH', 'THIRTY FIRST'
        ]
        return words[day - 1]

    def convert_year_to_words(self, year):
        ones = ['', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE']
        teens = ['TEN', 'ELEVEN', 'TWELVE', 'THIRTEEN', 'FOURTEEN', 'FIFTEEN', 'SIXTEEN', 'SEVENTEEN', 'EIGHTEEN', 'NINETEEN']
        tens = ['', '', 'TWENTY', 'THIRTY', 'FORTY', 'FIFTY', 'SIXTY', 'SEVENTY', 'EIGHTY', 'NINETY']

        str_year = str(year)
        words = f"{ones[int(str_year[0])]} THOUSAND "
        second_pair = int(str_year[1:3])

        if second_pair < 10:
            words += f"{ones[second_pair]} "
        elif second_pair < 20:
            words += f"{teens[second_pair - 10]} "
        else:
            words += f"{tens[second_pair // 10]} "
            if second_pair % 10 != 0:
                words += f"{ones[second_pair % 10]} "

        words += ones[int(str_year[3])]
        return words.strip()

    def convert_year_to_full_words(self, year):
        ones = ['', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE']
        teens = ['TEN', 'ELEVEN', 'TWELVE', 'THIRTEEN', 'FOURTEEN', 'FIFTEEN', 'SIXTEEN', 'SEVENTEEN', 'EIGHTEEN', 'NINETEEN']
        tens = ['', '', 'TWENTY', 'THIRTY', 'FORTY', 'FIFTY', 'SIXTY', 'SEVENTY', 'EIGHTY', 'NINETY']

        num = int(year)
        words = ''

        if 2000 <= num < 3000:
            words = 'TWO THOUSAND'
            last_two = num % 100

            if last_two > 0:
                words += ' '
                if last_two < 10:
                    words += ones[last_two]
                elif last_two < 20:
                    words += teens[last_two - 10]
                else:
                    words += tens[last_two // 10]
                    if last_two % 10 != 0:
                        words += f' {ones[last_two % 10]}'
        return words

import frappe
from frappe.utils import nowdate
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

@frappe.whitelist()
def create_payment_entry(tcr_name):
    # Get the Transfer Certificate Request document
    doc = frappe.get_doc("Transfer Certificate Request", tcr_name)

    # Ensure 'admission_no' is set and is a valid Customer
    if not doc.admission_no:
        frappe.throw("Admission No is not set in Transfer Certificate Request.")
    
    if not frappe.db.exists("Customer", doc.admission_no):
        frappe.throw(f"Customer with ID {doc.admission_no} does not exist.")

    # Create a new Payment Entry document
    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Receive"
    pe.posting_date = nowdate()
    pe.company = frappe.defaults.get_user_default("company")
    pe.party_type = "Customer"
    pe.party = doc.admission_no  # Set the customer from the admission_no field
    pe.party_name = frappe.db.get_value("Customer", doc.admission_no, "customer_name")
    pe.received_amount = doc.net_total or 0
    pe.paid_amount = doc.net_total or 0

    # Set default accounts for payment entry (receiving from customer)
    pe.paid_from = frappe.get_value("Account", {
        "company": pe.company,
        "account_type": "Bank",
        "is_group": 0
    })  # Set default bank account (for paid_from)
    pe.paid_to = frappe.get_value("Account", {
        "company": pe.company,
        "account_type": "Receivable",
        "is_group": 0
    })  # Set Receivable account

    pe.reference_no = doc.name
    pe.reference_date = nowdate()

    # Set the custom field 'custom_tcr_reference' to link the TCR to Payment Entry
    pe.custom_tcr_reference = doc.name  # This links the Payment Entry to TCR

    # Insert & save Payment Entry
    pe.insert(ignore_permissions=True)
    
    # Save again after the insert to make sure everything is saved properly
    pe.save()

    # Return the name of the Payment Entry
    frappe.msgprint(f"Payment Entry {pe.name} created with TCR reference.")
    return pe.name



# transfer_certificate_request.py

import frappe
from frappe.utils.background_jobs import enqueue
from frappe import _

def send_tcr_guardian_mail(doc, method=None):
    if doc.workflow_state != "Awaiting VP Review":
        return

    # Fetch guardian emails
    guardian_emails = frappe.db.sql("""
        SELECT g.email_address as guardian_email 
        FROM `tabStudent Guardian` sg
        JOIN `tabGuardian` g ON sg.guardian = g.name
        WHERE sg.parent = %s
        GROUP BY g.name
    """, (doc.admission_no,), as_dict=True)

    guardian_email_list = [entry["guardian_email"] for entry in guardian_emails if entry["guardian_email"]]
    if not guardian_email_list:
        return

    # Fetch values from Company
    company = doc.institute
    bcc_email, raw_template, print_format = frappe.db.get_value(
        "Company",
        company,
        ["default_email", "custom_parent_email_template", "custom_tcr_print_format"]
    )

    bcc_list = [bcc_email] if bcc_email else []

    # Render email message using the template
    if raw_template:
        try:
            message = frappe.render_template(raw_template, {"doc": doc})
        except Exception as e:
            frappe.log_error(f"Template rendering error for {doc.name}: {str(e)}", "send_tcr_guardian_mail")
            message = fallback_message(doc.admission_no)
    else:
        message = fallback_message(doc.admission_no)

    subject = _("Transfer Certificate Request for {0}").format(doc.admission_no)

    # Generate PDF using the custom print format
    pdf = None
    if print_format:
        try:
            pdf = frappe.get_print(
                doctype=doc.doctype,
                name=doc.name,
                print_format=print_format,
                as_pdf=True
            )
        except Exception as e:
            frappe.log_error(f"PDF generation failed for {doc.name}: {str(e)}", "send_tcr_guardian_mail")

    attachments = [{"fname": f"TCR_{doc.name}.pdf", "fcontent": pdf}] if pdf else []

    # Send the email
    try:
        enqueue(method=frappe.sendmail, queue="short", timeout=300, is_async=True,
            recipients=guardian_email_list,
            bcc=bcc_list,
            sender=None,
            subject=subject,
            message=message,
            attachments=attachments,
            now=True
        )
        frappe.logger().info(f"Guardian mail for TCR {doc.name} queued successfully with PDF.")
        
        # Show success message
        frappe.msgprint(_("Transfer Certificate Request email has been successfully queued and sent."))
        
    except Exception as e:
        frappe.log_error(f"Email send error for {doc.name}: {str(e)}", "send_tcr_guardian_mail")

def fallback_message(admission_no):
    return _(
        """
        Dear Guardian,<br><br>
        The Transfer Certificate Request for your ward (Admission No: <strong>{0}</strong>) 
        has been approved by the Admin and is now under review by the Vice Principal.<br><br>
        Regards,<br>School Office
        """
    ).format(admission_no)







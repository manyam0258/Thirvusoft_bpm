# transfer_certificate_request.py
import frappe
from frappe.model.document import Document

class TransferCertificateRequest(Document):
    def before_save(self):
        if not self.admission_no:
            return

        student = frappe.get_doc('Student', self.admission_no)

        self.name_of_the_student = student.student_name
        self.gender = student.gender
        self.udise_pen = student.uidai_no
        self.dob_figures = student.date_of_birth
        self.dob_words = self.convert_date_to_words(student.date_of_birth)
        self.nationality = student.nationality
        self.category = student.category
        self.date_of_joining = student.joining_date

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

        # Program Enrollment
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

            # Clear and add subjects studied
            self.set('subjects_studied', [])
            for course in full_pe.courses:
                self.append('subjects_studied', {
                    'course': course.course,
                    'course_name': course.course_name
                })

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
0.00
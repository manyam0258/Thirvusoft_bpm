import frappe
import json
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc
from frappe import _

@frappe.whitelist()
def make_fee_schedule(source_name, dialog_values, per_component_amount, total_amount, target_doc=None):
    dialog_values = json.loads(dialog_values)

    # Ensure per_component_amount is properly formatted
    if isinstance(per_component_amount, str):
        per_component_amount = json.loads(per_component_amount)  # Convert JSON string to dict
    if isinstance(per_component_amount, list):  # Convert list to dictionary
        per_component_amount = {comp["fees_category"]: comp["total"] for comp in per_component_amount}

    student_groups = dialog_values.get("student_groups", [])
    fee_plan_wise_distribution = [fee_plan.get("due_date") for fee_plan in dialog_values.get("distribution", [])]

    for distribution in dialog_values.get("distribution", []):
        validate_due_date(distribution.get("due_date"), distribution.get("idx"))

        doc = get_mapped_doc(
            "Fee Structure",
            source_name,
            {
                "Fee Structure": {"doctype": "Fee Schedule"},
                "Fee Component": {
                    "doctype": "Fee Component",
                    "field_map": {
                        "fees_category": "fees_category",
                        "amount": "amount",
                        "discount": "discount",
                        "total": "total"
                    }
                }
            },
        )

        doc.due_date = distribution.get("due_date")
        if distribution.get("term"):
            doc.academic_term = distribution.get("term")

        # Override the component calculations
        for component in doc.components:
            component.total = per_component_amount.get(component.fees_category, component.total)

            if not component.discount:
                component.discount = 0

            # Ensure correct calculation and avoid division by zero
            if component.discount < 100:
                component.amount = flt((component.total) / (100 - component.discount)) * 100
            else:
                component.amount = component.total  # If discount is 100%, amount = total

        doc.total_amount = distribution.get("amount")

        # Assigning student groups
        for group in student_groups:
            fee_schedule_student_group = doc.append("student_groups", {})
            fee_schedule_student_group.student_group = group.get("student_group")

        doc.save()

    return len(fee_plan_wise_distribution)

def validate_due_date(due_date, idx):
    """Ensure due date is not in the past"""
    if due_date < frappe.utils.nowdate():
        frappe.throw(_("Due Date in row {0} should be today or a future date.").format(idx))

@frappe.whitelist()
def make_term_wise_fee_schedule(source_name, target_doc=None):
    return get_mapped_doc(
        "Fee Structure",
        source_name,
        {
            "Fee Structure": {
                "doctype": "Fee Schedule",
                "validation": {"docstatus": ["=", 1]},
            },
            "Fee Component": {"doctype": "Fee Component"},
        },
        target_doc,
    )

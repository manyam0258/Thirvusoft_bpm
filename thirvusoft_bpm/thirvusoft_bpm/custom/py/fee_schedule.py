import frappe
from frappe.model.mapper import get_mapped_doc
import erpnext
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, cstr, flt, money_in_words
from frappe.utils.background_jobs import enqueue
from frappe.utils.csvutils import getlink


@frappe.whitelist()
def get_fee_structure(source_name, target_doc=None):
    fee_request = get_mapped_doc(
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
        ignore_permissions=True,
    )

    # Debugging log
    frappe.msgprint(f"Fetched Fee Structure: {fee_request.as_json()}")

    return fee_request
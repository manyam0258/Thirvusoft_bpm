import frappe
import json
from frappe.utils import call_hook_method
from frappe.utils.password import get_decrypted_password
from frappe.utils.data import urlencode
from frappe.integrations.utils import make_get_request, make_post_request


def custom_authorize_payment(self):
    """
    Monkeypatched version of authorize_payment
    """
    data = json.loads(self.integration_request.data)
    ref_name = self.integration_request.reference_docname
    comp = frappe.db.get_value("Payment Request", ref_name, "company")
    company_doc = frappe.get_doc("Company", comp)

    try:
        resp = make_get_request(
            f"https://api.razorpay.com/v1/payments/{self.data.razorpay_payment_id}",
            auth=(company_doc.api_key, company_doc.get_password(fieldname="api_secret", raise_exception=False)),
        )

        if resp.get("status") == "authorized":
            self.integration_request.update_status(data, "Authorized")
            self.flags.status_changed_to = "Authorized"

        elif resp.get("status") == "captured":
            self.integration_request.update_status(data, "Completed")
            self.flags.status_changed_to = "Completed"

        elif data.get("subscription_id"):
            if resp.get("status") == "refunded":
                self.integration_request.update_status(data, "Completed")
                self.flags.status_changed_to = "Verified"

        else:
            frappe.log_error(message=str(resp), title="Razorpay Payment not authorized")

    except Exception:
        frappe.log_error()

    status = frappe.flags.integration_request.status_code
    redirect_to = data.get("redirect_to") or None
    redirect_message = data.get("redirect_message") or None

    if self.flags.status_changed_to in ("Authorized", "Verified", "Completed"):
        if self.data.reference_doctype and self.data.reference_docname:
            custom_redirect_to = None
            try:
                frappe.flags.data = data
                custom_redirect_to = frappe.get_doc(
                    self.data.reference_doctype, self.data.reference_docname
                ).run_method("on_payment_authorized", self.flags.status_changed_to)
            except Exception:
                frappe.log_error(frappe.get_traceback())

            if custom_redirect_to:
                redirect_to = custom_redirect_to

        redirect_url = (
            f"payment-success?doctype={self.data.reference_doctype}&docname={self.data.reference_docname}"
        )
    else:
        redirect_url = "payment-failed"

    if redirect_to:
        redirect_url += "&" + urlencode({"redirect_to": redirect_to})
    if redirect_message:
        redirect_url += "&" + urlencode({"redirect_message": redirect_message})

    return {"redirect_to": redirect_url, "status": status}


def custom_capture_payment(is_sandbox=False, sanbox_response=None):
    """
    Monkeypatched version of capture_payment.
    """
    for doc in frappe.get_all(
        "Integration Request",
        filters={"status": "Authorized", "integration_request_service": "Razorpay"},
        fields=["name", "data", "reference_docname"]
    ):
        try:
            if is_sandbox:
                resp = sanbox_response
            else:
                data = json.loads(doc.data)
                ref_name = doc.reference_docname
                comp = frappe.db.get_value("Payment Request", ref_name, "company")
                company_doc = frappe.get_doc("Company", comp)

                # First, verify status is still authorized
                resp = make_get_request(
                    f"https://api.razorpay.com/v1/payments/{data.get('razorpay_payment_id')}",
                    auth=(company_doc.api_key, company_doc.get_password(fieldname="api_secret", raise_exception=False)),
                )

                if resp.get("status") == "authorized":
                    # Then, capture it
                    resp = make_post_request(
                        f"https://api.razorpay.com/v1/payments/{data.get('razorpay_payment_id')}/capture",
                        auth=(company_doc.api_key, company_doc.get_password(fieldname="api_secret", raise_exception=False)),
                        data={"amount": data.get("amount")},
                    )

            if resp.get("status") == "captured":
                frappe.db.set_value("Integration Request", doc.name, "status", "Completed")

        except Exception:
            # Log and mark as failed
            integration_doc = frappe.get_doc("Integration Request", doc.name)
            integration_doc.status = "Failed"
            integration_doc.error = frappe.get_traceback()
            integration_doc.save()
            frappe.log_error(integration_doc.error, f"{doc.name} Failed")



def custom_validate_payment_callback(data):
    """
    Monkeypatched version of validate_payment_callback
    """
    def _throw():
        frappe.throw(_("Invalid Subscription"), exc=frappe.InvalidStatusError)

    subscription_id = (
        data.get("payload", {})
            .get("subscription", {})
            .get("entity", {})
            .get("id")
    )

    if not subscription_id:
        _throw()

    controller = frappe.get_doc("Razorpay Settings")
    settings = controller.get_settings(data)

    ref_name = data.get("title")
    comp = frappe.db.get_value("Payment Request", ref_name, "company")
    company_doc = frappe.get_doc("Company", comp)

    resp = make_get_request(
        f"https://api.razorpay.com/v1/subscriptions/{subscription_id}",
        auth=(company_doc.api_key, company_doc.get_password(fieldname="api_secret", raise_exception=False)),
    )

    if resp.get("status") != "active":
        _throw()


def monkey_patch_razorpay():
    from payments.payment_gateways.doctype.razorpay_settings.razorpay_settings import RazorpaySettings
    from payments.payment_gateways.doctype.razorpay_settings import razorpay_settings

    # Monkey patch all 3 methods
    RazorpaySettings.authorize_payment = custom_authorize_payment
    razorpay_settings.capture_payment = custom_capture_payment
    razorpay_settings.validate_payment_callback = custom_validate_payment_callback  # 🔥 Patch here


# Call patch function on import
monkey_patch_razorpay()
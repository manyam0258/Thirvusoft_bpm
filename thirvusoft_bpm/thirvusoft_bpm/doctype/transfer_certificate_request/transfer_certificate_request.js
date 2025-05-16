// Copyright (c) 2024, BPM and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Transfer Certificate Request", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Transfer Certificate Request', {
    refresh(frm) {
        if (
            frm.doc.docstatus === 1 &&
            frm.doc.seat_retained &&
            frm.doc.custom_seat_retain_upto
        ) {
            frappe.msgprint(`Seat will be retained until <b>${frappe.format_date(frm.doc.custom_seat_retain_upto)}</b>`);
        }
    }
});


frappe.ui.form.on('Transfer Certificate Request', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('Create Payment Entry'), function () {
                frappe.call({
                    method: 'thirvusoft_bpm.thirvusoft_bpm.doctype.transfer_certificate_request.transfer_certificate_request.create_payment_entry',
                    args: {
                        tcr_name: frm.doc.name
                    },
                    callback: function (r) {
                        if (r.message) {
                            frappe.set_route("Form", "Payment Entry", r.message);
                        }
                    }
                });
            });
        }
    }
});



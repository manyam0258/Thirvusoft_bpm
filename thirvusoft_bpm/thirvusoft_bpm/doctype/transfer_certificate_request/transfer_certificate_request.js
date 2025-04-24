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


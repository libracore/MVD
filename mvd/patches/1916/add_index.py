import frappe

def execute():
    if not mitgl_sinv_index_exists():
        frappe.db.add_index(
            "Sales Invoice",
            [
                "mv_mitgliedschaft",
                "docstatus",
                "ist_mitgliedschaftsrechnung",
                "status",
                "mitgliedschafts_jahr"
            ],
            "idx_mv_membership_invoice"
        )

    if not mitgl_pe_index_exists():
        frappe.db.add_index(
            "Payment Entry Reference",
            [
                "reference_doctype",
                "reference_name",
                "docstatus",
                "creation"
            ],
            "idx_payment_entry_ref_lookup"
        )

    if not hv_sinv_index_exists():
        frappe.db.add_index(
            "Sales Invoice",
            [
                "mv_mitgliedschaft",
                "docstatus",
                "ist_hv_rechnung",
                "status",
                "posting_date"
            ],
            "idx_mv_hv_invoice"
        )


def mitgl_sinv_index_exists():
    indexes = frappe.db.sql("""
        SHOW INDEX
        FROM `tabSales Invoice`
        WHERE Key_name = 'idx_mv_membership_invoice'
    """, as_dict=True)

    return bool(indexes)

def mitgl_pe_index_exists():
    indexes = frappe.db.sql("""
        SHOW INDEX
        FROM `tabPayment Entry Reference`
        WHERE Key_name = 'idx_payment_entry_ref_lookup'
    """, as_dict=True)

    return bool(indexes)

def hv_sinv_index_exists():
    indexes = frappe.db.sql("""
        SHOW INDEX
        FROM `tabSales Invoice`
        WHERE Key_name = 'idx_mv_hv_invoice'
    """, as_dict=True)

    return bool(indexes)
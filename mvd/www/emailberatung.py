from __future__ import unicode_literals
import frappe
import json

no_cache = 1

def get_context(context):
    context.show_sidebar = True
    authorization_header = frappe.get_request_header("Authorization", None).split(" ") if frappe.get_request_header("Authorization") else None
    if authorization_header:
        # check tbd
        pass
    else:
        frappe.local.flags.redirect_location = "/nologin"
        raise frappe.Redirect

@frappe.whitelist(allow_guest=True)
def new_onlineberatung(**kwargs):
    args = json.loads(kwargs['kwargs'])
    # ~ frappe.throw(args['mitgliedschaft_nr'])
    if frappe.db.exists("Mitgliedschaft", args['mv_mitgliedschaft']):
        args['doctype'] = "Onlineberatung"
        new_ob = frappe.get_doc(args)
        new_ob.insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.msgprint("Vielen Dank, die Anfrage wurde gespeichert.")
    else:
        frappe.throw("Die Mitgliedschaft {0} konnte nicht abgerufen werden".format(args['mv_mitgliedschaft']))

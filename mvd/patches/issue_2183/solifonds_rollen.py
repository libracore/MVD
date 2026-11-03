import frappe

def execute():
    # Rollen für den Ablauf Solidaritätsfonds (analog zu MV_Mandat)
    try:
        for rolle in ("MV_Solifonds_Vorpruefung", "MV_Solifonds_GL"):
            if not frappe.db.exists("Role", rolle):
                frappe.get_doc({
                    "doctype": "Role",
                    "role_name": rolle,
                    "desk_access": 1
                }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as err:
        print("Patch solifonds_rollen failed")
        print(str(err))

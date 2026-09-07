import frappe
from frappe import _

def execute():
    try:
        baum_vorlagen = frappe.db.sql(
            """
                SELECT `name` FROM `tabVorlagen Baum`
            """,
            as_dict=True
        )
        for baum_vorlage in baum_vorlagen:
            bm = frappe.get_doc("Vorlagen Baum", baum_vorlage.name)
            row_added = False
            for email_vorlage in bm.email_vorlagen:
                email_template = frappe.get_doc("Email Template", email_vorlage.email_template)
                try:
                    textvorlage = create_textvorlage(email_template)
                    textvorlage_row = bm.append("textvorlagen", {})
                    textvorlage_row.textvorlage = textvorlage
                    row_added = True
                except:
                    pass
            if row_added:
                bm.use_for_textvorlagen = 1
                bm.save()

        frappe.db.commit()
    except Exception as err:
        print("Patch vorlagenbaum_mail_zu_text failed")
        print(str(err))
        pass
    return

def create_textvorlage(email_template):
    tv = frappe.new_doc("Textvorlagen")
    tv.titel = email_template.subject
    tv.text = email_template.response
    tv.insert()
    return tv.name
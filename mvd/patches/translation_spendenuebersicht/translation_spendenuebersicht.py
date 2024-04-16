import frappe
from frappe import _
from mvd.mvd.doctype.mitgliedschaft.utils import get_anredekonvention

def execute():
    print("Erstelle Übersaetzungen")
    new_translation_de = frappe.get_doc({
        "doctype": "Translation",
        "language": "de",
        "source_name": "Spendenuebersicht",
        "target_name": "Spendenübersicht"
    })
    new_translation_de.insert()
    new_translation_en = frappe.get_doc({
        "doctype": "Translation",
        "language": "en",
        "source_name": "Spendenuebersicht",
        "target_name": "Spendenübersicht"
    })
    new_translation_en.insert()
    return

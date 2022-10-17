import frappe
from frappe import _
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_anredekonvention

def execute():
    print("Adding Translations")
    to_translate = [
        ['Sehr geehrter Herr {nachname}', 'Cher Monsieur {nachname}'],
        ['Sehr geehrte Frau {nachname}', 'Chère Madame {nachname}'],
        # ~ ['Guten Tag {vorname} {nachname}', ''],
        # ~ ['Guten Tag', ''],
        # ~ ['Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}', ''],
        ['Sehr geehrter Herr {vorname_1} {nachname_1}, sehr geehrter Herr {vorname_2} {nachname_2}', 'Cher Monsieur {vorname_1} {nachname_1}, cher Monsieur {vorname_2} {nachname_2}'],
        ['Sehr geehrte Frau {vorname_1} {nachname_1}, sehr geehrte Frau {vorname_2} {nachname_2}', 'Mesdames {vorname_1} {nachname_1} et {vorname_2} {nachname_2}'],
        ['Sehr geehrter Herr {nachname_1}, sehr geehrter Herr {nachname_2}', 'Cher Monsieur {nachname_1}, cher Monsieur {nachname_2}'],
        ['Sehr geehrte Frau {nachname_1}, sehr geehrte Frau {nachname_2}', 'Chère Madame {nachname_1}, chère Madame {nachname_2}'],
        ['Sehr geehrte Herr und Frau {nachname_1}', 'Chère Madame {nachname_1}, cher Monsieur {nachname_1}'],
        ['Sehr geehrte Frau und Herr {nachname_1}', 'Chère Madame {nachname_1}, cher Monsieur {nachname_1}'],
        ['Sehr geehrter Herr {nachname_1}, sehr geehrte Frau {nachname_2}', 'Chère Madame {nachname_2}, cher Monsieur {nachname_1}'],
        ['Sehr geehrte Frau {nachname_1}, sehr geehrter Herr {nachname_2}', 'Chère Madame {nachname_1}, cher Monsieur {nachname_1}'],
        ['Sehr geehrte Herr und Frau {nachname_1}', 'Chère Madame {nachname_1}, cher Monsieur {nachname_1}']
    ]
    loop = 1
    
    for translation in to_translate:
        print("Adding translation {loop} of {total}".format(loop=loop, total=len(to_translate)))
        translate(translation)
        loop += 1
    frappe.db.commit()
    
    print("Update FR Mitgliedschaften")
    mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `language` = 'fr' AND `status_c` = 'Regulär'""", as_dict=True)
    loop = 1
    for mitgliedschaft in mitgliedschaften:
        print("Update Mitgliedschaft {loop} of {total}".format(loop=loop, total=len(mitgliedschaften)))
        briefanrede = get_anredekonvention(mitgliedschaft=mitgliedschaft.name)
        rg_briefanrede = get_anredekonvention(mitgliedschaft=mitgliedschaft.name, rg=True)
        frappe.db.set_value('Mitgliedschaft', mitgliedschaft.name, 'briefanrede', briefanrede)
        frappe.db.set_value('Mitgliedschaft', mitgliedschaft.name, 'rg_briefanrede', rg_briefanrede)
        loop += 1
    frappe.db.commit()

def translate(text):
    translation = frappe.get_doc({
        "doctype": "Translation",
        "language": "fr",
        "source_name": text[0],
        "target_name": text[1]
    }).insert(ignore_permissions=True)
    return

# -*- coding: utf-8 -*-
# #2242: Vorstand neu als Tabelle «Vorstand» in der Sektion statt Häkchen «Vorstand» bei der Termin-Kontaktperson.
# Übernimmt die markierten Kontaktpersonen (Name, E-Mail und Benutzer des ersten verknüpften Users)
# und ergänzt bestehende Vorstandsstimmen um Name/E-Mail/Benutzer. Mehrfach ausführbar.
from __future__ import unicode_literals
import frappe


def execute():
    frappe.reload_doc("mvd", "doctype", "sektion_vorstand")
    frappe.reload_doc("mvd", "doctype", "sektion")
    frappe.reload_doc("mvd", "doctype", "mandat_vorstand_stimme")

    personen = {}
    for kp in frappe.db.sql("""SELECT `name`, `kontakt`, `sektion_id`, `disabled` FROM `tabTermin Kontaktperson`""", as_dict=True):
        user = frappe.db.sql_list("""SELECT `user` FROM `tabTermin Kontaktperson Multi User`
            WHERE `parent` = %s AND IFNULL(`user`, '') != '' ORDER BY `idx`""", kp.name)
        user = user[0] if user else None
        personen[kp.name] = frappe._dict(kp, user=user,
            email=frappe.db.get_value("User", user, "email") if user else None,
            vorstand_name=kp.kontakt or kp.name)

    # Spalte bleibt nach dem Entfernen des Felds in der Tabelle stehen (Frappe löscht keine Spalten)
    if frappe.db.has_column("Termin Kontaktperson", "ist_vorstand"):
        for name in frappe.db.sql_list("""SELECT `name` FROM `tabTermin Kontaktperson` WHERE `ist_vorstand` = 1"""):
            p = personen[name]
            if not p.sektion_id or not p.email:
                print("Vorstand {0}: keine Sektion oder E-Mail, nicht übernommen".format(name))
                continue
            if frappe.db.exists("Sektion Vorstand", {"parent": p.sektion_id, "parentfield": "vorstand", "email": p.email}):
                continue
            idx = frappe.db.sql("""SELECT IFNULL(MAX(`idx`), 0) FROM `tabSektion Vorstand`
                WHERE `parent` = %s AND `parentfield` = 'vorstand'""", p.sektion_id)[0][0]
            frappe.get_doc({
                "doctype": "Sektion Vorstand", "parent": p.sektion_id, "parenttype": "Sektion", "parentfield": "vorstand",
                "idx": idx + 1, "vorstand_name": p.vorstand_name, "email": p.email, "user": p.user,
                "aktiv": 0 if p.disabled else 1
            }).db_insert()

    for s in frappe.db.sql("""SELECT `name`, `kontaktperson` FROM `tabMandat Vorstand Stimme`
            WHERE IFNULL(`kontaktperson`, '') != '' AND IFNULL(`vorstand_name`, '') = ''""", as_dict=True):
        p = personen.get(s.kontaktperson) or frappe._dict(vorstand_name=s.kontaktperson)
        frappe.db.set_value("Mandat Vorstand Stimme", s.name,
            {"vorstand_name": p.vorstand_name, "email": p.email, "user": p.user}, update_modified=False)

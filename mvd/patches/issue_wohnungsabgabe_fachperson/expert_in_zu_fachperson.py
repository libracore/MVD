import frappe

# Auswahl des bisherigen Select-Felds Wohnungsabgabe.expert_in; diese Personen bleiben aktiv
AKTIVE_EXPERT_INNEN = [
    "Baumeler, Markus", "Egger, Martin", "Fretz, Markus", "Fuhrer, Peter", "Gerspacher Marina",
    "Guldimann, Ursula", "Hofer, Werner", "Kofmel, Urban", "Merz, David", "Schärer, Mark",
    "Tschanz, Roland", "Wagner, Susanne"
]

def execute():
    # Wohnungsabgabe: expert_in war ein Select-Feld und wird ein Link auf "Wohnungsabgabe Fachperson".
    # Pro bisherigem Namen wird eine Fachperson angelegt, deren name ("Nachname, Vorname") dem
    # gespeicherten Wert entspricht. Läuft vor dem DocType-Sync, darum reload_doc.
    #
    # Bewusst ohne try/except und ohne eigenen commit: Frappe führt den Patch in einer Transaktion aus,
    # rollt bei einem Fehler zurück und trägt ihn nicht ins Patch Log ein. Der Patch läuft dann beim
    # nächsten migrate erneut (er ist wiederholbar) statt halb migrierte Daten zu hinterlassen, die
    # nach der Umstellung auf das Link-Feld das Speichern von Aufträgen verhindern würden.
    frappe.reload_doc("mvd", "doctype", "wohnungsabgabe_fachperson")

    werte = frappe.db.sql("""
        SELECT `expert_in`, MIN(`sektion_id`) AS `sektion_id`
        FROM `tabWohnungsabgabe`
        WHERE IFNULL(`expert_in`, '') != ''
        GROUP BY `expert_in`
    """, as_dict=True)
    sektion_je_wert = {w.expert_in: w.sektion_id for w in werte}
    for wert in AKTIVE_EXPERT_INNEN:
        if wert not in sektion_je_wert:
            sektion_je_wert[wert] = "MVBE"

    angelegt = 0
    umbenannt = 0
    for wert, sektion_id in sektion_je_wert.items():
        if "," in wert:
            teile = wert.split(",", 1)
        else:
            # ohne Komma, z. B. "Meiner Marili"
            teile = wert.strip().split(" ", 1)
        nachname = teile[0].strip()
        vorname = teile[1].strip() if len(teile) > 1 else "-"
        name = "{0}, {1}".format(nachname, vorname)

        if not frappe.db.exists("Wohnungsabgabe Fachperson", name):
            aktiv = wert in AKTIVE_EXPERT_INNEN
            frappe.get_doc({
                "doctype": "Wohnungsabgabe Fachperson",
                "sektion_id": sektion_id or "MVBE",
                "nachname": nachname,
                "vorname": vorname,
                "disabled": 0 if aktiv else 1
            }).insert(ignore_permissions=True)
            angelegt += 1
            print("  Fachperson angelegt: {0} ({1}{2})".format(name, sektion_id or "MVBE", "" if aktiv else ", deaktiviert"))

        if name != wert:
            frappe.db.sql("""
                UPDATE `tabWohnungsabgabe` SET `expert_in` = %s WHERE `expert_in` = %s
            """, (name, wert))
            anzahl = frappe.db.sql("""SELECT ROW_COUNT()""")[0][0]
            umbenannt += anzahl
            print("  expert_in umgeschrieben: '{0}' -> '{1}' ({2} Wohnungsabgaben)".format(wert, name, anzahl))

    print("  {0} Fachpersonen angelegt, {1} Wohnungsabgaben umgeschrieben".format(angelegt, umbenannt))

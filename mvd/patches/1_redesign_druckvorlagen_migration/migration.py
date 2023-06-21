import frappe
from frappe import _

def execute():
    try:
        print("Migriere Druckvorlagen (Druckformat Redesign)")
        frappe.reload_doc("mvd", "doctype", "Druckvorlage")
        druckvorlagen = frappe.db.sql("""SELECT `name` FROM `tabDruckvorlage`""", as_dict=True)
        total = len(druckvorlagen)
        loop = 1
        for druckvorlage in druckvorlagen:
            print("{0} of {1}".format(loop, total))
            d = frappe.get_doc("Druckvorlage", druckvorlage.name)
            d.migriert_neues_cd = 1
            d.seiten = []
            
            # ausklammern von E-Mail Vorlagen
            if not d.e_mail_vorlage:
                # Seite 1 (von möglichen 3)
                if int(d.anzahl_seiten) >= 1:
                    neue_1_seite = d.append('seiten', {})
                    neue_1_seite.stichwort = 'Blatt 1'
                    
                    # Inhalt
                    neue_1_seite.inhalt = d.seite_1a
                    
                    # Kopfzeile
                    if not d.logo_ausblenden:
                        neue_1_seite.kopfzeile = 1
                    
                    # Alte Fusszeile = Seitenzahlen
                    if not d.seite_1_fusszeile_ausblenden:
                        neue_1_seite.seitenzahlen = 1
                    
                    # Weil früher die MVD-Infos in der Fusszeile (welche neu nur noch die Seitenzahlen beinhaltet) war, ist neu der Referenzblock immer eingeblendet
                    neue_1_seite.referenzblock = 1
                    
                    # auf Seite 1 ist der Adressblock immer eingeblendet
                    neue_1_seite.adressblock = 1
                    
                    # Einzahlungsschein
                    if d.seite_1_qrr == 'Keiner':
                        neue_1_seite.einzahlungsschein = 0
                    else:
                        neue_1_seite.einzahlungsschein = 1
                        if d.seite_1_qrr == 'Mitgliedschaft':
                            neue_1_seite.ez_typ == 'Mitgliedschaft'
                        elif d.seite_1_qrr == 'HV':
                            neue_1_seite.ez_typ == 'Haftpflicht'
                        else:
                            # fallback
                            neue_1_seite.einzahlungsschein = 0
                    
                    # ggf. Rückseite
                    if d.doppelseitiger_druck:
                        neue_1_rueckseite = d.append('seiten', {})
                        neue_1_rueckseite.stichwort = 'Blatt 1 (Rückseite)'
                        # Inhalt
                        neue_1_rueckseite.inhalt = d.seite_1b
                
                # Seite 2 (von möglichen 3)
                if int(d.anzahl_seiten) >= 2:
                    neue_2_seite = d.append('seiten', {})
                    neue_2_seite.stichwort = 'Blatt 2'
                    
                    # Inhalt
                    neue_2_seite.inhalt = d.seite_2a
                    
                    # Kopfzeile
                    if not d.logo_ausblenden:
                        neue_2_seite.kopfzeile = 1
                    
                    # Alte Fusszeile = Seitenzahlen
                    if not d.seite_2_fusszeile_ausblenden:
                        neue_2_seite.seitenzahlen = 1
                    
                    if not d.seite_2_adressblock_ausblenden:
                        neue_2_seite.referenzblock = 1
                        neue_2_seite.adressblock = 1
                    
                    # Einzahlungsschein
                    if d.seite_2_qrr == 'Keiner':
                        neue_2_seite.einzahlungsschein = 0
                    else:
                        neue_2_seite.einzahlungsschein = 1
                        if d.seite_2_qrr == 'Mitgliedschaft':
                            neue_2_seite.ez_typ == 'Mitgliedschaft'
                        elif d.seite_2_qrr == 'HV':
                            neue_2_seite.ez_typ == 'Haftpflicht'
                        else:
                            # fallback
                            neue_2_seite.einzahlungsschein = 0
                    
                    # ggf. Rückseite
                    if d.doppelseitiger_druck:
                        neue_2_rueckseite = d.append('seiten', {})
                        neue_2_rueckseite.stichwort = 'Blatt 2 (Rückseite)'
                        # Inhalt
                        neue_2_rueckseite.inhalt = d.seite_2b
                
                # Seite 3 (von möglichen 3)
                if int(d.anzahl_seiten) >= 3:
                    neue_3_seite = d.append('seiten', {})
                    neue_3_seite.stichwort = 'Blatt 3'
                    
                    # Inhalt
                    neue_3_seite.inhalt = d.seite_3a
                    
                    # Kopfzeile
                    if not d.logo_ausblenden:
                        neue_3_seite.kopfzeile = 1
                    
                    # Alte Fusszeile = Seitenzahlen
                    if not d.seite_3_fusszeile_ausblenden:
                        neue_3_seite.seitenzahlen = 1
                    
                    if not d.seite_3_adressblock_ausblenden:
                        neue_3_seite.referenzblock = 1
                        neue_3_seite.adressblock = 1
                    
                    # Einzahlungsschein
                    if d.seite_3_qrr == 'Keiner':
                        neue_3_seite.einzahlungsschein = 0
                    else:
                        neue_3_seite.einzahlungsschein = 1
                        if d.seite_3_qrr == 'Mitgliedschaft':
                            neue_3_seite.ez_typ == 'Mitgliedschaft'
                        elif d.seite_3_qrr == 'HV':
                            neue_3_seite.ez_typ == 'Haftpflicht'
                        else:
                            # fallback
                            neue_3_seite.einzahlungsschein = 0
                    
                    # ggf. Rückseite
                    if d.doppelseitiger_druck:
                        neue_3_rueckseite = d.append('seiten', {})
                        neue_3_rueckseite.stichwort = 'Blatt 3 (Rückseite)'
                        # Inhalt
                        neue_3_rueckseite.inhalt = d.seite_3b
            
            d.save()
            
            loop += 1
            
        print("Migriere Sektionen (Druckformat Redesign)")
        frappe.reload_doc("mvd", "doctype", "Sektion")
        sektionen = frappe.db.sql("""SELECT `name` FROM `tabSektion`""", as_dict=True)
        total = len(sektionen)
        loop = 1
        for sektion in sektionen:
            print("{0} of {1}".format(loop, total))
            s = frappe.get_doc("Sektion", sektion.name)
            frappe.db.set_value("Sektion", sektion.name, 'referenzblock', s.fz_links + "<br>" + s.fz_mitte + "<br>" + s.fz_rechts)
            loop += 1
        
        frappe.db.commit()
    except Exception as err:
        print(err)
        print("Patch Druckvorlagen Migration failed")
        pass
    return

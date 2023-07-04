import frappe
from frappe import _

def execute():
    try:
        print("Migriere Korrespondenzen (Druckformat Redesign)")
        frappe.reload_doc("mvd", "doctype", "Korrespondenz")
        korrespondenzen = frappe.db.sql("""SELECT `name` FROM `tabKorrespondenz`""", as_dict=True)
        total = len(korrespondenzen)
        loop = 1
        for korrespondenz in korrespondenzen:
            print("{0} of {1}".format(loop, total))
            d = frappe.get_doc("Korrespondenz", korrespondenz.name)
            d.migriert_neues_cd = 1
            d.seiten = []
            
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
                neue_1_seite.einzahlungsschein = 0
                
                # Ausweis
                if d.seite_1_ausweis:
                    neue_1_seite.ausweis = 1
                
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
                neue_2_seite.einzahlungsschein = 0
                
                # Ausweis
                if d.seite_2_ausweis:
                    neue_2_seite.ausweis = 1
                
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
                neue_3_seite.einzahlungsschein = 0
                
                # Ausweis
                if d.seite_3_ausweis:
                    neue_3_seite.ausweis = 1
                
                # ggf. Rückseite
                if d.doppelseitiger_druck:
                    neue_3_rueckseite = d.append('seiten', {})
                    neue_3_rueckseite.stichwort = 'Blatt 3 (Rückseite)'
                    # Inhalt
                    neue_3_rueckseite.inhalt = d.seite_3b
            
            d.save()
            
            loop += 1
        
        frappe.db.commit()
    except Exception as err:
        print(err)
        print("Patch Korrespondenzen Migration failed")
        pass
    return

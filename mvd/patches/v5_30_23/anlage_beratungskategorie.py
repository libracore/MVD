import frappe
from frappe import _
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_ampelfarbe

def execute():
    beratungs_kategorien = [
        ['', 'Vor/nach der Miete'],
        ['101', 'Vertragsverhandlungen'],
        ['102', 'Mietvertrag'],
        ['103', 'MZ-Depot'],
        ['104', 'Whg-Übernahme'],
        ['105', 'Whg-Abgabe'],
        ['', 'Mietzins'],
        ['201', 'Anfangs-MZ'],
        ['202', 'MZ-Erhöhung'],
        ['203', 'MZ-Senkung'],
        ['204', 'MZ-Vorbehalt'],
        ['205', 'Rendite'],
        ['206', 'Orts- + Quartiersüblichkeit'],
        ['207', 'Ref.Zins'],
        ['208', 'Teuerung'],
        ['209', 'Allg. Kostensteigerungen'],
        ['210', 'Wertvermehrende Investitionen'],
        ['211', 'Formelles'],
        ['', 'Nebenkosten'],
        ['301', 'HK'],
        ['302', 'Betriebs-Kosten'],
        ['303', 'NK allgemein'],
        ['', 'Diverses während der Miete'],
        ['401', 'Mängel/Immissionen'],
        ['402', 'MZ-Hinterl.'],
        ['403', 'MZ-Red. Mängel'],
        ['404', 'Kl. Unterhalt'],
        ['405', 'Schadenersatz'],
        ['406', 'Versicherungs-Fragen'],
        ['407', 'Untermiete'],
        ['408', 'Solidar-Haftung'],
        ['409', 'Nachbarschaft/Hausordnung'],
        ['410', 'Haustiere'],
        ['411', 'Umbau/Renovation Vermieter'],
        ['412', 'Umbau/Renov. Mieter Entschädigung'],
        ['', 'Vermieter-Künd (ordentl/ausserord.)'],
        ['501', 'Form- oder Fristen-Fehler'],
        ['502', 'Rache-Kündigung'],
        ['503', 'Verkauf/Eigenbedarf'],
        ['504', 'Änderungs-Kündigung'],
        ['505', 'Sanierungs-Kündigung'],
        ['506', 'Zahlungsverzug Mieter'],
        ['507', 'Sorgfaltspflicht-Verletzung'],
        ['508', 'Erstreckung'],
        ['509', 'Allgemein'],
        ['', 'Mieter-Künd / ausserord. Auflösung'],
        ['601', 'Formelles'],
        ['602', 'wichtiger Grund'],
        ['603', 'Vorzeitige Rückgabe'],
        ['604', 'Allgemein'],
        ['', 'Empfehlungen MV'],
        ['701', 'Rechtsschutzfall/Mandat'],
        ['702', 'Nur Mandat (kein Rechtsschutz)'],
        ['703', 'Schlicht.Behörde'],
        ['704', 'Beizug Whg-Exp.'],
        ['', 'Dienstleistungen MV'],
        ['801', 'Brief (während Beratung)'],
        ['803', 'MZ-Überprüfung'],
        ['804', 'Beratung für Schlichtungsverhandl.']
    ]
    for beratungs_kategorie in beratungs_kategorien:
        print("Anlage {0}: {1}".format(beratungs_kategorie[0], beratungs_kategorie[1]))
        if len(beratungs_kategorie[0]) > 0:
            new_beratungs_kategorie = frappe.get_doc({
                'doctype': 'Beratungskategorie',
                'code': beratungs_kategorie[0],
                'kategorie': beratungs_kategorie[1],
                'titel': beratungs_kategorie[0] + " - " + beratungs_kategorie[1]
            }).insert()
        else:
            new_beratungs_kategorie = frappe.get_doc({
                'doctype': 'Beratungskategorie',
                'kategorie': beratungs_kategorie[1],
                'titel': beratungs_kategorie[1]
            }).insert()
    
    return

# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from datetime import datetime
from mvd.mvd.doctype.postretouren_log.libracore_facade import LibraCoreFacade
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr

class PostNotiz:
    mitgliedNummer = ''
    kategorie = ''
    von = datetime.now().date()
    notiz = ''

class PostRetour:
    sendungsNummer = ''
    auftragsNummer = ''
    mitgliedNummer = ''
    mitgliedId = ''
    legacyKategorieCode = 'MUWRETOUR'
    legacyNotiz = ''
    grundCode = 0
    grundBezeichnung = ''
    retoureMuWSequenceNumber = 0
    retoureDMC = ''
    retoureSendungsbild = ''
    datumErfasstPost = None
    neueAdresse = None
    rawData = ''

class PostRetourAdresse:
    validFrom = None
    validTo = None
    strasse = ''
    hausnummer = ''
    hausnummerZusatz = ''
    postleitzahl = ''
    ort = ''
    adresszusatz = ''
    postfach = False
    postfachNummer = ''

class PostRetourHandler:
    libracore = LibraCoreFacade()

    @staticmethod
    def create_moved_info(parts):
        company = parts[35]
        street_name = parts[42]
        house_number = parts[43]
        zip_code = parts[46]
        town_name = parts[48]

        # Filter out empty elements
        elements = filter(lambda x: len(x) > 0, [company, street_name, house_number, zip_code, town_name])
        return "Umzugsmeldung für Name1 oder Firma, " + ", ".join(elements)

    def create_notiz(self, company, sequence_nr, message):

        mw_ausgabe = self.libracore.get_mw_ausgabe(sequence_nr)

        notiz = "M+W Retoure (M+W Nr. {0}): {1} (Hauptmitglied".format(mw_ausgabe, message)
        
        if company:
            notiz += ", {0}".format(company)

        notiz += ", Mitgliedadresse)"

        return notiz

    def determine_category_and_message(self, parts):
        has_moved = parts[25] == 4
        if has_moved:
            moved_info = self.create_moved_info(parts)
            return "Adressrecherche", "Neu: " + moved_info

        retour_code = parts[4]

        if retour_code == "10":
            return "MUndWRetoure", "Weggezogen, Adresse unbekannt"

        if retour_code == "20" or retour_code == "30":
            return "MUndWRetoure", "Adresse unbekannt"

        if retour_code == "31":
            return "WuenschtKeineZeitung", "Frankierte Rücksendung"

        if retour_code == "40" or retour_code == "50":
            return "Verstorben", "Verstorben / Firma erloschen"

        if retour_code == "60":
            return "MUndWRetoure", "Briefkasten/Postfach wird nicht geleert"

        if retour_code == "70":
            return "WuenschtKeineZeitung", "Rückgabe durch Empfänger"

        if retour_code == "80":
            return "WuenschtKeineZeitung", "Nicht angenommen, Adresse korrekt"

        if retour_code == "90":
            return "WuenschtKeineZeitung", "Frankierte Rücksendung durch Empfänger"

        return "MUndWRetoure", "Retourengrund unbekannt"

    def get_post_objects(self, columns):
        mitglied_nr = columns[12][-9:-1]
        mitglied_id = get_mitglied_id_from_nr(mitglied_nr)
        sequence_nr = int(columns[12][-17:-9])

        (kategorie, message) = self.determine_category_and_message(columns)
        notiz = self.create_notiz(columns[35], sequence_nr, message)

        pr = PostRetour()
        pr.mitgliedNummer = mitglied_nr
        pr.mitgliedId = mitglied_id
        pr.auftragsNummer = columns[2]
        pr.sendungsNummer = columns[3]
        pr.grundCode = columns[4]
        pr.grundBezeichnung = columns[5]
        pr.legacyNotiz = notiz
        pr.retoureMuWSequenceNumber = sequence_nr
        pr.retoureDMC = columns[17]
        pr.retoureSendungsbild = columns[16]
        pr.datumErfasstPost = datetime.strptime(columns[0], '%d.%m.%Y').date()
        pr.neueAdresse = PostRetourAdresse()
        pr.neueAdresse.validFrom = datetime.fromisoformat(columns[29]).date() if len(columns[29]) > 0 else None
        pr.neueAdresse.validTo = datetime.fromisoformat(columns[30]).date() if len(columns[30]) > 0 else None
        pr.neueAdresse.strasse = columns[42]
        pr.neueAdresse.hausnummer = columns[43]
        pr.neueAdresse.hausnummerZusatz = columns[44]
        pr.neueAdresse.postleitzahl = columns[46]
        pr.neueAdresse.ort = columns[48]
        pr.neueAdresse.adresszusatz = columns[40]
        pr.neueAdresse.postfach = len(columns[52]) > 0
        pr.neueAdresse.postfachNummer = columns[52]

        pn = PostNotiz()
        pn.mitgliedNummer = mitglied_nr
        pn.kategorie = kategorie
        pn.notiz = notiz

        return pr, pn

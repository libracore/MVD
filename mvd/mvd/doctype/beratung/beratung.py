# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import today, now, getdate, get_datetime
import json
from bs4 import BeautifulSoup
from frappe.utils import cint
from frappe import _

class Beratung(Document):
    def validate(self):
        # keine Termine für nicht Mitglieder
        if len(self.termin) > 0:
            if not self.mv_mitgliedschaft or self.status == 'Nicht-Mitglied-Abgewiesen':
                frappe.throw("Nicht-Mitglieder dürfen keine Termine besitzen.")
        
        # Termin Filter handling
        if len(self.termin) > 0:
            self.hat_termine = 1
        else:
            self.hat_termine = 0
        if len(self.get_assigned_users()) > 0:
            self.zuweisung = 1
        else:
            self.zuweisung = 0
        
        # Beratungskategorien handling
        if not self.beratungskategorie_2:
            self.beratungskategorie_3 = None
        if not self.beratungskategorie:
            self.beratungskategorie_2 = None
        
        # MVBE-HACK
        if self.status == 'Rückfrage: Termin vereinbaren' and self.sektion_id == 'MVBE':
            if self.kontaktperson and len(self.termin) > 0:
                found_past_termin = False
                for termin in self.termin:
                    if getdate(termin.von) < getdate(now()):
                        found_past_termin = True
                
                if not found_past_termin:
                    self.status = 'Termin vereinbart'
        
        if self.kontaktperson and len(self.termin) > 0:
            if self.status in ('Eingang', 'Open'):
                found_past_termin = False
                for termin in self.termin:
                    if getdate(termin.von) < getdate(now()):
                        found_past_termin = True
                
                if not found_past_termin:
                    self.status = 'Termin vereinbart'
        
        # Statistik handling -> closed date tracker
        if self.status == 'Closed':
            if not self.geschlossen_am:
                self.geschlossen_am = today()
        else:
            if self.geschlossen_am:
                self.geschlossen_am = None
        
        # bei "Menü > E-Mail" gewährleisten, dass Empfänger von 'raised_by' übernommen wird
        if self.raised_by:
            self.email_id = self.raised_by
        
        # verknüpfung von mitgliedschaft auf basis email (wenn eingangsmailaccount-sektion == mitgliedschafts sektion)
        if self.raised_by and not self.mv_mitgliedschaft:
                mitgliedschaften = frappe.db.sql("""
                                                    SELECT
                                                        `name`,
                                                        `sektion_id`
                                                    FROM `tabMitgliedschaft`
                                                    WHERE
                                                    (`e_mail_1` = '{email}' OR `e_mail_2` = '{email}')
                                                    AND `status_c` = 'Regulär'""".format(email=self.raised_by), as_dict=True)
                
                if len(mitgliedschaften) == 1:
                    if self.sektion_id:
                        if self.sektion_id == mitgliedschaften[0].sektion_id:
                            self.mv_mitgliedschaft = mitgliedschaften[0].name
                            if self.beratungskategorie not in ('202 - MZ-Erhöhung', '300 - Nebenkosten'):
                                self.kontaktperson = frappe.db.get_value("Sektion", self.sektion_id, "default_emailberatung_todo_gruppe")
        
        # Titel aktualisierung
        titel = '{0}'.format(self.start_date)
        if self.mv_mitgliedschaft:
            titel += ' {0} {1}'.format(frappe.db.get_value("Mitgliedschaft", self.mv_mitgliedschaft, "vorname_1"), frappe.db.get_value("Mitgliedschaft", self.mv_mitgliedschaft, "nachname_1"))
        elif self.raised_by_name:
            titel += ' {0}'.format(self.raised_by_name)
        elif self.raised_by:
            titel += ' {0}'.format(self.raised_by.split("@")[0])
        if self.beratungskategorie:
            titel += ' {0}'.format(self.beratungskategorie)
        self.titel = titel
        
        if self.mv_mitgliedschaft:
            self.mitgliedname = " ".join((frappe.db.get_value("Mitgliedschaft", self.mv_mitgliedschaft, "vorname_1") or '', frappe.db.get_value("Mitgliedschaft", self.mv_mitgliedschaft, "nachname_1") or ''))
        
        # check for default_rueckfragen_email_template
        self.check_default_rueckfragen_email_template()
        
        # setzen von naechster_termin für Listenansicht
        self.set_naechster_termin()
        
        # synchron-haltung von kontaktperson in Beratung und in Beratungs-Termin
        self.synchron_kontaktperson()
        
        # Handling des Status
        self.status_handler()

        # Keine Beratung ohne Sektion
        if not self.sektion_id:
            self.set_sektion()
    
    def set_sektion(self):
        '''
        Diese Methode setzt bei Beratungen ohne Sektion die Standardsektion gem. User welcher die Beratung anlegen möchte.
        Besitzt der User keine Standardsektion, wird die Anlage unterbunden.

        Sollte der User "Administrator" sein, so wird die Anlage der Beratung ohne Sektion explizit erlaubt,
        weil ansonsten keine Beratungen via E-Mail-Eingang angelegt werden können.
        In diesem Fall wird die Sektion nachträglich (nach dem erstellen der zugehörigen Kommunikation) der Beratung hinzugefügt.
        Siehe Hook https://git.libracore.io/libracore/MVD/-/blob/master/mvd/hooks.py?ref_type=heads#L127
        '''
        if frappe.session.user != 'Administrator':
            default_sektion = frappe.db.sql("""SELECT `for_value` FROM `tabUser Permission` WHERE `allow` = 'Sektion' AND `user` = '{user}' AND `is_default` = 1""".format(user=frappe.session.user), as_dict=True)
            if len(default_sektion) > 0:
                self.sektion_id = default_sektion[0].for_value
            else:
                frappe.throw("Es wurde keine Standard Sektion für den User {user} gefunden.<br>Ohne Sektion kann keine Beratung angelegt werden.".format(user=frappe.session.user))
    
    def status_handler(self):
        # Prüfung ob Beratung gerade angelegt wird
        if frappe.db.exists("Beratung", self.name):
            # Beratung existiert und wurde verändert
            if len(self.termin) > 0 and self.status not in ('Closed', 'Nicht-Mitglied-Abgewiesen'):
                found_past_termin = False
                for termin in self.termin:
                    if getdate(termin.von) < getdate(now()):
                        found_past_termin = True
                
                if not found_past_termin:
                    # Manuelle Anlage via "Termin erstellen"
                    self.status = 'Termin vereinbart'
            else:
                if self.status not in ('Rückfragen', 'Rückfrage: Termin vereinbaren', 'Closed', 'Nicht-Mitglied-Abgewiesen'):
                    alter_status = frappe.db.get_value("Beratung", self.name, 'status')
                    if alter_status == 'Eingang':
                        if self.kontaktperson and self.mv_mitgliedschaft:
                            self.status = 'Open'
                        elif self.beratungskategorie and self.mv_mitgliedschaft:
                            self.status = 'Open'
                            # Zuweisung Defaultberater*in
                            self.zuweisung_default_berater_in()
                else:
                    if self.status not in ('Closed', 'Nicht-Mitglied-Abgewiesen'):
                        if self.status == 'Rückfragen' and self.kontaktperson:
                            bisherige_kontaktperson = frappe.db.get_value("Beratung", self.name, 'kontaktperson') or None
                            if not bisherige_kontaktperson:
                                self.status = 'Open'
                        elif self.status == 'Rückfragen' and self.ungelesen == 1 and not self.kontaktperson:
                            self.status = 'Open'
                            self.zuweisung_default_berater_in()
        else:
            # Beratung wird aktuell angelegt
            if self.anlage_durch_web_formular:
                # anlage via web formular
                '''
                Achtung MVBE-Hack
                '''
                if self.sektion_id == 'MVBE':
                    if self.status == 'Eingang':
                        if self.beratungskategorie not in ('202 - MZ-Erhöhung', '300 - Nebenkosten'):
                            self.status = 'Open'
                            # Zuweisung Defaultberater*in
                            self.zuweisung_default_berater_in()
                '''
                /MVBE-Hack
                '''
            else:
                if self.raised_by:
                    # Anlage via Mail
                    if self.mv_mitgliedschaft:
                        # Konnte einem Mitglied zugewiesen werden
                        self.status = 'Open'
                        # Zuweisung Defaultberater*in
                        self.zuweisung_default_berater_in()
                    else:
                        # Konnte nicht einem Mitglied zugewiesen werden
                        self.status = 'Eingang'
                    # flag für sync Mail attachements
                    self.anlage_durch_mail_check_attachments = 1
                else:
                    # Anlage manuell
                    self.status = 'Eingang'
                    if len(self.termin) > 0:
                        found_past_termin = False
                        for termin in self.termin:
                            if getdate(termin.von) < getdate(now()):
                                found_past_termin = True
                        
                        if not found_past_termin:
                            # Manuelle Anlage via "Termin erstellen"
                            self.status = 'Termin vereinbart'
    
    def zuweisung_default_berater_in(self):
        if self.sektion_id:
            default_emailberatung_todo_gruppe = frappe.db.get_value("Sektion", self.sektion_id, "default_emailberatung_todo_gruppe")
            if default_emailberatung_todo_gruppe:
                self.kontaktperson = default_emailberatung_todo_gruppe
                    
    def check_default_rueckfragen_email_template(self):
        if self.sektion_id:
            default_rueckfragen_email_template = frappe.db.get_value("Sektion", self.sektion_id, "default_rueckfragen_email_template")
            if self.default_rueckfragen_email_template != default_rueckfragen_email_template:
                self.default_rueckfragen_email_template = default_rueckfragen_email_template
    
    def set_naechster_termin(self):
        if len(self.termin) > 0:
            self.naechster_termin = frappe.utils.get_datetime(self.termin[len(self.termin) - 1].von).strftime('%d.%m.%Y %H:%M')
        else:
            self.naechster_termin = None
    
    def synchron_kontaktperson(self):
        if len(self.termin) > 0:
            if self.kontaktperson != self.termin[len(self.termin) - 1].berater_in:
                kontaktperson_alt = frappe.db.get_value("Beratung", self.name, 'kontaktperson')
                if kontaktperson_alt != self.kontaktperson:
                    self.termin[len(self.termin) - 1].berater_in = self.kontaktperson
                else:
                    self.kontaktperson = self.termin[len(self.termin) - 1].berater_in
    
    def split_beratung(self, split_type, communication_id):
        if split_type == '1:1 Kopie':
            from copy import deepcopy
            replicated_beratung = deepcopy(self)
        elif split_type == 'Neuanlage':
            replicated_beratung = {
                "doctype": "Beratung",
                "mv_mitgliedschaft": self.mv_mitgliedschaft,
                "sektion_id": self.sektion_id,
                "start_date": today()
            }
        else:
            frappe.throw("Fehlender split_type")

        replicated_beratung = frappe.get_doc(replicated_beratung).insert()

        # Replicate linked Communications
        comm_to_split_from = frappe.get_doc("Communication", communication_id)
        communications = frappe.get_all("Communication",
            filters={"reference_doctype": "Beratung",
                "reference_name": comm_to_split_from.reference_name,
                "creation": ('>=', comm_to_split_from.creation)})

        for communication in communications:
            doc = frappe.get_doc("Communication", communication.name)
            doc.reference_name = replicated_beratung.name
            doc.save(ignore_permissions=True)

        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "Beratung",
            "reference_name": replicated_beratung.name,
            "content": " - Beratung gesplittet von <a href='#Form/Beratung/{0}'>{1}</a>".format(self.name, frappe.bold(self.name)),
        }).insert(ignore_permissions=True)
        
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "Beratung",
            "reference_name": self.name,
            "content": " - Beratung wurde in neue Beratung <a href='#Form/Beratung/{0}'>{1}</a> gesplittet".format(replicated_beratung.name, frappe.bold(replicated_beratung.name)),
        }).insert(ignore_permissions=True)

        return replicated_beratung.name
    
    def replace_table_as_p(self):
        soup = BeautifulSoup(self.notiz, 'lxml')
        tables = soup.find_all("table")

        for table in tables:
            tds = table.find_all("td")
            div_tag = soup.new_tag("div")

            for td in tds:
                p_tag = soup.new_tag("p")
                p_tag.string = td.get_text()
                div_tag.append(p_tag)
                div_tag.append(soup.new_tag("br"))
            
            table.replace_with(div_tag)
        
        self.notiz = soup.prettify()
        self.save()
        
        return

@frappe.whitelist()
def verknuepfen(beratung, verknuepfung):
    multiselect_1 = frappe.get_doc({
        'doctype': 'Beratung Multiselect',
        'parentfield': 'verknuepfungen',
        'parenttype': 'Beratung',
        'parent': beratung,
        'beratung': verknuepfung
    }).insert()
    
    multiselect_2 = frappe.get_doc({
        'doctype': 'Beratung Multiselect',
        'parentfield': 'verknuepfungen',
        'parenttype': 'Beratung',
        'parent': verknuepfung,
        'beratung': beratung
    }).insert()

@frappe.whitelist()
def verknuepfung_entfernen(beratung, verknuepfung):
    multiselects_1 = frappe.db.sql("""SELECT
                                        `name`
                                    FROM `tabBeratung Multiselect`
                                    WHERE `parentfield` = 'verknuepfungen'
                                    AND `parenttype` = 'Beratung'
                                    AND `parent` = '{beratung}'
                                    AND `beratung` = '{verknuepfung}'""".format(beratung=beratung, verknuepfung=verknuepfung), as_dict=True)
    for multiselect in multiselects_1:
        m = frappe.get_doc("Beratung Multiselect", multiselect.name)
        m.delete()
    
    multiselects_2 = frappe.db.sql("""SELECT
                                        `name`
                                    FROM `tabBeratung Multiselect`
                                    WHERE `parentfield` = 'verknuepfungen'
                                    AND `parenttype` = 'Beratung'
                                    AND `parent` = '{verknuepfung}'
                                    AND `beratung` = '{beratung}'""".format(beratung=beratung, verknuepfung=verknuepfung), as_dict=True)
    for multiselect in multiselects_2:
        m = frappe.get_doc("Beratung Multiselect", multiselect.name)
        m.delete()

@frappe.whitelist()
def get_verknuepfungsuebersicht(beratung):
    verknuepfungen_zu = frappe.db.sql("""SELECT
                                            *
                                        FROM `tabBeratung`
                                        WHERE `name` IN (
                                            SELECT `beratung`
                                            FROM `tabBeratung Multiselect`
                                            WHERE `parent` = '{beratung}'
                                        )""".format(beratung=beratung), as_dict=True)
    verknuepfungen_von = frappe.db.sql("""SELECT
                                            *
                                        FROM `tabBeratung`
                                        WHERE `name` IN (
                                            SELECT `parent`
                                            FROM `tabBeratung Multiselect`
                                            WHERE `beratung` = '{beratung}'
                                        )
                                        AND `name` NOT IN (
                                            SELECT `beratung`
                                            FROM `tabBeratung Multiselect`
                                            WHERE `parent` = '{beratung}'
                                        )""".format(beratung=beratung), as_dict=True)
    if len(verknuepfungen_zu) > 0 or len(verknuepfungen_von) > 0:
        table = """<table style="width: 100%;">
                        <thead>
                            <tr>
                                <th>Datum</th>
                                <th>Priorität</th>
                                <th>Status</th>
                                <th>Kontaktperson</th>
                                <th>Beratungskategorie</th>
                                <th>Verkn. öffnen</th>
                                <th>Verkn. aufheben</th>
                            </tr>
                        </thead>
                        <tbody>"""
        
        for verknuepfung in verknuepfungen_zu:
            table += """<tr>
                            <td>{0}</td>
                            <td>{1}</td>
                            <td>{2}</td>
                            <td>{3}</td>
                            <td>{4}</td>
                            <td style="text-align: center;"><i class="fa fa-external-link verknuepfung_jump" data-jump="{5}" style="cursor: pointer;"></i></td>
                            <td style="text-align: center;"><i class="fa fa-trash verknuepfung_trash" data-remove="{5}" style="cursor: pointer;"></i></td>
                        </tr>""".format(frappe.utils.get_datetime(verknuepfung.start_date).strftime('%d.%m.%Y'), \
                                        verknuepfung.beratung_prio or '-', verknuepfung.status, verknuepfung.kontaktperson or '-', verknuepfung.beratungskategorie or '-', verknuepfung.name)
        for verknuepfung in verknuepfungen_von:
            table += """<tr>
                            <td>{0}</td>
                            <td>{1}</td>
                            <td>{2}</td>
                            <td>{3}</td>
                            <td>{4}</td>
                            <td style="text-align: center;"><i class="fa fa-external-link verknuepfung_jump" data-jump="{5}" style="cursor: pointer;"></i></td>
                            <td style="text-align: center;"><i class="fa fa-trash verknuepfung_trash" data-remove="{5}" style="cursor: pointer;"></i></td>
                        </tr>""".format(frappe.utils.get_datetime(verknuepfung.start_date).strftime('%d.%m.%Y'), \
                                        verknuepfung.beratung_prio or '-', verknuepfung.status, verknuepfung.kontaktperson or '-', verknuepfung.beratungskategorie or '-', verknuepfung.name)
        
        table += """</tbody>
                    </table>"""
    else:
        table = """<p>Keine Verknüpfungen vorhanden</p>"""
    
    slaves = frappe.db.sql("""SELECT `name` FROM `tabBeratung` WHERE `master` = '{beratung}'""".format(beratung=beratung), as_dict=True)
    if len(slaves) > 0:
        table += """<table style="width: 100%;">
                        <thead>
                            <tr>
                                <th>Zusammengeführt mit</th>
                                <th>Verkn. öffnen</th>
                            </tr>
                        </thead>
                        <tbody>"""
        for slave in slaves:
            table += """
                        <tr>
                            <td>{beratung}</td>
                            <td style="text-align: center;"><i class="fa fa-external-link verknuepfung_jump" data-jump="{beratung}" style="cursor: pointer;"></i></td>
                        </tr>""".format(beratung=slave.name)
        table += """</tbody>
                    </table>"""
    
    if frappe.db.get_value("Beratung", beratung, 'mv_mitgliedschaft'):
        anzahl_beratungen_zu_mitglied = frappe.db.count('Beratung', {'mv_mitgliedschaft': frappe.db.get_value("Beratung", beratung, 'mv_mitgliedschaft')}) or 0
        table += """<br><p id="route_to_list_view" style="cursor: pointer;"><b>Anzahl Beratungen dieser Mitgliedschaft: {0}</b></p>""".format(anzahl_beratungen_zu_mitglied)
    
    return table

@frappe.whitelist()
def new_todo(beratung, kontaktperson):
    kp = frappe.get_doc("Termin Kontaktperson", kontaktperson)
    for user in kp.user:
        frappe.get_doc({
            'doctype': 'ToDo',
            'description': 'Zuweisung für Beratung {0}'.format(beratung),
            'reference_type': 'Beratung',
            'reference_name': beratung,
            'assigned_by': frappe.session.user or 'Administrator',
            'owner': user.user
        }).insert(ignore_permissions=True)
    frappe.db.set_value("Beratung", beratung, 'create_todo', 0, update_modified=False)
    frappe.db.commit()

# SP API Endpunkt: Abfrage Dokumente
def _get_beratungs_dokument(beratungs_dokument):
    if 'beratungs_dokument_id' in beratungs_dokument:
        if frappe.db.exists("File", beratungs_dokument["beratungs_dokument_id"]):
            # File zurück senden
            file_doc = frappe.get_doc("File", beratungs_dokument["beratungs_dokument_id"])
            filecontent = file_doc.get_content()
            file_name = frappe.db.get_value("File", beratungs_dokument["beratungs_dokument_id"], 'file_name')
            return {
                'filecontent': filecontent,
                'type': str(file_name.split(".")[len(file_name.split(".")) - 1]),
                'name': file_name
            }
            
        else:
            return raise_xxx(400, 'Bad Request', 'file not found')
    else:
        return raise_xxx(400, 'Bad Request', 'beratungs_dokument missing')

# Status Returns
def raise_xxx(code, title, message):
    frappe.log_error("{0}\n{1}\n{2}\n\n{3}".format(code, title, message, frappe.utils.get_traceback()), 'SP API Error!')
    frappe.local.response.http_status_code = code
    frappe.local.response.message = message
    return ['{code} {title}'.format(code=code, title=title), {
        "error": {
            "code": code,
            "message": "{message}".format(message=message)
        }
    }]

def check_communication(self, event):
    from frappe.utils.data import get_datetime, add_to_date
    communication = self
    if communication.sent_or_received == 'Received':
        if communication.reference_doctype == 'Beratung':
            beratung = frappe.get_doc("Beratung", communication.reference_name)
            if frappe.db.count("Communication", {'reference_doctype': 'Beratung', 'reference_name': communication.reference_name}) < 2:
                time_stamp_communication = add_to_date(get_datetime(communication.creation), minutes=-1, as_datetime=True)
                time_stamp_beratung = get_datetime(beratung.creation)
                if time_stamp_communication < time_stamp_beratung:
                    if not beratung.notiz:
                        beratung.notiz = communication.content
                    if not beratung.sektion_id:
                        beratung.sektion_id = frappe.db.get_value("Email Account", communication.email_account, 'sektion_id')
                    if not beratung.raised_by_name:
                        beratung.raised_by_name = communication.sender_full_name
                    if not beratung.raised_by:
                        beratung.raised_by = communication.sender
                    beratung.save()
                else:
                    beratung.ungelesen = 1
                    beratung.save()
            else:
                beratung.ungelesen = 1
                beratung.save()

@frappe.whitelist()
def uebernahme(beratung, user):
    kontaktpersonen = frappe.db.sql("""
                                        SELECT
                                            `parent`
                                        FROM `tabTermin Kontaktperson Multi User`
                                        WHERE `parent` IN (
                                            SELECT
                                                `parent`
                                            FROM `tabTermin Kontaktperson Multi User`
                                            WHERE `user` = '{user}'
                                            AND `idx` = 1
                                        )
                                        AND `parent` NOT IN (
                                            SELECT
                                                `parent`
                                            FROM `tabTermin Kontaktperson Multi User`
                                            WHERE `user` != '{user}'
                                        )
                                    """.format(user=user), as_dict=True)
    if len(kontaktpersonen) > 0:
        return kontaktpersonen[0].parent
    else:
        return False

@frappe.whitelist()
def merge(slave, master):
    slave_doc = frappe.get_doc("Beratung", slave)
    master_doc = frappe.get_doc("Beratung", master)
    
    if master_doc.notiz:
        master_doc.notiz += "<br><h3>Anfrage aus der zusammengeführten Beratung</h3><br>" + str(slave_doc.notiz)
    else:
        master_doc.notiz = "<h3>Anfrage aus der zusammengeführten Beratung</h3><br>" + str(slave_doc.notiz)
    
    if master_doc.antwort:
        master_doc.antwort += "<br><h3>Antwort aus der zusammengeführten Beratung</h3><br>" + str(slave_doc.antwort)
    else:
        master_doc.antwort = "<br><h3>Antwort aus der zusammengeführten Beratung</h3><br>" + str(slave_doc.antwort)
    
    master_doc.save()
    
    frappe.db.set_value("Beratung", slave_doc.name, "master", master_doc.name)
    frappe.db.set_value("Beratung", slave_doc.name, "status", 'Zusammengeführt')
    
    # relink files
    beratungs_files = frappe.db.sql("""SELECT `name` FROM `tabFile` WHERE `attached_to_name` = '{0}'""".format(slave_doc.name), as_dict=True)
    if len(beratungs_files) > 0:
        for beratung_file in beratungs_files:
            frappe.db.set_value("File", beratung_file.name, "attached_to_name", master_doc.name)
    
    # Info in Audit-Trail
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Beratung",
        "reference_name": master,
        "content": " - Die Beratung <a href='#Form/Beratung/{0}'>{1}</a> wurde mit dieser zusammengeführt".format(slave, frappe.bold(slave)),
    }).insert(ignore_permissions=True)
    
    master_doc.save()
    
    return

@frappe.whitelist()
def set_protection(beratung):
    if frappe.db.exists("Beratung", beratung):
        if not frappe.db.get_value("Beratung", beratung, 'gesperrt_am'):
            now_date_time = now().split(".")[0]
            frappe.db.set_value("Beratung", beratung, 'gesperrt_von', frappe.session.user, update_modified=False)
            frappe.db.set_value("Beratung", beratung, 'gesperrt_am', now_date_time, update_modified=False)
            frappe.db.commit()

@frappe.whitelist()
def clear_protection(beratung, force=False):
    if frappe.db.get_value("Beratung", beratung, 'gesperrt_von') == frappe.session.user or force:
        frappe.db.set_value("Beratung", beratung, 'gesperrt_von', None, update_modified=False)
        frappe.db.set_value("Beratung", beratung, 'gesperrt_am', None, update_modified=False)
        frappe.db.commit()
    
    if force:
        frappe.get_doc("Beratung", beratung).add_comment('Submitted', 'Hat manuell die aktive Beratungssperre aufgehoben')
        return

@frappe.whitelist()
def get_beratungsorte(sektion, kontakt=None):
    if not kontakt:
        orte = frappe.db.sql("""SELECT `name` AS `ort_def` FROM `tabBeratungsort` WHERE `sektion_id` = '{sektion}' ORDER BY `ort` ASC""".format(sektion=sektion), as_dict=True)
    else:
        orte = frappe.db.sql("""SELECT DISTINCT `ort` AS `ort_def` FROM `tabArbeitsplan Standardzeit` WHERE `parent` = '{kontakt}' ORDER BY `ort` ASC""".format(kontakt=kontakt), as_dict=True)
    
    ort_list = []
    for ort in orte:
        ort_list.append(ort.ort_def)
    ort_string = "\n".join(ort_list)
    return {
        'ort_string': ort_string,
        'default': orte[0].ort_def if len(orte) > 0 else '',
        'default_termindauer': frappe.db.get_value("Sektion", sektion, 'default_termindauer') or 45
    }

@frappe.whitelist()
def anz_beratungen_ohne_termine(mv_mitgliedschaft):
    return int(frappe.db.count('Beratung', {'mv_mitgliedschaft': mv_mitgliedschaft, 'hat_termine': 0}))

# die nachfolgende Methode erstellt ggf. eine Beratung und n zugehörige Termin(e) aus einer Mitgliedschaft heraus
@frappe.whitelist()
def create_neue_beratung(mitgliedschaft, termin_block_data, art, ort, berater_in, telefonnummer, notiz, beratung=None):
    termin_block_data = json.loads(termin_block_data)
    if not beratung:
        # erstelle neue Beratung
        beratung = frappe.get_doc({
            "doctype": "Beratung",
            "sektion_id": frappe.db.get_value("Mitgliedschaft", mitgliedschaft, 'sektion_id'),
            "mv_mitgliedschaft": mitgliedschaft,
            "kontaktperson": berater_in,
            "notiz": "Terminnotiz:<br>{0}".format(notiz)
        })
        beratung.insert()
        for termin in termin_block_data:
            row = beratung.append('termin', {})
            row.von = "{0} {1}".format(termin['date'], termin['von'])
            row.bis = "{0} {1}".format(termin['date'], termin['bis'])
            row.art = art
            row.ort = ort
            row.berater_in = berater_in
            row.telefonnummer = telefonnummer
            row.abp_referenz = termin['referenz']
            row.notiz = notiz
        beratung.save()
    else:
        # füge Termin zu bestehenden Beratung hinzu
        beratung = frappe.get_doc("Beratung", beratung)
        for termin in termin_block_data:
            row = beratung.append('termin', {})
            row.von = "{0} {1}".format(termin['date'], termin['von'])
            row.bis = "{0} {1}".format(termin['date'], termin['bis'])
            row.art = art
            row.ort = ort
            row.berater_in = berater_in
            row.telefonnummer = telefonnummer
            row.abp_referenz = termin['referenz']
            row.notiz = notiz
        beratung.save()
    
    return beratung.name

@frappe.whitelist()
def remove_comments(comments):
    comments = json.loads(comments)
    for comment in comments:
        frappe.db.sql("""DELETE FROM `tabComment` WHERE `name` = '{c_name}'""".format(c_name=comment), as_list=True)
    return True

def sync_mail_attachements(file_record, event):
    if file_record.attached_to_doctype == 'Communication':
        communication = file_record.attached_to_name
        if frappe.db.get_value("Communication", communication, 'sent_or_received') == 'Received':
            if frappe.db.get_value("Communication", communication, 'reference_doctype') == 'Beratung':
                beratung = frappe.db.get_value("Communication", communication, 'reference_name')
                # check for -zip and delete if neccessary
                no_zip = True
                if ".zip" in file_record.file_url:
                    no_zip = False
                    frappe.get_doc("Beratung", beratung).add_comment('Comment', 'Der Anhang {0} musste aus sicherheitstechnischen Gründen entfernt werden.'.format(file_record.file_name))
                    file_record.delete()
                
                if no_zip:
                    # copy file and link to beratung
                    from copy import deepcopy
                    new_file = deepcopy(file_record)
                    new_file.name = None
                    new_file.content = None
                    new_file.attached_to_doctype = 'Beratung'
                    new_file.attached_to_name = beratung
                    new_file.insert(ignore_permissions=True)
    elif file_record.attached_to_doctype == 'Beratung':
        if file_record.folder == "Home/Attachments":
            # siehe auch sync_attachments_and_beratungs_table
            vorhanden = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratungsdateien` WHERE `file` = '{fileurl}' AND `parent` = '{beratung}'""".format(\
                fileurl=file_record.file_url, \
                beratung=file_record.attached_to_name), as_dict=True)[0].qty
            if vorhanden < 1:
                b = frappe.get_doc("Beratung", file_record.attached_to_name)
                row = b.append('dokumente', {})
                row.file = file_record.file_url
                row.document_type = 'Sonstiges'
                row.filename = file_record.file_name
                b.save()

def sync_attachments_and_beratungs_table(doc, event):
    if doc.doctype == "Beratung":
        old_doc = doc._doc_before_save or False
        if old_doc:
            try:
                if old_doc.dokumente and doc.dokumente:
                    if len(old_doc.dokumente) < len(doc.dokumente):
                        # es wurde ein File zur Dokumenten Table hinzugefügt.
                        # hier muss nicht eingegriffen werden, da das File autom. als Attachment gespeichert wird.
                        pass
                    if len(old_doc.dokumente) > len(doc.dokumente):
                        # es wurde ein File aus der Dokumente-Table entfernt, der Filedatensatz muss nun noch gelöscht werden.
                        alte_dok_list = [json.dumps({'file': alt.file, 'name': alt.name}) for alt in old_doc.dokumente]
                        neue_dok_list = [json.dumps({'file': neu.file, 'name': neu.name}) for neu in doc.dokumente]
                        diff = list(set(alte_dok_list).difference(set(neue_dok_list)))
                        for entry_to_delete in diff:
                            file_to_delete = json.loads(entry_to_delete)['file']
                            _f = frappe.db.sql("""SELECT `name` FROM `tabFile` WHERE `file_url` = '{file_to_delete}' AND `attached_to_doctype` = 'Beratung' AND `attached_to_name` = '{docname}'""".format(\
                                file_to_delete=file_to_delete, \
                                docname=doc.name), as_dict=True)
                            if len(_f) > 0:
                                f = frappe.get_doc("File", _f[0].name)
                                f.delete()
                elif old_doc.dokumente:
                    for file_to_delete in old_doc.dokumente:
                        _f = frappe.db.sql("""SELECT `name` FROM `tabFile` WHERE `file_url` = '{file_to_delete}' AND `attached_to_doctype` = 'Beratung' AND `attached_to_name` = '{docname}'""".format(\
                            file_to_delete=file_to_delete.file, \
                            docname=doc.name), as_dict=True)
                        if len(_f) > 0:
                            f = frappe.get_doc("File", _f[0].name)
                            f.delete()
                elif doc.dokumente:
                    # es wurde ein File zur Dokumenten Table hinzugefügt.
                    # hier muss nicht eingegriffen werden, da das File autom. als Attachment gespeichert wird.
                    pass
            except Exception as err:
                frappe.log_error("Error:\n{0}\n\nDocument:\n{1}".format(err, str(doc.as_dict())), "sync_attachments_and_beratungs_table")
                pass
        
        # Abgleich anz Files als Attachment und anz. File in Tabelle.
        # Hat es mehr Files als Attachments, so wird das Delta zur Tabelle hinzugefügt.
        file_attachments = frappe.db.sql("""SELECT * FROM `tabFile` WHERE `attached_to_doctype` = 'Beratung' AND `attached_to_name` = '{docname}'""".format(\
                            docname=doc.name), as_dict=True)
        if len(file_attachments) > 0:
            start_sync = False
            if not doc.dokumente:
                start_sync = True
            elif len(file_attachments) != len(doc.dokumente):
                start_sync = True
            if start_sync:
                new_row_added = False
                for file_attachment in file_attachments:
                    file_found = False
                    for present_file in doc.dokumente:
                        if present_file.file == file_attachment.file_url:
                            file_found = True
                    if not file_found:
                        row = doc.append('dokumente', {})
                        row.file = file_attachment.file_url
                        row.document_type = 'Sonstiges'
                        row.filename = file_attachment.file_name
                        new_row_added = True
                if new_row_added:
                    doc.save()
    
    if doc.doctype == 'File':
        # Diese Funktion synchronisiert nur das entfernen, für die Anlage siehe sync_mail_attachements
        if doc.attached_to_doctype == 'Beratung':
            vorhanden = frappe.db.sql("""SELECT `name` FROM `tabBeratungsdateien` WHERE `file` = '{fileurl}' AND `parent` = '{beratung}'""".format(fileurl=doc.file_url, \
                beratung=doc.attached_to_name), as_dict=True)
            if len(vorhanden) > 0:
                files_to_delete = [v.name for v in vorhanden]
                b = frappe.get_doc("Beratung", doc.attached_to_name)
                for row in b.dokumente:
                    if row.name in files_to_delete:
                        b.remove(row)
                b.save()

@frappe.whitelist()
def erstelle_todo(owner, beratung, description=False, datum=False, notify=0, mitgliedschaft=None):
    description_string = description or ''
    if mitgliedschaft:
        description_string += '<br><br><a href="/desk#Form/Mitgliedschaft/{0}">Link zur Mitgliedschaft</a>'.format(mitgliedschaft)
    todo = frappe.get_doc({
        "doctype":"ToDo",
        "owner": owner,
        "reference_type": "Beratung",
        "reference_name": beratung,
        "description": description_string,
        "priority": "Medium",
        "status": "Open",
        "date": datum or '',
        "assigned_by": frappe.session.user
    }).insert(ignore_permissions=True)
    
    # notify
    if cint(notify) == 1:
        from frappe.desk.form.assign_to import notify_assignment
        notify_assignment(todo.assigned_by, todo.owner, todo.reference_type, todo.reference_name, action='ASSIGN',\
                 description=todo.description, notify=notify)
    return

@frappe.whitelist()
def get_termin_mail_txt(von, bis, art, ort, telefonnummer, mitgliedschaft):
    index = 0
    von = json.loads(von)
    bis = json.loads(bis)
    anrede = ''
    sektion = ''
    if mitgliedschaft:
        anrede = frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "briefanrede")
        sektion = frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "sektion_id")
        sprache = frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "language")
    mail_txt = '<p>{0}</p>'.format(anrede)
    subject = 'Termin '
    
    for entry in von:
        von_datum = getdate(entry)
        ort_info = frappe.db.get_value("Beratungsort", ort, "infofeld") or ''
        if sprache == 'fr':
            if art == 'telefonisch':
                subject += '(telefonische) Beratung am {wochentag}., {datum} um {von} (in {ort})'.format(wochentag=_(von_datum.strftime('%A'))[:2], \
                                                                                                        datum=von_datum.strftime('%d.%m.%y'), \
                                                                                                        von=":".join(von[index].split(" ")[1].split(":")[:2]), \
                                                                                                        ort=ort.replace("({0})".format(sektion), ""))
                mail_txt += """
                    <div>
                        Nous avons réservé pour vous le rendez-vous téléphonique suivant:<br>
                        {wochentag}, {datum} à {von}<br>
                        Notre conseiller/notre conseillère Monsieur/Madame vous appellera au numéro suivant:<br>
                        {telefonnummer}<br><br>
                        Veuillez noter que nos consultants* juridiques ne consultent pas les documents avant le rendez-vous.<br><br>
                        En cas d'empêchement, nous vous prions d'annoncer votre absence le plus rapidement possible.<br><br>
                        Avec nos meilleures salutations
                    </div>
                """.format(wochentag=_(von_datum.strftime('%A'), sprache), datum=von_datum.strftime('%d.%m.%y'), \
                        von=":".join(von[index].split(" ")[1].split(":")[:2]), \
                        telefonnummer=telefonnummer)
            else:
                subject += 'Beratung am {wochentag}., {datum} um {von} (in {ort})'.format(wochentag=_(von_datum.strftime('%A'))[:2], \
                                                                                                        datum=von_datum.strftime('%d.%m.%y'), \
                                                                                                        von=":".join(von[index].split(" ")[1].split(":")[:2]), \
                                                                                                        ort=ort.replace("({0})".format(sektion), ""))
                mail_txt += """
                    <div>
                        Nous avons réservé pour vous le rendez-vous suivant:<br>
                        {wochentag}, {datum} à {von}<br>
                        Notre consultant* Müller Klaus vous attend à<br>
                        {ort}, {ort_info}.<br><br>
                        Veuillez noter que nos consultants* juridiques ne consultent pas les documents avant le rendez-vous.<br><br>
                        En cas d'empêchement, nous vous prions d'annoncer votre absence le plus rapidement possible.<br><br>
                        Avec nos meilleures salutations
                    </div>
                """.format(wochentag=_(von_datum.strftime('%A'), sprache), datum=von_datum.strftime('%d.%m.%y'), \
                        von=":".join(von[index].split(" ")[1].split(":")[:2]), \
                        ort_info="<br>{0}".format(ort_info) if ort_info else '', ort=ort.replace("({0})".format(sektion), ""))
        else:
            if art == 'telefonisch':
                subject += '(telefonische) Beratung am {wochentag}., {datum} um {von} (in {ort})'.format(wochentag=_(von_datum.strftime('%A'))[:2], \
                                                                                                        datum=von_datum.strftime('%d.%m.%y'), \
                                                                                                        von=":".join(von[index].split(" ")[1].split(":")[:2]), \
                                                                                                        ort=ort.replace("({0})".format(sektion), ""))
                mail_txt += """
                    <div>
                        Wir haben für Sie folgenden Termin reserviert:<br>
                        Telefonische Beratung<br>
                        {wochentag}, {datum} um {von}<br>
                        Unsere Berater*in Müller Klaus wird Sie unter dieser Nummer anrufen:<br>
                        {telefonnummer}<br><br>
                        Bitte beachten Sie, dass unsere Rechtsberater*innen die Unterlagen vor dem Beratungstermin nicht sichten. Sie werden bei Bedarf während des Beratungstermin konsultiert.<br><br>
                        Wir bitten Sie im Verhinderungsfall so rasch wie möglich abzumelden.<br><br>
                        Mit freundlichen Grüssen
                    </div>
                """.format(wochentag=_(von_datum.strftime('%A'), sprache), datum=von_datum.strftime('%d.%m.%y'), \
                        von=":".join(von[index].split(" ")[1].split(":")[:2]), \
                        telefonnummer=telefonnummer)
            else:
                subject += 'Beratung am {wochentag}., {datum} um {von} (in {ort})'.format(wochentag=_(von_datum.strftime('%A'))[:2], \
                                                                                                        datum=von_datum.strftime('%d.%m.%y'), \
                                                                                                        von=":".join(von[index].split(" ")[1].split(":")[:2]), \
                                                                                                        ort=ort.replace("({0})".format(sektion), ""))
                mail_txt += """
                    <div>
                        Wir haben für Sie folgenden Termin reserviert:<br>
                        Persönliche Beratung<br>
                        {wochentag}, {datum} um {von}<br>
                        Unsere Berater*in Müller Klaus erwartet Sie in:<br>
                        {ort}, {ort_info}.<br><br>
                        Bitte beachten Sie, dass unsere Rechtsberater*innen die Unterlagen vor dem Beratungstermin nicht sichten. Sie werden bei Bedarf während des Beratungstermin konsultiert.<br><br>
                        Wir bitten Sie im Verhinderungsfall so rasch wie möglich abzumelden.<br><br>
                        Mit freundlichen Grüssen
                    </div>
                """.format(wochentag=_(von_datum.strftime('%A'), sprache), datum=von_datum.strftime('%d.%m.%y'), \
                        von=":".join(von[index].split(" ")[1].split(":")[:2]), \
                        ort_info="<br>{0}".format(ort_info) if ort_info else '', ort=ort.replace("({0})".format(sektion), ""))
        index += 1

    return {
        'mail_txt': mail_txt,
        'subject': subject
    }

@frappe.whitelist()
def get_termin_block_data(abp_zuweisungen):
    if abp_zuweisungen.startswith("-"):
        abp_zuweisungen = abp_zuweisungen.replace("-", "", 1)
    return_data = []
    for abp_zuweisung in abp_zuweisungen.split("-"):
        return_data.append({
            'referenz': abp_zuweisung,
            'von': frappe.db.get_value("APB Zuweisung", abp_zuweisung, 'from_time'),
            'bis': frappe.db.get_value("APB Zuweisung", abp_zuweisung, 'to_time'),
            'date': frappe.db.get_value("APB Zuweisung", abp_zuweisung, 'date')
        })
    return return_data

@frappe.whitelist()
def get_tel_for_termin(mitgliedschaft=None):
    if not mitgliedschaft:
        return ''
    
    tel = frappe.db.get_value("Mitgliedschaft", mitgliedschaft, 'tel_m_1')
    if tel:
        return tel
    tel = frappe.db.get_value("Mitgliedschaft", mitgliedschaft, 'tel_p_1')
    if tel:
        return tel
    tel = frappe.db.get_value("Mitgliedschaft", mitgliedschaft, 'tel_g_1')
    if tel:
        return tel
    
    return ''
# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import today, now

class Beratung(Document):
    def onload(self):
        # Sperren der Beratung beim öffnen
        if frappe.db.exists("Beratung", self.name):
            if not frappe.db.get_value("Beratung", self.name, 'gesperrt_am'):
                self.gesperrt_von = frappe.session.user
                now_date_time = now().split(".")[0]
                self.gesperrt_am = now_date_time
                frappe.db.set_value("Beratung", self.name, 'gesperrt_von', frappe.session.user, update_modified=False)
                frappe.db.set_value("Beratung", self.name, 'gesperrt_am', now_date_time, update_modified=False)
                frappe.db.commit()
            else:
                self.gesperrt_von = frappe.db.get_value("Beratung", self.name, 'gesperrt_von')
                self.gesperrt_am = frappe.db.get_value("Beratung", self.name, 'gesperrt_am')
    
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
                self.status = 'Termin vergeben'
                todos_to_remove = frappe.db.sql("""
                                                    SELECT
                                                        `name`
                                                    FROM `tabToDo`
                                                    WHERE `status` = 'Open'
                                                    AND `owner` = 'libracore@be.mieterverband.ch'
                                                    AND `reference_type` = 'Beratung'
                                                    AND `reference_name` = '{0}'""".format(self.name), as_dict=True)
                for todo in todos_to_remove:
                    t = frappe.get_doc("ToDo", todo.name)
                    t.status = 'Cancelled'
                    t.save(ignore_permissions=True)
                self.create_todo = 1
                # setze todo-log
                self.auto_todo_log = self.kontaktperson
            else:
                self.create_todo = 0
                self.auto_todo_log = None
                self.kontaktperson = None
                todos_to_remove = frappe.db.sql("""
                                                    SELECT
                                                        `name`
                                                    FROM `tabToDo`
                                                    WHERE `status` = 'Open'
                                                    AND `reference_type` = 'Beratung'
                                                    AND `reference_name` = '{0}'""".format(self.name), as_dict=True)
                for todo in todos_to_remove:
                    t = frappe.get_doc("ToDo", todo.name)
                    t.status = 'Cancelled'
                    t.save(ignore_permissions=True)
                frappe.get_doc({
                    'doctype': 'ToDo',
                    'description': 'Termin vergeben.<br>Zuweisung für Beratung {0}'.format(self.name),
                    'reference_type': 'Beratung',
                    'reference_name': self.name,
                    'assigned_by': frappe.session.user or 'Administrator',
                    'owner': 'libracore@be.mieterverband.ch'
                }).insert(ignore_permissions=True)
        else:
            # Auto ToDo handling
            if self.kontaktperson:
                if not frappe.db.get_value("Beratung", self.name, "kontaktperson"):
                    # vor dem speichern war noch kein Kontakt vorhanden, erstelle Gruppen-Todo
                    self.create_todo = 1
                    
                    # setze todo-log
                    self.auto_todo_log = self.kontaktperson
                else:
                    # vor dem speichern war bereits ein Kontakt vorhanden
                    if self.kontaktperson != frappe.db.get_value("Beratung", self.name, "kontaktperson"):
                        # der Kontakt hat geändert -> entferne alte ToDos & erstelle neue ToDos
                        # entferne alte ToDos
                        kontaktperson = frappe.get_doc("Termin Kontaktperson", self.auto_todo_log)
                        for user in kontaktperson.user:
                            todos_to_remove = frappe.db.sql("""
                                                                SELECT
                                                                    `name`
                                                                FROM `tabToDo`
                                                                WHERE `status` = 'Open'
                                                                AND `owner` = '{0}'
                                                                AND `reference_type` = 'Beratung'
                                                                AND `reference_name` = '{1}'""".format(user.user, self.name), as_dict=True)
                            for todo in todos_to_remove:
                                t = frappe.get_doc("ToDo", todo.name)
                                t.status = 'Cancelled'
                                t.save(ignore_permissions=True)
                        
                        # trigger neue ToDos
                        self.create_todo = 1
                        
                        # setze todo-log
                        self.auto_todo_log = self.kontaktperson
                        
            else:
                if frappe.db.get_value("Beratung", self.name, "kontaktperson"):
                    # vor dem entfernen war ein Kontakt hinterlegt -> entferne alte ToDos und resete ToDo-Log
                    # entferne alte ToDos
                    kontaktperson = frappe.get_doc("Termin Kontaktperson", self.auto_todo_log)
                    for user in kontaktperson.user:
                        todos_to_remove = frappe.db.sql("""
                                                            SELECT
                                                                `name`
                                                            FROM `tabToDo`
                                                            WHERE `status` = 'Open'
                                                            AND `owner` = '{0}'
                                                            AND `reference_type` = 'Beratung'
                                                            AND `reference_name` = '{1}'""".format(user.user, self.name), as_dict=True)
                        for todo in todos_to_remove:
                            t = frappe.get_doc("ToDo", todo.name)
                            t.status = 'Cancelled'
                            t.save(ignore_permissions=True)
                    
                    # reset ToDo-Log
                    self.auto_todo_log = None
        
        if self.kontaktperson and len(self.termin) > 0:
            if self.status in ('Eingang', 'Open'):
                self.status = 'Termin vergeben'
        
        # Statistik handling -> closed date tracker
        if self.status == 'Closed':
            if not self.geschlossen_am:
                self.geschlossen_am = today()
                todos_to_remove = frappe.db.sql("""
                                                SELECT
                                                    `name`
                                                FROM `tabToDo`
                                                WHERE `status` = 'Open'
                                                AND `reference_type` = 'Beratung'
                                                AND `reference_name` = '{0}'""".format(self.name), as_dict=True)
                for todo in todos_to_remove:
                    t = frappe.get_doc("ToDo", todo.name)
                    t.status = 'Cancelled'
                    t.save(ignore_permissions=True)
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
                                                    WHERE `e_mail_1` = '{email}'
                                                    OR `e_mail_2` = '{email}'
                                                    AND `status_c` = 'Regulär'""".format(email=self.raised_by), as_dict=True)
                
                if len(mitgliedschaften) == 1:
                    if self.sektion_id:
                        if self.sektion_id == mitgliedschaften[0].sektion_id:
                            self.mv_mitgliedschaft = mitgliedschaften[0].name
                            
                            # auto ToDo assign an ToDo Gruppe wenn Default hinterlegt
                            if self.beratungskategorie not in ('202 - MZ-Erhöhung', '300 - Nebenkosten'):
                                self.kontaktperson = frappe.db.get_value("Sektion", self.sektion_id, "default_emailberatung_todo_gruppe")
                                self.auto_todo_log = self.kontaktperson
                                self.create_todo = 1
                            else:
                                # MVBE Spezial-Hack
                                if frappe.db.exists("Beratung", self.name):
                                    frappe.get_doc({
                                        'doctype': 'ToDo',
                                        'description': 'Vorprüfung {0}<br>Zuweisung für Beratung {0}'.format(self.beratungskategorie, self.name),
                                        'reference_type': 'Beratung',
                                        'reference_name': self.name,
                                        'assigned_by': frappe.session.user or 'Administrator',
                                        'owner': 'libracore@be.mieterverband.ch'
                                    }).insert(ignore_permissions=True)
                                else:
                                    self.create_be_admin_todo = 1
        '''
        -------------------------------------------------------------------------------------------------------
            Nachfolgende Stelle auskommentiert weil nach Rücksprache mit ChLa dies falsch zu sein scheint.
            Bei der Anlage von Beratungen (Status Eingang inkl. Mitglied) soll keine autom. Zuweisung erfolgen!
            Siehe uch https://wiki.mieterverband.ch/pages/viewpage.action?pageId=107184296#BeratungDokumentation(Entwurf)-Status%C3%A4nderungen(automatisiert)
        --------------------------------------------------------------------------------------------------------
        if (self.mv_mitgliedschaft and self.status == 'Eingang') and not self.kontaktperson:
            if self.beratungskategorie not in ('202 - MZ-Erhöhung', '300 - Nebenkosten'):
                default_emailberatung_todo_gruppe = frappe.db.get_value("Sektion", self.sektion_id, "default_emailberatung_todo_gruppe")
                if default_emailberatung_todo_gruppe:
                    self.kontaktperson = default_emailberatung_todo_gruppe
                    self.auto_todo_log = self.kontaktperson
                    self.create_todo = 1
            else:
                # MVBE Spezial-Hack
                if frappe.db.exists("Beratung", self.name):
                    frappe.get_doc({
                        'doctype': 'ToDo',
                        'description': 'Vorprüfung {0}<br>Zuweisung für Beratung {0}'.format(self.beratungskategorie, self.name),
                        'reference_type': 'Beratung',
                        'reference_name': self.name,
                        'assigned_by': frappe.session.user or 'Administrator',
                        'owner': 'libracore@be.mieterverband.ch'
                    }).insert(ignore_permissions=True)
                else:
                    self.create_be_admin_todo = 1
        '''
        
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
    
    def status_handler(self):
        # Prüfung ob Beratung gerade angelegt wird
        if frappe.db.exists("Beratung", self.name):
            # Beratung existiert und wurde verändert
            if len(self.termin) > 0 and self.status not in ('Closed', 'Nicht-Mitglied-Abgewiesen'):
                # Manuelle Anlage via "Termin erstellen"
                self.status = 'Termin vergeben'
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
                        
                        # Bei Wechsel von "Eingang" auf "Offen ohne Berater*in -> Eintragung Standardberater*in
                        if self.status == 'Open' and not self.kontaktperson:
                            default_emailberatung_todo_gruppe = frappe.db.get_value("Sektion", self.sektion_id, "default_emailberatung_todo_gruppe")
                            if default_emailberatung_todo_gruppe:
                                self.kontaktperson = default_emailberatung_todo_gruppe
                                self.auto_todo_log = self.kontaktperson
                                self.create_todo = 1
                        
                else:
                    if self.status not in ('Closed', 'Nicht-Mitglied-Abgewiesen'):
                        if self.status == 'Rückfragen' and self.kontaktperson:
                            bisherige_kontaktperson = frappe.db.get_value("Beratung", self.name, 'kontaktperson') or None
                            if not bisherige_kontaktperson:
                                self.status = 'Open'
                        elif self.status == 'Rückfragen' and self.ungelesen == 1 and not self.kontaktperson:
                            self.status = 'Open'
                            # Zuweisung Defaultberater*in
                            self.zuweisung_default_berater_in()
        else:
            # Beratung wird aktuell angelegt
            if self.anlage_durch_web_formular:
                # anlage via web formular
                self.status = 'Eingang'
                '''
                Achtung MVBE-Hack
                '''
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
                else:
                    # Anlage manuell
                    self.status = 'Eingang'
                    if len(self.termin) > 0:
                        # Manuelle Anlage via "Termin erstellen"
                        self.status = 'Termin vergeben'
    
    def zuweisung_default_berater_in(self):
        if self.sektion_id:
            default_emailberatung_todo_gruppe = frappe.db.get_value("Sektion", self.sektion_id, "default_emailberatung_todo_gruppe")
            if default_emailberatung_todo_gruppe:
                self.kontaktperson = default_emailberatung_todo_gruppe
                self.auto_todo_log = self.kontaktperson
                self.create_todo = 1
                    
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
    
    def split_beratung(self, communication_id):
        from copy import deepcopy

        replicated_beratung = deepcopy(self)

        frappe.get_doc(replicated_beratung).insert()

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

        return replicated_beratung.name

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
    if len(verknuepfungen_zu) > 0:
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
    communication = self
    if communication.sent_or_received == 'Received':
        if communication.reference_doctype == 'Beratung':
            beratung = frappe.get_doc("Beratung", communication.reference_name)
            if frappe.db.count("Communication", {'reference_doctype': 'Beratung', 'reference_name': communication.reference_name}) < 2:
                if not beratung.notiz:
                    beratung.notiz = communication.content
                if not beratung.sektion_id:
                    beratung.sektion_id = frappe.db.get_value("Email Account", communication.email_account, 'sektion_id')
                if not beratung.raised_by_name:
                    beratung.raised_by_name = communication.sender_full_name
                if not beratung.raised_by:
                    beratung.raised_by = communication.sender
                beratung.ungelesen = 1
                beratung.save()
            else:
                beratung.ungelesen = 1
                beratung.save()
            relink_attachements(communication.name, beratung.name)

def new_initial_todo(self, event):
    if int(self.create_todo == 1):
        new_todo(self.name, self.kontaktperson)
        # ~ frappe.db.set_value("Beratung", self.name, 'status', 'Open', update_modified=False)
        frappe.db.commit()

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
        master_doc.notiz += slave_doc.notiz
    else:
        master_doc.notiz = slave_doc.notiz
    
    if master_doc.antwort:
        master_doc.antwort += slave_doc.antwort
    else:
        master_doc.antwort = slave_doc.antwort
    
    master_doc.save()
    
    frappe.db.set_value("Beratung", slave_doc.name, "master", master_doc.name)
    frappe.db.set_value("Beratung", slave_doc.name, "status", 'Zusammengeführt')
    
    # relink files
    beratungs_files = frappe.db.sql("""SELECT `name` FROM `tabFile` WHERE `attached_to_name` = '{0}'""".format(slave_doc.name), as_dict=True)
    if len(beratungs_files) > 0:
        for beratung_file in beratungs_files:
            frappe.db.set_value("File", beratung_file.name, "attached_to_name", master_doc.name)
    
    return

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
        orte = frappe.db.sql("""SELECT `ort` AS `ort_def` FROM `tabBeratungsort Multiselect` WHERE `parent` = '{kontakt}' ORDER BY `ort` ASC""".format(kontakt=kontakt), as_dict=True)
    
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

@frappe.whitelist()
def create_neue_beratung(von, bis, art, ort, berater_in, notiz=None, beratungskategorie=None, beratung=None, sektion_id=None, mv_mitgliedschaft=None):
    if not beratung:
        # erstelle neue Beratung
        beratung = frappe.get_doc({
            "doctype": "Beratung",
            "sektion_id": sektion_id,
            "beratungskategorie": beratungskategorie,
            "mv_mitgliedschaft": mv_mitgliedschaft,
            "termin": [
                {
                    "von": von,
                    "bis": bis,
                    "art": art,
                    'ort': ort,
                    'berater_in': berater_in
                }
            ],
            "kontaktperson": berater_in,
            "notiz": notiz
        })
        beratung.insert()
    else:
        # füge Termin zu bestehenden Beratung hinzu
        beratung = frappe.get_doc("Beratung", beratung)
        row = beratung.append('termin', {})
        row.von = von
        row.bis = bis
        row.art = art
        row.ort = ort
        row.berater_in = berater_in
        beratung.kontaktperson = berater_in
        beratung.notiz = notiz
        if mv_mitgliedschaft:
            beratung.mv_mitgliedschaft = mv_mitgliedschaft
        beratung.save()
    
    return beratung.name

def relink_attachements(communication, beratung):
    files = frappe.db.sql("""SELECT `name` FROM `tabFile` WHERE `attached_to_doctype` = 'Communication' AND `attached_to_name` = '{0}'""".format(communication), as_dict=True)
    for file_record in files:
        frappe.db.set_value("File", file_record.name, 'attached_to_doctype', "Beratung")
        frappe.db.set_value("File", file_record.name, 'attached_to_name', beratung)

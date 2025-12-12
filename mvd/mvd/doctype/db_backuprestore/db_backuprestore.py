# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from frappe.utils.password import get_decrypted_password
from frappe.utils.background_jobs import enqueue

class DBBackupRestore(Document):
    def create_json(self):
        # Alle Doctypes, die für einen Restore exportiert werden sollen
        doctypes = [
            "Service Plattform API",
            "Email Domain",
            "Email Account",
            "Notification",
            "Auto Email Report",
            "Social Login Key",
            "Postretouren Einstellungen",
            "MVD Settings",
            "Calendar Sync Settings",
            "JWT"
        ]

        data = {}

        for dt in doctypes:
            meta = frappe.get_meta(dt)

            # Liste aller Passwort-Felder des Doctypes
            password_fields = [df.fieldname for df in meta.fields if df.fieldtype == "Password"]

            # Single DocType
            if meta.issingle:
                doc = frappe.get_single(dt)
                d = doc.as_dict()

                # Passwort-Felder entschlüsseln und Klartext in das Dict schreiben
                for fieldname in password_fields:
                    d[fieldname] = get_decrypted_password(
                        dt,
                        dt,
                        fieldname,
                        raise_exception=False
                    )

                data[dt] = [d]

            # Normale DocTypes
            else:
                docs = []
                names = frappe.get_all(dt)

                for dt_name in names:
                    doc = frappe.get_doc(dt, dt_name.name)
                    d = doc.as_dict()

                    # Passwort-Felder entschlüsseln und Klartext in das Dict schreiben
                    for fieldname in password_fields:
                        d[fieldname] = get_decrypted_password(
                            dt,
                            dt_name.name,
                            fieldname,
                            raise_exception=False,
                        )

                    docs.append(d)

                data[dt] = docs
        

        # JSON-String bauen
        json_content = json.dumps(data, indent=4, ensure_ascii=False, default=str)
        
        # Alte Attachments löschen
        old_files = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "DB BackupRestore",
                "attached_to_name": "DB BackupRestore",
                "file_name": "db_backup_restore_data.json",
            }
        )
        for f in old_files:
            frappe.delete_doc("File", f.name, ignore_permissions=True)
        
        # Neues Attachment erstellen
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": "db_backup_restore_data.json",
            "content": json_content,
            "is_private": 1,
            "attached_to_doctype": "DB BackupRestore",
            "attached_to_name": "DB BackupRestore",
        })

        file_doc.insert(ignore_permissions=True)

        return

    def load_json(self):
        args = {}
        enqueue("mvd.mvd.doctype.db_backuprestore.db_backuprestore._load_json", queue='long', job_name='Lade JSON Backup Konfigurationsdatei', timeout=5000, **args)

def _load_json():
    # Letztes (neustes) Restore-File holen
    files = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "DB BackupRestore",
            "attached_to_name": "DB BackupRestore",
            "file_name": "db_backup_restore_data.json",
        },
        order_by="creation desc",
        limit=1,
    )

    if not files:
        frappe.throw("Kein 'db_backup_restore_data.json'-Attachment am Doctype DB BackupRestore gefunden.")

    file_doc = frappe.get_doc("File", files[0].name)
    content = file_doc.get_content()

    # content kann bytes oder str sein
    if isinstance(content, bytes):
        content = content.decode("utf-8")

    data = json.loads(content)

    for dt, docs in data.items():
        try:
            meta = frappe.get_meta(dt)

            # Single DocType
            if meta.issingle:
                d = docs[0] if docs else {}
                if not d:
                    continue

                doc = frappe.get_single(dt)

                # Child-Table-Felder auslesen
                table_fields = [df for df in meta.fields if df.fieldtype == "Table"]

                # normale Felder setzen (ohne Child-Tables)
                for key, value in d.items():
                    # Meta-Felder überspringen
                    if key in ["name", "owner", "creation", "modified", "modified_by"]:
                        continue
                    # Child-Table-Felder überspringen
                    if any(key == tf.fieldname for tf in table_fields):
                        continue

                    setattr(doc, key, value)

                # Child-Tabellen neu aufbauen
                for tf in table_fields:
                    fieldname = tf.fieldname
                    rows = d.get(fieldname, []) or []

                    # Child-Table leeren
                    doc.set(fieldname, [])

                    # neue Zeilen hinzufügen
                    for row in rows:
                        # Meta-Felder entfernen
                        for k in ["name", "owner", "creation", "modified", "modified_by", "parent", "parenttype", "parentfield"]:
                            row.pop(k, None)

                        doc.append(fieldname, row)

                doc.flags.ignore_mandatory = True
                doc.flags.ignore_permissions = True
                doc.save()

            # Normaler DocType
            else:
                # Alle existierende Records löschen
                old_records = frappe.get_all(dt)
                for old_record in old_records:
                    frappe.delete_doc(dt, old_record.name, ignore_permissions=True, force=True)
                frappe.db.commit()

                for d in docs:
                    name = d.get("name")
                    
                    if name and frappe.db.exists(dt, name):
                        # existierenden Datensatz updaten
                        doc = frappe.get_doc(dt, name)
                        doc.update(d)
                        doc.flags.ignore_mandatory = True
                        doc.flags.ignore_permissions = True
                        doc.save()
                    else:
                        # neuen Datensatz anlegen
                        doc = frappe.get_doc(d)
                        doc.flags.ignore_mandatory = True
                        doc.flags.ignore_permissions = True
                        doc.db_insert()

        except Exception as err:
            frappe.throw(str(frappe.get_traceback()))
        frappe.db.commit()

    return
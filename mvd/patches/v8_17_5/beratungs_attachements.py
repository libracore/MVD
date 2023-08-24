import frappe
from frappe import _
from mvd.mvd.doctype.retouren.retouren import adresse_geaendert_check

def execute():
    try:
        print("Prüfe Beratungs Attachements")
        beratungs_attachements = frappe.db.sql("""SELECT `name`, `file_url`, `attached_to_name`, `file_name` FROM `tabFile` WHERE `attached_to_doctype` = 'Beratung'""", as_dict=True)
        total = len(beratungs_attachements)
        loop = 1
        betroffen = 0
        for beratungs_attachement in beratungs_attachements:
            print("{0} of {1}".format(loop, total))
            if beratungs_attachement.attached_to_name:
                vorhanden = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratungsdateien` WHERE `file` = '{fileurl}' AND `parent` = '{beratung}'""".format(fileurl=beratungs_attachement.file_url, \
                    beratung=beratungs_attachement.attached_to_name), as_dict=True)[0].qty
                if vorhanden < 1:
                    betroffen += 1
                    try:
                        b = frappe.get_doc("Beratung", beratungs_attachement.attached_to_name)
                        row = b.append('dokumente', {})
                        row.file = beratungs_attachement.file_url
                        row.document_type = 'Sonstiges'
                        row.filename = beratungs_attachement.file_name
                        b.save()
                    except:
                        print("File: {0} // Beratung: {1}".format(beratungs_attachement.name, beratungs_attachement.attached_to_name))
            loop += 1
        frappe.db.commit()
        print("Fertig, {0} betroffene korrigiert".format(betroffen))
    except Exception as err:
        print("Patch v8.17.5 failed")
        print(str(err))
        pass
    try:
        print("Prüfe Communication Attachements")
        communication_attachements = frappe.db.sql("""SELECT `name`, `file_url`, `attached_to_name`, `file_name` FROM `tabFile` WHERE `attached_to_doctype` = 'Communication'""", as_dict=True)
        total = len(communication_attachements)
        loop = 1
        betroffen = 0
        for communication_attachement in communication_attachements:
            print("{0} of {1}".format(loop, total))
            if frappe.db.get_value("Communication", communication_attachement.attached_to_name, 'sent_or_received') == 'Received':
                if frappe.db.get_value("Communication", communication_attachement.attached_to_name, 'reference_doctype') == 'Beratung':
                    beratung = frappe.db.get_value("Communication", communication_attachement.attached_to_name, 'reference_name')
                    vorhanden = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabFile` WHERE `file_url` = '{fileurl}' AND `attached_to_name` = '{beratung}'""".format(\
                        fileurl=communication_attachement.file_url, \
                        beratung=beratung), as_dict=True)[0].qty
                    if vorhanden < 1:
                        betroffen += 1
                        # copy file and link to beratung
                        from copy import deepcopy
                        file_record = frappe.get_doc("File", communication_attachement.name)
                        new_file = deepcopy(file_record)
                        new_file.name = None
                        new_file.content = None
                        new_file.attached_to_doctype = 'Beratung'
                        new_file.attached_to_name = beratung
                        new_file.insert(ignore_permissions=True)
                        # create new file row in beratung
                        b = frappe.get_doc("Beratung", beratung)
                        row = b.append('dokumente', {})
                        row.file = new_file.file_url
                        row.document_type = 'Sonstiges'
                        row.filename = new_file.file_name
                        b.save()
            loop += 1
        frappe.db.commit()
        print("Fertig, {0} betroffene korrigiert".format(betroffen))
    except Exception as err:
        print("Patch v8.17.5 failed")
        print(str(err))
        pass
    return

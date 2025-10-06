# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.utils.manuelle_rechnungs_items import get_item_price
from mvd.mvd.doctype.webshop_order.webshop_order import create_order_from_api
import json
from frappe.utils import cint
from frappe.utils import sanitize_html

'''
Beispiel CURL Request
----------------------
curl --location --request POST 'https://[DOMAIN]/api/method/mvd.mvd.v2.api.get_data' \
--header 'Authorization: token [API_KEY]:[API_SECRET]' \
--header 'Content-Type: application/json' \
--header 'Cookie: full_name=Guest; sid=Guest; system_user=yes; user_id=Guest; user_image=' \
--data-raw '{}'
'''

class return_object:
    def __init__(self):
        self.sektionen=[]
    
    def add_sektion(self, sektion):
        self.sektionen.append(sektion)
    
    def asDict(self):
        return self.__dict__

class sektion_object:
    def __init__(self):
        self.sektion=None
        self.doctype_sektion=None
        self.all_items=None
    
    def set_values(self, sektion, all_items):
        self.sektion = sektion.name
        self.all_items = all_items
        # insert whole classe i.e. doctype sektion
        self.doctype_sektion = frappe.get_doc("Sektion", sektion.name)
    def asDict(self):
        return self.__dict__

'''
    API Endpunkt
'''
# @frappe.whitelist(allow_guest=True)
@frappe.whitelist()
def get_data_sektionen(**api_request):
    return_obj = return_object()
    sektionen = frappe.db.sql("""
                                SELECT
                                    `name`,
                                    `mitgliedschafts_artikel` AS `mitgliedschaft_privat`
                                FROM `tabSektion`
                                WHERE `pseudo_sektion` != 1 AND `name` != 'M+W-Abo'
                              """, as_dict=True)
    for sektion in sektionen:
        sektion_obj = sektion_object()
        all_items = get_all_item_details(sektion)
        sektion_obj.set_values(sektion, all_items)
        return_obj.add_sektion(sektion_obj.asDict())

    frappe.local.response.http_status_code = 200
    frappe.local.response.message = return_obj.asDict()
    return

'''
    Hilfs-Methoden
'''
def get_item_names_of_doctype(doctype_name):
    '''
    Holt und gibt alle Item-Namen aus dem Doctype Sektion als Liste zurück
    '''
    meta = frappe.get_meta(doctype_name)

    link_fields = []
    
    for field in meta.fields:
        if field.fieldtype == 'Link' and field.options == 'Item':
            link_fields.append(field.fieldname)
    
    return link_fields


def get_all_item_details(sektion):
    '''
    Holt und gibt alle Item-Details aus dem Doctype Sektion zurück mit Artielnummer, Beschreibung und Preis
    '''

    #all_items = get_item_names_of_doctype("Sektion")
    all_items = ["mitgliedschafts_artikel", "mitgliedschafts_artikel_geschaeft", "mitgliedschafts_artikel_beitritt", "mitgliedschafts_artikel_beitritt_geschaeft", "mitgliedschafts_artikel_reduziert", "mitgliedschafts_artikel_gratis", "hv_artikel", "spenden_artikel"]
    
    # das ist nicht schön so
    doctype_sektion = frappe.get_doc("Sektion", sektion.name)
    
    items = {}
    for item_field_name in all_items:
        if doctype_sektion.get(item_field_name):
            item_name = doctype_sektion.get(item_field_name)
            item_details = frappe.db.sql("""
                                            SELECT
                                                `name`,
                                                `description`,
                                                NULL AS `rate`
                                            FROM `tabItem`
                                            WHERE `name` = '{0}'
                                        """.format(item_name), as_dict=True)
            if len(item_details) > 0:
                item_details[0].rate = get_item_rate(item_details[0].name)
                #items.append(item_details[0])   
                items[item_details[0].name] = item_details[0]   
                items[item_details[0].name]['field_name'] = item_field_name          
    
    return items

def get_item_rate(item):
    return get_item_price(item)['price']

@frappe.whitelist()
def get_mvd_shop_all_items():
    """
    Retrieves a list of all enabled items from the 'tabItem' table along with their associated pricing and member rates.

    This function performs the following steps:
    1. Retrieves all items from the 'tabItem' table that are not marked as 'disabled' (disabled = 0).
    2. For each item, it sets default values for `rate` and `member_rate` to `NULL` (as placeholders).
    3. Retrieves the latest item rates from the `tabItem Price` table using the `get_mvd_rates()` function.
    4. Retrieves member-specific pricing for items from the `tabPricing Rule` table using the `get_mvd_member_rates()` function.
    5. Returns a list of items with the necessary data, which can include `rate` and `member_rate` if they exist.

    Returns:
        list: A list of dictionaries containing item details, including:
              - `item_code`: Unique identifier for the item.
              - `sektion_id`: Section ID of the item.
              - `item_name`: Name of the item.
              - `item_group`: Item group to which the item belongs.
              - `show_in_website`: Boolean (0 or 1)
              - `description`: Web long description of the item.
              - `rate`: Price list rate (optional, populated later).
              - `member_rate`: Member-specific rate (optional, populated later).
              - `image`: URL or path to the item's image.
    """
    items = frappe.db.sql("""SELECT `item_code` AS `item_code`,
                                `sektion_id` AS `sektion_id`,
                                `item_name` AS `item_name`,
                                `item_group` AS `item_group`,
                                `web_long_description` AS `description`,
                                `show_in_website` AS `show_in_website`,
                                NULL AS `rate`,
                                NULL AS `member_rate`,
                                `website_image` AS `image`
                                FROM `tabItem` 
                                WHERE `disabled` = 0 -- später brauchen wir noch webEnabled
                            ORDER BY `sektion_id`, `weightage` ASC;""", as_dict=True)
    item_rates = get_mvd_rates()
    item_member_rates = get_mvd_member_rates()

    for item in items:
        if item.item_code in item_rates:  # Update rate if available
            item.rate = item_rates[item.item_code].get('price_list_rate')
        if item.item_code in item_member_rates:  # Update member_rate if available
            item.member_rate = item_member_rates[item.item_code].get('rate')

    return items

def get_mvd_rates():
    """
    Fetches the latest valid price list rates for each item from the 'tabItem Price' table. For this 
    the function retrieves the most recent `price_list_rate` for each `item_code`.

    Returns:
        dict: A dictionary where the keys are `item_code` and the values are dictionaries containing
              item details such as `price_list_rate`.   
    """
    item_rates = frappe.db.sql("""SELECT *
                                FROM `tabItem Price` tip1
                                WHERE tip1.valid_from <= CURDATE()
                                AND tip1.valid_from = (
                                    SELECT MAX(valid_from)
                                    FROM `tabItem Price` tip2 
                                    WHERE tip1.item_code = tip2.item_code
                                    AND tip2.valid_from <= CURDATE()
                                );""", as_dict=True)
    return {item['item_code']: item for item in item_rates}

def get_mvd_member_rates():
    """
    Fetches the member-specific pricing rates for each `item_code` from the 'tabPricing Rule' table.

    The pricing rule has either no end date (`valid_upto` is NULL) or has a `valid_upto`
    date that has not yet passed. 
    
    The function performs a SQL query that joins the `tabPricing Rule Item Code` table with the `tabPricing Rule`
    table to retrieve the `rate` for each `item_code`.
    Returns:
        dict: A dictionary where the keys are `item_code` and the values are dictionaries containing
              the item pricing rule details, including the `rate`.
    """
    item_member_rates = frappe.db.sql("""SELECT tpric.*, tpr.rate, tpr.applicable_for 
                                FROM `tabPricing Rule Item Code` tpric
                                JOIN `tabPricing Rule` tpr 
                                    ON tpric.parent = tpr.name
                                WHERE tpr.applicable_for = 'Customer Group'
                                AND (tpr.valid_upto IS NULL OR NOT tpr.valid_upto <= CURDATE());""", as_dict=True)
    return {item['item_code']: item for item in item_member_rates}

@frappe.whitelist()
def get_member_annual_invoices(id):
    invoices = frappe.get_all(
    "Sales Invoice",
    filters={
        "mv_mitgliedschaft": id,
        "ist_mitgliedschaftsrechnung": 1},
    fields=['name', 'mitgliedschafts_jahr', 'grand_total', 'due_date', 'status', 'payment_reminder_level', 'outstanding_amount']
)

    # Determine base URL from request
    host = frappe.request.host or ""
    scheme = frappe.request.scheme or "https"
    base_url = "{0}://{1}".format(scheme, host)

    for sinv in invoices:
        if sinv['status'] != 'Paid':
            signature = frappe.get_doc("Sales Invoice", sinv.name).get_signature()
            sinv['pdf_link'] = "{0}/api/method/mvd.mvd.v2.api.get_annual_invoice_pdf?invoice_name={1}&signature={2}".format(
                base_url, sinv['name'], signature
            )
            sinv.pop('name', None)
        else:
            sinv['pdf_link'] = None
        
        if sinv['status'] == 'Paid':
            payment_entry_ref = frappe.get_all(
                "Payment Entry Reference",
                filters={'reference_name': sinv['name']},
                fields=['parent'],
                order_by="creation desc",
                limit=1
            ) # get all für den Fall, dass es mehrere Zahlungen für eine Rechnung gibt. Nur die letzte Zahlung wird angezeigt.
            if payment_entry_ref:
                posting_date = frappe.get_value("Payment Entry", payment_entry_ref[0].parent, 'posting_date')
                sinv['posting_date'] = posting_date
            else:
                sinv['posting_date'] = None
        else:
            sinv['posting_date'] = None

    return invoices

@frappe.whitelist(allow_guest=True)
def get_annual_invoice_pdf(invoice_name=None, signature=False):
    try:
        from erpnextswiss.erpnextswiss.guest_print import get_pdf_as_guest
        return get_pdf_as_guest(doctype="Sales Invoice", name=invoice_name, format="Automatisierte Mitgliedschaftsrechnung", key=signature)
    except Exception as err:
        return ['500 Internal Server Error', str(err)]

@frappe.whitelist(allow_guest=True)
def payrexx_webhook(**kwargs):
    from mvd.mvd.doctype.payrexxwebhooks.payrexxwebhooks import process_webhook
    process_webhook(kwargs)

@frappe.whitelist()
def kampagne(**kwargs):
    #kwargs = json.loads(frappe.local.request.get_data())
    # Convert list to JSON string for DB field
    if isinstance(kwargs.get("newsletter_names"), list):
        kwargs["newsletter_names"] = json.dumps(kwargs["newsletter_names"])

    if kwargs.get("id", None):
        if frappe.db.exists("Kampagne", kwargs.get("id", None)):
            kwargs['doctype'] = "Kampagne"
            if "cmd" in kwargs:
                del kwargs["cmd"]
            kampagne_doc = frappe.get_doc("Kampagne", kwargs.get("id", None))
            kampagne_doc.update(kwargs)
            frappe.local.response.update({
                "data": kampagne_doc.save().as_dict()
            })
            frappe.db.commit()
        else:
            if "cmd" in kwargs:
                del kwargs["cmd"]
            kwargs['doctype'] = "Kampagne"
            frappe.local.response.update({
                "data": frappe.get_doc(kwargs).insert().as_dict()
            })
            frappe.db.commit()
    else:
        raise frappe.NameError

'''
    API endpoints for creating consultations and uploading files related to consultations via the website
'''
@frappe.whitelist()
def create_beratung(**args):
    '''
        API endpoint for creating a new consultation.
        Returns consultation ID in case of success.
    '''
    try:
        create_beratungs_log(error=0, info=1, beratung=None, method='create_beratung', title='Neue Beratung wird duch Website angelegt', json="{0}".format(str(args)))

        if frappe.db.exists("Mitgliedschaft", args['mitglied_id']):
            sektion = frappe.db.get_value("Mitgliedschaft", args['mitglied_id'], "sektion_id")
            topic = None
            beratungskategorie = None
            if args['topic'] != 'anderes':
                if args['topic'] == 'Mietzinserhöhung' or args['topic'] == 'mz_erhoehung':
                    beratungskategorie = '202 - Mietzinserhöhung'
                if args['topic'] == 'Mietzinssenkung' or args['topic'] == 'mz_senkung':
                    beratungskategorie = '203 - Mietzinssenkung'
                elif args['topic'] == 'Heiz- und Nebenkosten':
                    beratungskategorie = '300 - Heiz- und Nebenkosten allgemein'

            make_appointment = False
            if 'make_appointment' in args and cint(args['make_appointment']) == 1:
                make_appointment = True
            
            if 'phone' in args and args['phone']:
                phone = """<b>Telefon:</b> {0}<br>""".format(args['phone'])
            else:
                phone = ''
            if 'email' in args and args['email']:
                email = """<b>E-Mail:</b> <a href="mailto:{0}">{0}</a><br>""".format(args['email'])
            else:
                email = ''
            if 'other_rental_property' in args and args['other_rental_property']:
                other_rental_property = """<b>Anderes Mietobjekt:</b><br>{0}<br><br>""".format(sanitize_html(args['other_rental_property']).replace("\n", "<br>"))
            else:
                other_rental_property = ''
            if args['question']:
                question = """<b>Frage:</b><br>{0}<br><br>""".format(sanitize_html(args['question']).replace("\n", "<br>"))
            else:
                question = ''
            if 'date_rent_notification' in args and args['date_rent_notification']:
                date_rent_notification = """<b>Briefdatum der Mietzinserhöhungsanzeige:</b> {0}""".format(args['date_rent_notification'])
            else:
                date_rent_notification = ''
            
            notiz = """{0}{1}{2}{3}{4}""".format(phone, email, other_rental_property, question, date_rent_notification)
            
            new_ber = frappe.get_doc({
                'doctype': 'Beratung',
                'status': 'Rückfrage: Termin vereinbaren' if make_appointment else 'Eingang',
                'subject': topic,
                'beratungskategorie': beratungskategorie,
                'mv_mitgliedschaft': args['mitglied_id'],
                'notiz': notiz,
                'raised_by': args['email'] if 'email' in args and args['email'] else None,
                'telefon_privat_mobil': args['phone'] if 'phone' in args and args['phone'] else None,
                'anderes_mietobjekt': args['other_rental_property'] if 'other_rental_property' in args and args['other_rental_property'] else None,
                'frage': args['question'] if args['question'] else None,
                'datum_mietzinsanzeige': args.get('date_rent_notification', None),
                'anlage_durch_web_formular': 1,
                'sektion_id': sektion
            })
            new_ber.insert(ignore_permissions=True)
            frappe.db.commit()
            
            # MVBE Spezial-Hack
            if new_ber.create_be_admin_todo == 1:
                frappe.get_doc({
                    'doctype': 'ToDo',
                    'description': 'Vorprüfung {0}<br>Zuweisung für Beratung {0}'.format(new_ber.beratungskategorie, new_ber.name),
                    'reference_type': 'Beratung',
                    'reference_name': new_ber.name,
                    'assigned_by': 'Administrator',
                    'owner': 'libracore@be.mieterverband.ch'
                }).insert(ignore_permissions=True)
            
            # Mail wird (glaube ich) durch die Website versendet...
            # if args['email']:
            #     send_confirmation_mail(args['mitglied_id'], new_ber.name, notiz, raised_by=args['email'], sektion=sektion)
            
            frappe.local.response.http_status_code = 200
            frappe.local.response.message = new_ber.name
            return
        
        else:
            frappe.local.response.http_status_code = 404
            frappe.local.response.message = 'Mitglied not found'
            return
    
    except Exception as err:
        # allgemeiner Fehler
        create_beratungs_log(error=1, info=0, beratung=None, method='new_beratung', title='Exception', json="{0}".format(str(err)))
        frappe.local.response.http_status_code = 500
        frappe.local.response.message = str(err)

def create_beratungs_log(error=0, info=0, beratung=None, method=None, title=None, json=None):
    '''
        Hilfsmethode für create_beratung()
    '''
    frappe.get_doc({
        'doctype': 'Beratungs Log',
        'error': error,
        'info': info,
        'beratung': beratung,
        'method': method,
        'title': title,
        'json': json
    }).insert(ignore_permissions=True)
    frappe.db.commit()

@frappe.whitelist()
def upload_file_to_beratung():
    '''
        Muss als multipart/form-data curl gesendet werden

        Beispiel CURL Request:
        curl https://[URL]/api/method/mvd.mvd.v2.api.upload_file_to_beratung \
        --header 'Authorization: token [API-Key]:[API-Secret]' \
        -F "file=@testbild.png" \
        -F "beratung=25-08-12-446182"

    '''
    files = frappe.request.files
    is_private = 1 #frappe.form_dict.is_private
    doctype = "Beratung" #frappe.form_dict.doctype
    docname = frappe.form_dict.beratung #frappe.form_dict.docname
    fieldname = None #frappe.form_dict.fieldname
    file_url = None #frappe.form_dict.file_url
    folder = 'Home/Attachments' #frappe.form_dict.folder or 'Home'
    method = None #frappe.form_dict.method
    last_file = cint(frappe.form_dict.last_file)
    beratung_file_type = frappe.form_dict.beratung_file_type or None
    beratung_file_date = frappe.form_dict.beratung_file_date or None
    content = None
    filename = None

    if 'file' in files:
        file = files['file']
        content = file.stream.read()
        filename = file.filename

    frappe.local.uploaded_file = content
    frappe.local.uploaded_filename = filename

    # if frappe.session.user == 'Guest':
    import mimetypes
    filetype = mimetypes.guess_type(filename)[0]
    if filetype not in ['image/png', 'image/jpeg', 'application/pdf']:
        frappe.local.response.http_status_code = 403
        frappe.local.response.message = "File none of JPG, PNG or PDF"
        return

    # if method:
    #     method = frappe.get_attr(method)
    #     is_whitelisted(method)
    #     return method()
    # else:
    file_doc = frappe.get_doc({
        "doctype": "File",
        "attached_to_doctype": doctype,
        "attached_to_name": docname,
        "attached_to_field": fieldname,
        "folder": folder,
        "file_name": filename,
        "file_url": file_url,
        "is_private": cint(is_private),
        "content": content,
        "beratung_datei_typ": beratung_file_type,
        "beratung_datei_datum": beratung_file_date
    })
    try:
        file_doc.insert(ignore_permissions=True)

        if last_file == 1:
            # mark for SP API
            frappe.db.set_value("Beratung", docname, 'trigger_api', 1, update_modified=False)
        
    except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
        pass
        frappe.clear_messages()
        frappe.local.response.http_status_code = 409
        frappe.local.response.message = "Same file has already been attached to the record"
        return
    except Exception as err:
        frappe.local.response.http_status_code = 500
        frappe.local.response.message = str(frappe.get_traceback())
        return
    
    frappe.local.response.http_status_code = 200
    frappe.local.response.message = "File saved"
    return

@frappe.whitelist()
def create_order(**api_request):
    return create_order_from_api(api_request, v2=1)


@frappe.whitelist(allow_guest=True)
def webshop_download(token):
    """
    Serve a PDF download for a given token.
    """
    # Look up the download link record by hash
    link = frappe.db.get_value(
        "Webshop Order Download Link",
        {"download_hash": token},
        ["name", "file"],
        as_dict=True
    )

    if not link:
        frappe.local.response.http_status_code = 404
        frappe.local.response.message = 'Hoppla! Dieser Download-Link ist ungültig. Bitte überprüfen Sie Ihre E-Mail für den richtigen Link oder kontaktieren Sie den Support.'
        return

    # Get the File document
    file_doc = frappe.get_doc("File", link.file)

    # Serve the file inline
    frappe.local.response.filename = file_doc.file_name
    frappe.local.response.filecontent = file_doc.get_content()  # get the file content
    frappe.local.response.type = "pdf"

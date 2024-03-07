# -*- coding: utf-8 -*-
# Copyright (c) 2021-2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_sektion_id, get_status_c, get_mitgliedtyp_c, get_inkl_hv, get_sprache_abk, check_email
from frappe.utils.data import getdate, now, today
from frappe.utils import cint

'''
API Request Eingang
Schritt 1:
    Prüfung ob die Main-Keys vorhanden sind. Ggf. Ablehnung mittels "Bad Request 400"
'''
def api_request_check(kwargs):
    if 'mitgliedId' in kwargs:
        if kwargs["mitgliedId"] > 0:
            missing_keys = check_main_keys(kwargs)
            if not missing_keys:
                create_sp_log(kwargs)
                return raise_200()
            else:
                return missing_keys
        else:
            return raise_xxx(400, 'Bad Request', 'mitgliedId == 0', str(kwargs))
    else:
        return raise_xxx(400, 'Bad Request', 'mitgliedId missing', str(kwargs))

def check_main_keys(kwargs):
    mandatory_keys = [
        'mitgliedNummer',
        'mitgliedId',
        'sektionCode',
        'typ',
        'status',
        'regionCode',
        'istTemporaeresMitglied',
        'fuerBewirtschaftungGesperrt',
        'erfassungsdatum',
        'eintrittsdatum',
        'austrittsdatum',
        'zuzugsdatum',
        'wegzugsdatum',
        'kuendigungPer',
        'jahrBezahltMitgliedschaft',
        'jahrBezahltHaftpflicht',
        'naechstesJahrGeschuldet',
        'bemerkungen',
        'anzahlZeitungen',
        'zeitungAlsPdf',
        'adressen',
        'sprache',
        'needsValidation',
        'isKollektiv',
        'isGeschenkmitgliedschaft',
        'isEinmaligeSchenkung',
        'schenkerHasGeschenkunterlagen',
        'datumBezahltHaftpflicht',
        'onlineHaftpflicht',
        'onlineGutschrift',
        'onlineBetrag',
        'datumOnlineVerbucht',
        'datumOnlineGutschrift',
        'onlinePaymentMethod',
        'onlinePaymentId',
        'kuendigungsgrund'
    ]
    for key in mandatory_keys:
        if key not in kwargs:
            return raise_xxx(400, 'Bad Request', '{key} missing'.format(key=key), daten=kwargs)
    if 'Geschenkmitgliedschaft' in kwargs:
        return raise_xxx(400, 'Bad Request', 'Geschenkmitgliedschaft unbekannt', daten=kwargs)
    else:
        return False

'''
Schritt 2:
    Erstellung "Service Plattform Log"
    Diese werden im Anschluss mittels einem BG-Worker im FiFo-Prinzip abgearbeitet
'''
def create_sp_log(kwargs):
    if frappe.db.exists("Mitgliedschaft", kwargs["mitgliedId"]):
        existing = True
    else:
        existing = False
    import json
    json_formatted_str = json.dumps(kwargs, indent=2)

    # Prüfung ob die Queue aktiv ist, oder der Request sofort ausgeführt werden soll
    sp_incoming_immediately_executing = cint(frappe.db.get_single_value('Service Plattform API', 'sp_incoming_immediately_executing'))

    sp_log = frappe.get_doc({
        "doctype": "Service Plattform Log",
        "status": "New",
        "mv_mitgliedschaft": kwargs["mitgliedId"] if existing else None,
        "json": json_formatted_str,
        "neuanlage": 0 if existing else 1,
        "update": 1 if existing else 0,
        "immediately_executing": sp_incoming_immediately_executing
    }).insert(ignore_permissions=True)
    
    return

'''
API Returns
'''
# Error Return
def raise_xxx(code, title, message, daten=None):
    frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(code, title, message, frappe.utils.get_traceback(), daten or ''), 'SP API Error!')
    frappe.local.response.http_status_code = code
    frappe.local.response.message = message
    return ['{code} {title}'.format(code=code, title=title), {
        "error": {
            "code": code,
            "message": "{message}".format(message=message)
        }
    }]

# Success Return
def raise_200(answer='Success'):
    frappe.local.response.http_status_code = 200
    frappe.local.response.message = answer
    return ['200 Success', answer]

'''
Schritt 3:
    BG-Worker (Abarbeitung API Requests)
'''
def service_plattform_log_worker():
    flush_limit = int(frappe.db.get_single_value('Service Plattform API', 'flush_limit_eingehend')) or 20
    mvzh_filter = """AND `json` NOT LIKE '%sektionCode%:%ZH%'"""
    open_creation_logs = frappe.db.sql("""
                                        SELECT `name`
                                        FROM `tabService Plattform Log`
                                        WHERE `status` IN ('New', 'Failed')
                                        {mvzh_filter}
                                        ORDER BY `creation` ASC
                                        LIMIT {flush_limit}""".format(flush_limit=flush_limit, mvzh_filter=mvzh_filter), as_dict=True)
    
    if len(open_creation_logs) < 1:
        open_creation_logs = frappe.db.sql("""
                                            SELECT `name`
                                            FROM `tabService Plattform Log`
                                            WHERE `status` IN ('New', 'Failed')
                                            ORDER BY `creation` ASC
                                            LIMIT {flush_limit}""".format(flush_limit=flush_limit), as_dict=True)
    
    for service_plattform_log in open_creation_logs:
        sp_log = frappe.get_doc("Service Plattform Log", service_plattform_log.name)
        sp_log_free_to_execute = True
        if sp_log.status == 'New' and sp_log.mv_mitgliedschaft:
            existing_failed_log = get_existing_failed_log(sp_log.mv_mitgliedschaft, sp_log.name)
            if existing_failed_log > 0:
                sp_log_free_to_execute = False
        if sp_log_free_to_execute:
            execute_sp_log(sp_log)

def get_existing_failed_log(mv_mitgliedschaft, sp_log):
    existing_failed_log = frappe.db.sql("""
                                            SELECT COUNT(`name`) AS `qty`
                                            FROM `tabService Plattform Log`
                                            WHERE `status` = 'Failed'
                                            AND `mv_mitgliedschaft` = '{mv_mitgliedschaft}'
                                            AND `name` != '{sp_log}'""".format(mv_mitgliedschaft=mv_mitgliedschaft, sp_log=sp_log), as_dict=True)[0].qty
    return existing_failed_log or 0

@frappe.whitelist()
def execute_sp_log(sp_log, manual_execution=False):
    if manual_execution:
        sp_log = frappe.get_doc("Service Plattform Log", sp_log)
        if sp_log.mv_mitgliedschaft:
            existing_failed_log = get_existing_failed_log(sp_log.mv_mitgliedschaft, sp_log.name)
            if existing_failed_log > 0:
                return 0
    
    import json
    json_object = json.loads(sp_log.json)
    
    import ast
    api_kwargs = ast.literal_eval(str(json_object))
    
    error_in_execution = 'Weder Update noch Neuanlage'
    
    if sp_log.update == 1:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", api_kwargs["mitgliedId"])
        error_in_execution = mvm_update(mitgliedschaft, api_kwargs)
    
    if sp_log.neuanlage == 1:
        # check ob wirklich neuanlage, oder in zwischenzeit bereits angelegt
        if frappe.db.exists("Mitgliedschaft", api_kwargs["mitgliedId"]):
            # wurde in der Zwischenzeit angelegt, sp_log wird als Update verarbeitet
            existing_failed_log = get_existing_failed_log(api_kwargs["mitgliedId"], sp_log.name)
            if existing_failed_log < 1:
                sp_log.neuanlage = 0
                sp_log.update = 1
                mitgliedschaft = frappe.get_doc("Mitgliedschaft", api_kwargs["mitgliedId"])
                error_in_execution = mvm_update(mitgliedschaft, api_kwargs)
            else:
                return
        else:
            # effektive neuanlage
            error_in_execution = mvm_neuanlage(api_kwargs)
    
    if error_in_execution:
        sp_log.status = 'Failed'
        sp_log.add_comment('Comment', text='{0}'.format(error_in_execution))
    else:
        sp_log.status = 'Done'
        if sp_log.neuanlage == 1:
            sp_log.mv_mitgliedschaft = api_kwargs["mitgliedId"]
    
    sp_log.save()
    frappe.db.commit()
    
    if manual_execution:
        return 1

'''
Neuanlage einer Mitgliedschaft
(exklusiv der Adressen und Kontakte)
'''
def mvm_neuanlage(kwargs):
    try:
        # allgemeine Daten
        sektion_id = get_sektion_id(kwargs['sektionCode'])
        if not sektion_id:
            return 'Sektion ({sektion_id}) not found'.format(sektion_id=kwargs['sektionCode'])
        
        status_c = get_status_c(kwargs['status'])
        if not status_c:
            return 'MitgliedStatus ({status_c}) not found'.format(status_c=kwargs['status'])
        
        if kwargs['neueSektionCode']:
            wegzug_zu = get_sektion_id(kwargs['neueSektionCode'])
        else:
            wegzug_zu = ''
        
        if kwargs['alteSektionCode']:
            zuzug_von = get_sektion_id(kwargs['alteSektionCode'])
        else:
            zuzug_von = ''
        
        mitgliedtyp_c = get_mitgliedtyp_c(kwargs['typ'])
        if not mitgliedtyp_c:
            return 'typ ({mitgliedtyp_c}) not found'.format(mitgliedtyp_c=kwargs['Typ'])
        
        if kwargs['zeitungAlsPdf']:
            m_und_w_pdf = 1
        else:
            m_und_w_pdf = 0
        
        if kwargs['isKollektiv']:
            ist_kollektiv = 1
        else:
            ist_kollektiv = '0'
        
        if kwargs['isGeschenkmitgliedschaft']:
            ist_geschenkmitgliedschaft = 1
        else:
            ist_geschenkmitgliedschaft = '0'
        
        if kwargs['isEinmaligeSchenkung']:
            ist_einmalige_schenkung = 1
        else:
            ist_einmalige_schenkung = '0'
        
        if kwargs['schenkerHasGeschenkunterlagen']:
            geschenkunterlagen_an_schenker = 1
        else:
            geschenkunterlagen_an_schenker = '0'
        
        region = ''
        if kwargs['regionCode']:
            regionen = frappe.db.sql("""SELECT `name` FROM `tabRegion` WHERE `region_c` = '{region}'""".format(region=kwargs['regionCode']), as_dict=True)
            if len(regionen) > 0:
                region = regionen[0].name
        
        mitglied_nr = str(kwargs['mitgliedNummer'])
        
        mitglied_id = str(kwargs['mitgliedId'])
        
        region_manuell = 1 if kwargs['regionManuell'] else '0'
        
        inkl_hv = get_inkl_hv(kwargs["jahrBezahltHaftpflicht"])
        
        m_und_w = kwargs['anzahlZeitungen']
        
        wichtig = str(kwargs['bemerkungen']) if kwargs['bemerkungen'] else ''
        
        language = get_sprache_abk(language=kwargs['sprache'])
        # -----------------------------------------------------------------
        
        # Datums Angaben
        if kwargs['eintrittsdatum'] and status_c not in ('Interessent*in', 'Anmeldung', 'Online-Anmeldung'):
            eintritt = kwargs['eintrittsdatum'].split("T")[0]
        else:
            eintritt = None
        
        if kwargs['zuzugsdatum']:
            zuzug = kwargs['zuzugsdatum'].split("T")[0]
        else:
            if status_c == 'Zuzug':
                # hotfix ISS-2024-00060
                # Online Sektionswechsel geben kein Zuzugsdatum an ERPNext weiter.
                zuzug = today()
            else:
                zuzug = None
        
        if kwargs['wegzugsdatum']:
            wegzug = kwargs['wegzugsdatum'].split("T")[0]
        else:
            wegzug = ''
        
        if kwargs['austrittsdatum']:
            austritt = kwargs['austrittsdatum'].split("T")[0]
        else:
            austritt = ''
        
        if kwargs['kuendigungPer']:
            kuendigung = kwargs['kuendigungPer'].split("T")[0]
        else:
            kuendigung = ''
        # -----------------------------------------------------------------
        
        # Zahlungs-Daten (Mitgliedschaft, HV, Datatrans)
        
        zahlung_hv = int(kwargs['jahrBezahltHaftpflicht']) if kwargs['jahrBezahltHaftpflicht'] else 0
        
        bezahltes_mitgliedschaftsjahr = int(kwargs['jahrBezahltMitgliedschaft']) if kwargs['jahrBezahltMitgliedschaft'] else 0
        
        naechstes_jahr_geschuldet = 1 if kwargs['naechstesJahrGeschuldet'] else '0'
        
        if kwargs['datumBezahltHaftpflicht']:
            datum_hv_zahlung = kwargs['datumBezahltHaftpflicht'].split("T")[0]
        else:
            datum_hv_zahlung = None
        
        if kwargs['onlineHaftpflicht']:
            online_haftpflicht = kwargs['onlineHaftpflicht']
        else:
            online_haftpflicht = None
        
        if kwargs['onlineGutschrift']:
            online_gutschrift = kwargs['onlineGutschrift']
        else:
            online_gutschrift = None
        
        if kwargs['onlineBetrag']:
            online_betrag = kwargs['onlineBetrag']
        else:
            online_betrag = None
        
        if kwargs['datumOnlineVerbucht']:
            datum_online_verbucht = kwargs['datumOnlineVerbucht']
            if zuzug_von != 'MVZH':
                datum_zahlung_mitgliedschaft = datum_online_verbucht.split("T")[0]
            else:
                datum_zahlung_mitgliedschaft = None
        else:
            datum_online_verbucht = None
            datum_zahlung_mitgliedschaft = None
        
        if kwargs['datumOnlineGutschrift']:
            datum_online_gutschrift = kwargs['datumOnlineGutschrift']
        else:
            datum_online_gutschrift = None
        
        if kwargs['onlinePaymentMethod']:
            online_payment_method = kwargs['onlinePaymentMethod']
        else:
            online_payment_method = None
        
        if kwargs['onlinePaymentId']:
            online_payment_id = kwargs['onlinePaymentId']
        else:
            online_payment_id = None
        
        # MVB Standard und MVB Mini
        mvb_typ = None
        if 'mvbTyp' in kwargs:
            if kwargs['mvbTyp']:
                mvb_typ = kwargs['mvbTyp']
            else:
                mvb_typ = None
        
        new_mitgliedschaft = frappe.get_doc({
            'doctype': 'Mitgliedschaft',
            'mitglied_nr': mitglied_nr,
            'sektion_id': sektion_id,
            'region': region,
            'region_manuell': region_manuell,
            'status_c': status_c,
            'mitglied_id': mitglied_id,
            'mitgliedtyp_c': mitgliedtyp_c,
            'inkl_hv': inkl_hv,
            'm_und_w': m_und_w,
            'm_und_w_pdf': m_und_w_pdf,
            'wichtig': wichtig,
            'eintrittsdatum': eintritt,
            'zuzug': zuzug,
            'zuzug_von': zuzug_von,
            'wegzug': wegzug,
            'wegzug_zu': wegzug_zu,
            'austritt': austritt,
            'kuendigung': kuendigung,
            'zahlung_hv': zahlung_hv,
            'bezahltes_mitgliedschaftsjahr': bezahltes_mitgliedschaftsjahr,
            'naechstes_jahr_geschuldet': naechstes_jahr_geschuldet,
            'validierung_notwendig': 0,
            'language': language,
            'ist_kollektiv': ist_kollektiv,
            'ist_geschenkmitgliedschaft': ist_geschenkmitgliedschaft,
            'ist_einmalige_schenkung': ist_einmalige_schenkung,
            'geschenkunterlagen_an_schenker': geschenkunterlagen_an_schenker,
            'datum_hv_zahlung': datum_hv_zahlung,
            'letzte_bearbeitung_von': 'SP',
            'online_haftpflicht': online_haftpflicht,
            'online_gutschrift': online_gutschrift,
            'online_betrag': online_betrag,
            'datum_online_verbucht': datum_online_verbucht,
            'datum_online_gutschrift': datum_online_gutschrift,
            'online_payment_method': online_payment_method,
            'online_payment_id': online_payment_id,
            'datum_zahlung_mitgliedschaft': datum_zahlung_mitgliedschaft,
            'mvb_typ': mvb_typ
        })
        
        new_mitgliedschaft = adressen_und_kontakt_handling(new_mitgliedschaft, kwargs)
        
        if not new_mitgliedschaft:
            return 'Bei der Adressen Anlage ist etwas schief gelaufen'
        
        if status_c in ('Online-Anmeldung', 'Online-Beitritt', 'Online-Kündigung'):
            new_mitgliedschaft.validierung_notwendig = 1
            if status_c == 'Online-Beitritt':
                if online_haftpflicht:
                    if int(online_haftpflicht) == 1:
                        new_mitgliedschaft.datum_hv_zahlung = eintritt
                        new_mitgliedschaft.zahlung_hv = int(getdate(eintritt).strftime("%Y"))
                        
                        # Trello 909: Bei Online-Beitritten zwischen 15.09.xx und 31.12.xx muss die HV für das Folgejahr gelten.
                        u_limit = getdate(getdate(eintritt).strftime("%Y") + "-09-15")
                        o_limit = getdate(getdate(eintritt).strftime("%Y") + "-12-31")
                        if getdate(eintritt) >= u_limit:
                            if getdate(eintritt) <= o_limit:
                                new_mitgliedschaft.zahlung_hv += 1
                        # ------------------------------------------------------------------------------------------------------
                new_mitgliedschaft.datum_zahlung_mitgliedschaft = eintritt
        else:
            if kwargs['needsValidation']:
                new_mitgliedschaft.validierung_notwendig = 1
                if status_c != 'Zuzug':
                    new_mitgliedschaft.status_vor_onl_mutation = status_c
                    new_mitgliedschaft.status_c = 'Online-Mutation'
        
        # Zuzugsdatum-Fix bei Sektionswechsel von MVZH
        if new_mitgliedschaft.zuzug_von == 'MVZH' and new_mitgliedschaft.status_c == 'Zuzug':
            if not new_mitgliedschaft.zuzug:
                new_mitgliedschaft.zuzug = today()
        
        # Hotfix bei (libracore/libracore) Sektionswechsel gehandelt durch die SP
        if new_mitgliedschaft.status_c == 'Zuzug':
            if not new_mitgliedschaft.zuzug:
                new_mitgliedschaft.zuzug = today()
            new_mitgliedschaft.zuzug_durch_sp = 1
        
        new_mitgliedschaft.insert()
        frappe.db.commit()
        
        # ACHTUNG: False = Positiv!
        return False
        
    except Exception as err:
        return 'Internal Server Error: {0}'.format(err)

'''

'''
def mvm_update(mitgliedschaft, kwargs, timestamp_mismatch_retry=False):
    try:
        # allgemeine Daten
        sektion_id = get_sektion_id(kwargs['sektionCode'])
        if not sektion_id:
            return 'Sektion ({sektion_id}) not found'.format(sektion_id=kwargs['sektionCode'])
            
        status_vor_onl_mutation = mitgliedschaft.status_c
        status_c = get_status_c(kwargs['status'])
        if not status_c:
            return 'MitgliedStatus ({status_c}) not found'.format(status_c=kwargs['status'])
            
        mitgliedtyp_c = get_mitgliedtyp_c(kwargs['typ'])
        if not mitgliedtyp_c:
            return 'typ ({mitgliedtyp_c}) not found'.format(mitgliedtyp_c=kwargs['Typ'])
        
        if kwargs['neueSektionCode']:
            wegzug_zu = get_sektion_id(kwargs['neueSektionCode'])
        else:
            wegzug_zu = ''
        
        if kwargs['alteSektionCode']:
            zuzug_von = get_sektion_id(kwargs['alteSektionCode'])
        else:
            zuzug_von = ''
        
        if kwargs['zeitungAlsPdf']:
            m_und_w_pdf = 1
        else:
            m_und_w_pdf = 0
        
        m_und_w = kwargs['anzahlZeitungen']
        
        if kwargs['isKollektiv']:
            ist_kollektiv = 1
        else:
            ist_kollektiv = '0'
        
        if kwargs['isGeschenkmitgliedschaft']:
            ist_geschenkmitgliedschaft = 1
        else:
            ist_geschenkmitgliedschaft = '0'
        
        if kwargs['isEinmaligeSchenkung']:
            ist_einmalige_schenkung = 1
        else:
            ist_einmalige_schenkung = '0'
        
        if kwargs['schenkerHasGeschenkunterlagen']:
            geschenkunterlagen_an_schenker = 1
        else:
            geschenkunterlagen_an_schenker = '0'
        
        region = ''
        if kwargs['regionCode']:
            regionen = frappe.db.sql("""SELECT `name` FROM `tabRegion` WHERE `region_c` = '{region}'""".format(region=kwargs['regionCode']), as_dict=True)
            if len(regionen) > 0:
                region = regionen[0].name
        
        region_manuell = 1 if kwargs['regionManuell'] else '0'
        
        mitglied_nr = kwargs['mitgliedNummer']
        
        mitglied_id = kwargs['mitgliedId']
        
        inkl_hv = get_inkl_hv(kwargs["jahrBezahltHaftpflicht"])
        
        wichtig = kwargs['bemerkungen'] if kwargs['bemerkungen'] else ''
        
        language = get_sprache_abk(language=kwargs['sprache']) if kwargs['sprache'] else 'de'
        # -----------------------------------------------------------------
        
        # Datums Angaben
        if kwargs['eintrittsdatum'] and status_c not in ('Interessent*in', 'Anmeldung', 'Online-Anmeldung'):
            eintritt = kwargs['eintrittsdatum'].split("T")[0]
        else:
            eintritt = None
        
        if kwargs['zuzugsdatum']:
            zuzug = kwargs['zuzugsdatum'].split("T")[0]
        else:
            zuzug = ''
        
        if kwargs['wegzugsdatum']:
            wegzug = kwargs['wegzugsdatum'].split("T")[0]
        else:
            wegzug = ''
        
        if kwargs['austrittsdatum']:
            austritt = kwargs['austrittsdatum'].split("T")[0]
        else:
            austritt = ''
        
        if kwargs['kuendigungPer']:
            if kwargs['needsValidation'] and status_c not in ('Online-Anmeldung', 'Online-Beitritt', 'Online-Kündigung', 'Zuzug'):
                if not mitgliedschaft.kuendigung:
                    kuendigung = kwargs['kuendigungPer'].split("T")[0]
                else:
                    kuendigung = mitgliedschaft.kuendigung
            else:
                if sektion_id == 'MVZH':
                    kuendigung = kwargs['kuendigungPer'].split("T")[0]
                else:
                    kuendigung = mitgliedschaft.kuendigung
        else:
            kuendigung = ''
        # -----------------------------------------------------------------
        
        # Zahlungs-Daten (Mitgliedschaft, HV, Datatrans)
        if kwargs['datumBezahltHaftpflicht']:
            datum_hv_zahlung = kwargs['datumBezahltHaftpflicht'].split("T")[0]
        else:
            datum_hv_zahlung = None
        
        if kwargs['onlineHaftpflicht'] or kwargs['onlineHaftpflicht'] == 0:
            online_haftpflicht = kwargs['onlineHaftpflicht']
        else:
            online_haftpflicht = None
        
        zahlung_hv = int(kwargs['jahrBezahltHaftpflicht']) if kwargs['jahrBezahltHaftpflicht'] else 0
        
        if kwargs['onlineGutschrift']:
            online_gutschrift = kwargs['onlineGutschrift']
        else:
            online_gutschrift = None
        
        if kwargs['onlineBetrag']:
            online_betrag = kwargs['onlineBetrag']
        else:
            online_betrag = None
        
        if kwargs['datumOnlineVerbucht']:
            datum_online_verbucht = kwargs['datumOnlineVerbucht']
        else:
            datum_online_verbucht = None
        
        if kwargs['datumOnlineGutschrift']:
            datum_online_gutschrift = kwargs['datumOnlineGutschrift']
        else:
            datum_online_gutschrift = None
        
        if kwargs['onlinePaymentMethod']:
            online_payment_method = kwargs['onlinePaymentMethod']
        else:
            online_payment_method = None
        
        if kwargs['onlinePaymentId']:
            online_payment_id = kwargs['onlinePaymentId']
        else:
            online_payment_id = None
        
        bezahltes_mitgliedschaftsjahr = int(kwargs['jahrBezahltMitgliedschaft']) if kwargs['jahrBezahltMitgliedschaft'] else 0
        
        naechstes_jahr_geschuldet = 1 if kwargs['naechstesJahrGeschuldet'] else '0'

        # MVB Standard und MVB Mini
        mvb_typ = None
        if 'mvbTyp' in kwargs:
            if kwargs['mvbTyp']:
                mvb_typ = kwargs['mvbTyp']
            else:
                mvb_typ = None
        
        # -----------------------------------------------------------------
        
        # erstelle ggf. status change log und Status-Änderung
        if status_c != mitgliedschaft.status_c:
            change_log_row = mitgliedschaft.append('status_change', {})
            change_log_row.datum = now()
            change_log_row.status_alt = mitgliedschaft.status_c
            change_log_row.status_neu = status_c
            if status_c == 'Online-Kündigung':
                if kwargs['kuendigungsgrund'] == 'Andere Gründe':
                    change_log_row.grund = kwargs['kuendigungsgrund'] + ": " + kwargs['kuendigungsgrundBemerkung'] if kwargs['kuendigungsgrundBemerkung'] else '---'
                else:
                    change_log_row.grund = kwargs['kuendigungsgrund']
            else:
                change_log_row.grund = 'SP Update'
        
        mitgliedschaft.mitglied_nr = mitglied_nr
        mitgliedschaft.sektion_id = sektion_id
        mitgliedschaft.region = region
        mitgliedschaft.region_manuell = region_manuell
        mitgliedschaft.status_c = status_c
        mitgliedschaft.mitglied_id = mitglied_id
        mitgliedschaft.mitgliedtyp_c = mitgliedtyp_c
        mitgliedschaft.inkl_hv = inkl_hv
        mitgliedschaft.m_und_w = m_und_w
        mitgliedschaft.m_und_w_pdf = m_und_w_pdf
        mitgliedschaft.wichtig = wichtig
        mitgliedschaft.eintrittsdatum = eintritt
        mitgliedschaft.zuzug = zuzug
        mitgliedschaft.zuzug_von = zuzug_von
        mitgliedschaft.wegzug = wegzug
        mitgliedschaft.wegzug_zu = wegzug_zu
        mitgliedschaft.austritt = austritt
        mitgliedschaft.kuendigung = kuendigung
        mitgliedschaft.zahlung_hv = zahlung_hv
        mitgliedschaft.bezahltes_mitgliedschaftsjahr = bezahltes_mitgliedschaftsjahr
        mitgliedschaft.naechstes_jahr_geschuldet = naechstes_jahr_geschuldet
        mitgliedschaft.validierung_notwendig = 0
        mitgliedschaft.language = language
        mitgliedschaft.ist_kollektiv = ist_kollektiv
        mitgliedschaft.ist_geschenkmitgliedschaft = ist_geschenkmitgliedschaft
        mitgliedschaft.ist_einmalige_schenkung = ist_einmalige_schenkung
        mitgliedschaft.geschenkunterlagen_an_schenker = geschenkunterlagen_an_schenker
        mitgliedschaft.datum_hv_zahlung = datum_hv_zahlung
        mitgliedschaft.letzte_bearbeitung_von = 'SP'
        mitgliedschaft.online_haftpflicht = online_haftpflicht
        mitgliedschaft.online_gutschrift = online_gutschrift
        mitgliedschaft.online_betrag = online_betrag
        mitgliedschaft.datum_online_verbucht = datum_online_verbucht
        mitgliedschaft.datum_online_gutschrift = datum_online_gutschrift
        mitgliedschaft.online_payment_method = online_payment_method
        mitgliedschaft.online_payment_id = online_payment_id
        mitgliedschaft.mvb_typ = mvb_typ
        

        try:
            mitgliedschaft = adressen_und_kontakt_handling(mitgliedschaft, kwargs)
        except Exception as err:
            return 'adressen_und_kontakt_handling: {0}'.format(err)
        
        if not mitgliedschaft:
            return 'Beim Adressen Update ist etwas schief gelaufen'
        
        if status_c in ('Online-Anmeldung', 'Online-Beitritt', 'Online-Kündigung'):
            mitgliedschaft.validierung_notwendig = 1
            if status_c == 'Online-Beitritt':
                if online_haftpflicht:
                    if int(online_haftpflicht) == 1:
                        mitgliedschaft.datum_hv_zahlung = eintritt
                mitgliedschaft.datum_zahlung_mitgliedschaft = eintritt
        else:
            if kwargs['needsValidation']:
                mitgliedschaft.validierung_notwendig = 1
                if status_c != 'Zuzug':
                    if status_vor_onl_mutation != 'Online-Mutation':
                        mitgliedschaft.status_vor_onl_mutation = status_vor_onl_mutation
                    change_log_row = mitgliedschaft.append('status_change', {})
                    change_log_row.datum = now()
                    change_log_row.status_alt = mitgliedschaft.status_c
                    change_log_row.status_neu = 'Online-Mutation'
                    change_log_row.grund = 'SP Update'
                    mitgliedschaft.status_c = 'Online-Mutation'
                
        
        # Zuzugsdatum-Fix bei Sektionswechsel von MVZH
        if mitgliedschaft.zuzug_von == 'MVZH' and mitgliedschaft.status_c == 'Zuzug':
            if not mitgliedschaft.zuzug:
                mitgliedschaft.zuzug = today()
        
        mitgliedschaft.flags.ignore_links=True
        try:
            mitgliedschaft.save()
            frappe.db.commit()
        except frappe.TimestampMismatchError as err:
            if not timestamp_mismatch_retry:
                frappe.log_error("{0}".format(kwargs), 'TimestampMismatchError: Retry')
                frappe.clear_messages()
                reloaded_mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
                mvm_update(reloaded_mitgliedschaft, kwargs, timestamp_mismatch_retry=True)
            else:
                return 'Internal Server Error: {0}'.format(err)
        
        # ACHTUNG: False == Positiv!
        return False
        
    except Exception as err:
        return 'Internal Server Error {0}'.format(err)

'''

'''
def adressen_und_kontakt_handling(new_mitgliedschaft, kwargs):
    mitglied = False
    objekt = False
    rechnung = False
    filiale = False
    mitbewohner = False
    zeitung = False
    
    for adresse in kwargs["adressen"]["adressenListe"]:
        adressen_dict = adresse
        
        if isinstance(adressen_dict, str):
            adressen_dict = json.loads(adressen_dict)
        
        if adressen_dict['typ'] == 'Filiale':
            filiale = adressen_dict
        elif adressen_dict['typ'] == 'Mitbewohner':
            mitbewohner = adressen_dict
        elif adressen_dict['typ'] == 'Zeitung':
            zeitung = adressen_dict
        elif adressen_dict['typ'] == 'Mitglied':
            mitglied = adressen_dict
        elif adressen_dict['typ'] == 'Objekt':
            objekt = adressen_dict
        elif adressen_dict['typ'] == 'Rechnung':
            rechnung = adressen_dict
        else:
            # unbekannter adresstyp
            frappe.log_error("{0}".format(adressen_dict), 'unbekannter adresstyp')
            return False
    
    if not mitglied:
        frappe.log_error("{0}".format(kwargs), 'adress/kontakt anlage: Keine mitglied Adresse')
        # muss zwingend vorhanden sein
        return False
    
    if mitglied:
        found_solidarmitglied = False
        # erfassung mitglied-daten
        for kontaktdaten in mitglied["kontakte"]:
            if kontaktdaten["istHauptkontakt"]:
                # hauptmiglied
                if not mitglied["strasse"] or str(mitglied["strasse"]) == '':
                    if not mitglied["postfach"]:
                        # eines von beidem muss zwingend vorhanden sein
                        frappe.log_error("{0}".format(kwargs), 'adress/kontakt anlage: Weder Postfach noch Strasse')
                        return False
                    else:
                        mitglied["strasse"] = 'Postfach'
                if kontaktdaten["firma"]:
                    new_mitgliedschaft.kundentyp = 'Unternehmen'
                    new_mitgliedschaft.firma = str(kontaktdaten["firma"])
                    new_mitgliedschaft.zusatz_firma = str(kontaktdaten["firmaZusatz"]) if kontaktdaten["firmaZusatz"] else ''
                else:
                    new_mitgliedschaft.kundentyp = 'Einzelperson'
                if kontaktdaten["anrede"] != 'Unbekannt':
                    new_mitgliedschaft.anrede_c = str(kontaktdaten["anrede"]) if kontaktdaten["anrede"] else ''
                new_mitgliedschaft.nachname_1 = str(kontaktdaten["nachname"]) if kontaktdaten["nachname"] else ''
                new_mitgliedschaft.vorname_1 = str(kontaktdaten["vorname"]) if kontaktdaten["vorname"] else ''
                new_mitgliedschaft.tel_p_1 = str(kontaktdaten["telefon"]) if kontaktdaten["telefon"] else ''
                if kontaktdaten["mobile"]:
                    if str(kontaktdaten["mobile"]) != str(kontaktdaten["telefon"]):
                        new_mitgliedschaft.tel_m_1 = str(kontaktdaten["mobile"])
                    else:
                        new_mitgliedschaft.tel_m_1 = ''
                else:
                    new_mitgliedschaft.tel_m_1 = ''
                new_mitgliedschaft.tel_g_1 = str(kontaktdaten["telefonGeschaeft"]) if kontaktdaten["telefonGeschaeft"] else ''
                new_mitgliedschaft.e_mail_1 = str(kontaktdaten["email"]) if check_email(kontaktdaten["email"]) else ''
                new_mitgliedschaft.zusatz_adresse = str(mitglied["adresszusatz"]) if mitglied["adresszusatz"] else ''
                new_mitgliedschaft.strasse = str(mitglied["strasse"]) if mitglied["strasse"] else ''
                new_mitgliedschaft.nummer = str(mitglied["hausnummer"]) if mitglied["hausnummer"] else ''
                new_mitgliedschaft.nummer_zu = str(mitglied["hausnummerZusatz"]) if mitglied["hausnummerZusatz"] else ''
                new_mitgliedschaft.postfach = 1 if mitglied["postfach"] else '0'
                new_mitgliedschaft.postfach_nummer = str(mitglied["postfachNummer"]) if mitglied["postfachNummer"] else ''
                new_mitgliedschaft.plz = str(mitglied["postleitzahl"]) if mitglied["postleitzahl"] else ''
                new_mitgliedschaft.ort = str(mitglied["ort"]) if mitglied["ort"] else ''
                if mitglied["fuerKorrespondenzGesperrt"]:
                    new_mitgliedschaft.adressen_gesperrt = 1
            else:
                # solidarmitglied
                found_solidarmitglied = True
                new_mitgliedschaft.hat_solidarmitglied = 1
                if kontaktdaten["anrede"] != 'Unbekannt':
                    new_mitgliedschaft.anrede_2 = str(kontaktdaten["anrede"]) if kontaktdaten["anrede"] else ''
                new_mitgliedschaft.nachname_2 = str(kontaktdaten["nachname"]) if kontaktdaten["nachname"] else ''
                new_mitgliedschaft.vorname_2 = str(kontaktdaten["vorname"]) if kontaktdaten["vorname"] else ''
                new_mitgliedschaft.tel_p_2 = str(kontaktdaten["telefon"]) if kontaktdaten["telefon"] else ''
                if kontaktdaten["mobile"]:
                    if str(kontaktdaten["mobile"]) != str(kontaktdaten["telefon"]):
                        new_mitgliedschaft.tel_m_2 = str(kontaktdaten["mobile"])
                    else:
                        new_mitgliedschaft.tel_m_2 = ''
                else:
                    new_mitgliedschaft.tel_m_2 = ''
                new_mitgliedschaft.tel_g_2 = str(kontaktdaten["telefonGeschaeft"]) if kontaktdaten["telefonGeschaeft"] else ''
                new_mitgliedschaft.e_mail_2 = str(kontaktdaten["email"]) if check_email(kontaktdaten["email"]) else ''
        
        if not found_solidarmitglied:
            new_mitgliedschaft.hat_solidarmitglied = 0
    
    if objekt:
        if objekt["strasse"]:
            new_mitgliedschaft.abweichende_objektadresse = 1
            new_mitgliedschaft.objekt_zusatz_adresse = str(objekt["adresszusatz"]) if objekt["adresszusatz"] else ''
            new_mitgliedschaft.objekt_strasse = str(objekt["strasse"]) if objekt["strasse"] else ''
            new_mitgliedschaft.objekt_hausnummer = str(objekt["hausnummer"]) if objekt["hausnummer"] else ''
            new_mitgliedschaft.objekt_nummer_zu = str(objekt["hausnummerZusatz"]) if objekt["hausnummerZusatz"] else ''
            new_mitgliedschaft.objekt_plz = str(objekt["postleitzahl"]) if objekt["postleitzahl"] else ''
            new_mitgliedschaft.objekt_ort = str(objekt["ort"]) if objekt["ort"] else ''
            if objekt["fuerKorrespondenzGesperrt"]:
                new_mitgliedschaft.adressen_gesperrt = 1
        else:
            frappe.log_error("Adressdaten:\n{0}\n\nMitgliedsdaten:\n{1}".format(objekt, kwargs), 'Adresse Typ Objekt: Wurde entfernt; fehlende Strasse')
            # reset objektadresse
            new_mitgliedschaft.abweichende_objektadresse = 0
            new_mitgliedschaft.objekt_zusatz_adresse = None
            new_mitgliedschaft.objekt_strasse = None
            new_mitgliedschaft.objekt_hausnummer = None
            new_mitgliedschaft.objekt_plz = None
            new_mitgliedschaft.objekt_ort = None
    else:
        # reset objektadresse
        new_mitgliedschaft.abweichende_objektadresse = 0
        new_mitgliedschaft.objekt_zusatz_adresse = None
        new_mitgliedschaft.objekt_strasse = None
        new_mitgliedschaft.objekt_hausnummer = None
        new_mitgliedschaft.objekt_plz = None
        new_mitgliedschaft.objekt_ort = None
    
    
    if rechnung:
        new_mitgliedschaft.abweichende_rechnungsadresse = 1
        new_mitgliedschaft.rg_zusatz_adresse = str(rechnung["adresszusatz"]) if rechnung["adresszusatz"] else ''
        new_mitgliedschaft.rg_strasse = str(rechnung["strasse"]) if rechnung["strasse"] else 'Postfach' if rechnung["postfach"] else ''
        new_mitgliedschaft.rg_nummer = str(rechnung["hausnummer"]) if rechnung["hausnummer"] else ''
        new_mitgliedschaft.rg_nummer_zu = str(rechnung["hausnummerZusatz"]) if rechnung["hausnummerZusatz"] else ''
        new_mitgliedschaft.rg_postfach = 1 if rechnung["postfach"] else '0'
        new_mitgliedschaft.rg_postfach_nummer = str(rechnung["postfachNummer"]) if rechnung["postfachNummer"] else ''
        new_mitgliedschaft.rg_plz = str(rechnung["postleitzahl"]) if rechnung["postleitzahl"] else ''
        new_mitgliedschaft.rg_ort = str(rechnung["ort"]) if rechnung["ort"] else ''
        
        if rechnung["fuerKorrespondenzGesperrt"]:
            new_mitgliedschaft.adressen_gesperrt = 1
        
        found_unabhaengiger_debitor = False
        
        for kontaktdaten in rechnung["kontakte"]:
            if kontaktdaten["istHauptkontakt"]:
                if (str(kontaktdaten["nachname"]) + str(kontaktdaten["vorname"])) != (new_mitgliedschaft.nachname_1 + new_mitgliedschaft.vorname_1):
                    # unabhängiger debitor
                    found_unabhaengiger_debitor = True
                    new_mitgliedschaft.unabhaengiger_debitor = 1
                    if kontaktdaten["firma"]:
                        new_mitgliedschaft.rg_kundentyp = 'Unternehmen'
                        new_mitgliedschaft.rg_firma = str(kontaktdaten["firma"])
                        new_mitgliedschaft.rg_zusatz_firma = str(kontaktdaten["firmaZusatz"]) if kontaktdaten["firmaZusatz"] else ''
                    else:
                        new_mitgliedschaft.rg_kundentyp = 'Einzelperson'
                    if kontaktdaten["anrede"] != 'Unbekannt':
                        new_mitgliedschaft.rg_anrede = str(kontaktdaten["anrede"]) if kontaktdaten["anrede"] else ''
                    new_mitgliedschaft.rg_nachname = str(kontaktdaten["nachname"]) if kontaktdaten["nachname"] else ''
                    new_mitgliedschaft.rg_vorname = str(kontaktdaten["vorname"]) if kontaktdaten["vorname"] else ''
                    new_mitgliedschaft.rg_tel_p = str(kontaktdaten["telefon"]) if kontaktdaten["telefon"] else ''
                    if kontaktdaten["mobile"]:
                        if str(kontaktdaten["mobile"]) != str(kontaktdaten["telefon"]):
                            new_mitgliedschaft.rg_tel_m = str(kontaktdaten["mobile"])
                        else:
                            new_mitgliedschaft.rg_tel_m = ''
                    else:
                        new_mitgliedschaft.rg_tel_m = ''
                    new_mitgliedschaft.rg_tel_g = str(kontaktdaten["telefonGeschaeft"]) if kontaktdaten["telefonGeschaeft"] else ''
                    new_mitgliedschaft.rg_e_mail = str(kontaktdaten["email"]) if check_email(kontaktdaten["email"]) else ''
        if not found_unabhaengiger_debitor:
            new_mitgliedschaft.unabhaengiger_debitor = 0
    else:
        new_mitgliedschaft.abweichende_rechnungsadresse = 0
    
    if zeitung:
        # manuelle erfassung zeitung
        frappe.log_error("Adressdaten:\n{0}\n\nMitgliedsdaten:\n{1}".format(zeitung, kwargs), 'Adresse Typ Zeitung: Manuelle Verarbeitung')
    
    if mitbewohner:
        # manuelle erfassung solidarmitglied
        frappe.log_error("Adressdaten:\n{0}\n\nMitgliedsdaten:\n{1}".format(mitbewohner, kwargs), 'Adresse Typ Mitbewohner: Manuelle Verarbeitung')
    
    if filiale:
        # manuelle erfassung filiale
        frappe.log_error("Adressdaten:\n{0}\n\nMitgliedsdaten:\n{1}".format(filiale, kwargs), 'Adresse Typ Filiale: Manuelle Verarbeitung')
    
    
    return new_mitgliedschaft

def check_immediately_executing(self, event):
    if cint(self.immediately_executing) == 1:
        service_plattform_log_worker()
    return

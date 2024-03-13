# -*- coding: utf-8 -*-
# Copyright (c) 2021-2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe.utils.data import getdate

def get_sektion_id(sektion_c):
    sektionen = frappe.db.sql("""SELECT `name` FROM `tabSektion` WHERE `sektion_c` = '{sektion_c}'""".format(sektion_c=sektion_c), as_dict=True)
    if len(sektionen) > 0:
        return sektionen[0].name
    else:
        return False

def get_status_c(status_c):
    mapper = {
        'Anmeldung': 'Anmeldung',
        'OnlineAnmeldung': 'Online-Anmeldung',
        'OnlineBeitritt': 'Online-Beitritt',
        'OnlineKuendigung': 'Online-Kündigung',
        'Zuzug': 'Zuzug',
        'Regulaer': 'Regulär',
        'Gestorben': 'Gestorben',
        'Kuendigung': 'Kündigung',
        'Wegzug': 'Wegzug',
        'Ausschluss': 'Ausschluss',
        'Inaktiv': 'Inaktiv',
        'InteressentIn': 'Interessent*in'
    }
    if status_c in mapper:
        return mapper[status_c]
    else:
        return False

def get_mitgliedtyp_c(mitgliedtyp_c):
    mapper = {
        'privat': 'Privat',
        'kollektiv': 'Kollektiv',
        'geschaeft': 'Geschäft',
        'Privat': 'Privat',
        'Kollektiv': 'Kollektiv',
        'Geschaeft': 'Geschäft'
    }
    if mitgliedtyp_c.lower() in mapper:
        return mapper[mitgliedtyp_c.lower()]
    else:
        return False

def get_inkl_hv(inkl_hv):
    curr_year = cint(getdate().strftime("%Y"))
    if inkl_hv:
        if cint(inkl_hv) >= curr_year:
            return 1
        else:
            return 0
    else:
        return 0

def get_sprache_abk(language='Deutsch'):
    language = frappe.db.sql("""SELECT `name` AS `lang` FROM `tabLanguage` WHERE `language_name` = '{language}'""".format(language=language), as_dict=True)
    if len(language) > 0:
        return language[0].lang
    else:
        return 'de'
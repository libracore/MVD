# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
from mvd.mvd.service_plattform.api import send_kampagne_to_sp
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import mitgliedschaft_zuweisen
import json

class Kampagne(Document):
    def before_insert(self):
        if not self.id:
            self.id = frappe.generate_hash(txt="", length=10)
        
        # Normalize newsletter_names to comma-separated string
        names = []

        if isinstance(self.newsletter_names, list):
            names = self.newsletter_names
        elif isinstance(self.newsletter_names, str):
            try:
                # Try to parse JSON string to list
                parsed = json.loads(self.newsletter_names)
                if isinstance(parsed, list):
                    names = parsed
                else:
                    names = self.newsletter_names.split(",")
            except Exception:
                # fallback: assume comma-separated
                names = self.newsletter_names.split(",")

        cleaned_list = [n.strip().replace(" ", "") for n in names if isinstance(n, str)]
        self.newsletter_names = ",".join(cleaned_list)

    def after_insert(self):
        """
        Versuche dem Kampagnen Eintrag eine Mitgliedschaft zuzuordnen über 
            - den Mitglied Hash
            - die Email
        Über die PLZ wird immer eine Sektion zugeordnet
        """
        email = self.email 
        mitglied_hash = self.mitglied_hash
        zip_code = self.zip_code

        mitglied_info = mitgliedschaft_zuweisen(email=email, mitglied_hash=mitglied_hash, zip_code=zip_code)

        if mitglied_info:
            if isinstance(mitglied_info, tuple):
                self.mitglied_id = mitglied_info[0]
                if not self.sektion_id:
                    self.sektion_id = mitglied_info[1]
            elif isinstance(mitglied_info, str) and not self.sektion_id:
                self.sektion_id = mitglied_info
                
            self.save(ignore_permissions=True)

        if cint(frappe.db.get_value("MVD Settings", "MVD Settings", "suspend_kampagne_to_sp")) != 1 \
           and self.email and self.campaign_trigger_code and self.newsletter_names:
                    # Send to emarsis
            sp_data = {
                "Email": self.email or None,
                "NewsletterNames": self.newsletter_names.split(","),
                "CampaignTriggerCode": str(self.campaign_trigger_code),
                "SubscribedOverPledge": False if cint(self.subscribed_over_pledge) != 1 else True,
                "Zip_code": self.zip_code or 0,
                "Last_name": self.last_name or None,
                "First_name": self.first_name or None,
                "Anrede": self.anrede or None,
                "LangCode": self.lang_code or "de",
                "Nl_abo": False if cint(self.nl_abo) != 1 else True,
                "Quelle": self.quelle or None
            }
            send_kampagne_to_sp(sp_data, id=self.name)

@frappe.whitelist()
def erweiterte_zuordnung():
    """
    Versucht, alle Kampagnen ohne zugeordnetes Mitglied anhand des Falls
    (Vorname, Nachname, Strasse, PLZ) automatisch einer Mitgliedschaft zuzuordnen.
    Das wird nicht beim insert gemacht, weil es rechenintensiv ist!
    Aktualisiert die Felder 'mitglied' und 'sektion_id', falls ein eindeutiges Match gefunden wird.
    """
    assigned = 0
    # Nur Kampagnen ohne Mitglied abrufen
    kampagnen = frappe.get_all(
        "Kampagne",
        filters={"mitglied": ["is", "not set"]},
        fields=[
            "name", "email", "mitglied_hash", "zip_code",
            "last_name", "first_name", "strasse", "ort", "strasse_nummer"
        ]
    )
    total = len(kampagnen)
    for k in kampagnen:
        # Nur der neue Fall: Name + PLZ + Strasse
        if k.first_name and k.last_name and k.strasse and k.zip_code:
            mitglied_info = mitgliedschaft_zuweisen(
                zip_code=k.zip_code,
                last_name=k.last_name,
                first_name=k.first_name,
                strasse=k.strasse
            )

            if mitglied_info:
                if isinstance(mitglied_info, tuple):
                    mitglied_id, sektion_id = mitglied_info
                    frappe.db.set_value("Kampagne", k.name, "mitglied", mitglied_id)
                    frappe.db.set_value("Kampagne", k.name, "sektion_id", sektion_id)
                    assigned += 1

    frappe.db.commit()
    return {
        "total": total,
        "assigned": assigned
    }
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from mvd.mvd.doctype.rechnungsbereinigung.rechnungsbereinigung import (
    BUSY, CASE, INTERNAL, _clear_approval, _protect_fields, _run, _same_value)


class RechnungsbereinigungFall(Document):
    def validate(self):
        if self.flags.get('interne_bereinigung') is INTERNAL:
            return
        if self.is_new():
            frappe.throw('Bereinigungsfälle werden ausschliesslich durch einen Prüflauf erstellt.')
        previous = self.get_doc_before_save()
        if previous:
            _protect_fields(self, previous, ('ersatzrechnung', 'notizen'))
            run = _run(self.prueflauf, lock=True)
            if run.status in BUSY:
                frappe.throw('Dieser Prüflauf wird gerade verarbeitet. Änderungen sind vorübergehend gesperrt.')
            modified = frappe.db.get_value(CASE, self.name, 'modified')
            if not _same_value(modified, previous.modified):
                frappe.throw('Der Fall wurde inzwischen geändert. Bitte neu laden.')
            if self.ersatzrechnung != previous.ersatzrechnung:
                if previous.status == 'Bereinigt':
                    frappe.throw('Die Ersatzrechnung kann während oder nach der Bereinigung nicht geändert werden.')
                self.update(_clear_approval())
                self.status = 'Offen'
                self.pruefhinweis = 'Ersatzrechnung geändert. Bitte erneut prüfen und freigeben.'

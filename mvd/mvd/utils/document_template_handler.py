# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import io
from odf.opendocument import load
from odf.text import P, H, Span
from pathlib import Path
from frappe.utils.file_manager import save_file
import json

@frappe.whitelist()
def use_template(template=None, replacements=None, source_doc=None, source_dt=None, test=False):
    if not template:
        frappe.throw("Es wird eine Dokumentenvorlage benötigt.")
    else:
        if not frappe.db.exists("Dokumentenvorlage", template):
            frappe.throw("Die Dokumentenvorlage '{0}' existiert nicht!".format(template))
    
    temp = frappe.get_doc("Dokumentenvorlage", template)
    if source_dt:
        source_doc = frappe.get_doc(source_dt, source_doc)

    if replacements is None:
        replacements = temp.get_placeholder_values(source_doc) if source_doc else {}

    # Falls von Client (String) --> parsen
    if isinstance(replacements, str):
        try:
            replacements = json.loads(replacements)
        except json.JSONDecodeError:
            frappe.throw("replacements ist kein gültiges JSON")
    
    file_path = False
    bench_path = frappe.utils.get_bench_path()
    site_name = frappe.local.site
    
    if temp.file_base == 'Anhang':
        attachment = frappe.db.sql(
            """
                SELECT `file_url`
                FROM `tabFile`
                WHERE `attached_to_doctype` = 'Dokumentenvorlage'
                AND `attached_to_name` = '{0}'
                LIMIT 1
            """.format(template),
            as_dict=True
        )
        if len(attachment) > 0:
            attm = attachment[0].file_url
        else:
            frappe.throw("Die Dokumentenvorlage besitzt kein Attachment!")
        
        file_path = "{0}/sites/{1}{2}".format(bench_path, site_name, attm)
    
    if temp.file_base == 'ERPNext':
        file_path = "{0}/sites/{1}{2}".format(bench_path, site_name, temp.file_path)
    
    if temp.file_base == 'Nextcloud':
        frappe.throw("Diese Funktionalität muss noch ausgebaut werden...")
    
    if file_path:
        replace_in_odt(file_path, "/tmp/Test.odt", replacements, test, template, source_doc)

def replace_in_text_node(node, replacements: dict[str, str]) -> None:
    if hasattr(node, "data") and isinstance(node.data, str):
        text = node.data
        for old, new in replacements.items():
            text = text.replace(old, new or old)
        node.data = text

    if hasattr(node, "childNodes"):
        for child in node.childNodes:
            replace_in_text_node(child, replacements)


def replace_in_odt(input_file: str, output_file: str, replacements: dict[str, str], test: bool, template: str, source_doc: dict[str, str]) -> None:
    """
    Ersetzt Wörter/Textstellen in einer .odt-Datei und speichert das Ergebnis.
    """
    doc = load(input_file)
    
    # Durch alle relevanten Elemente loopen und entsprechend replacements ersetzen
    for elem in doc.getElementsByType(P):
        replace_in_text_node(elem, replacements)

    for elem in doc.getElementsByType(H):
        replace_in_text_node(elem, replacements)

    for elem in doc.getElementsByType(Span):
        replace_in_text_node(elem, replacements)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    file_doc = save_file(
        fname="verarbeitete_vorlage.odt",
        content=buffer.getvalue(),
        dt="Dokumentenvorlage" if test else source_doc.doctype,
        dn=template if test else source_doc.name,
        is_private=1
    )
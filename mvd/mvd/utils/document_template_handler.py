# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
import io
import json
from odf.opendocument import load
from odf.text import P, H
from odf import draw
from frappe.utils.file_manager import save_file


@frappe.whitelist()
def use_template(template=None, replacements=None, source_doc=None, source_dt=None,
                 save_output_to=[], filename=None, test=False):

    if not template:
        frappe.throw("Es wird eine Dokumentenvorlage benötigt.")

    if not frappe.db.exists("Dokumentenvorlage", template):
        frappe.throw("Die Dokumentenvorlage '{0}' existiert nicht!".format(template))

    temp = frappe.get_doc("Dokumentenvorlage", template)

    if source_dt:
        source_doc = frappe.get_doc(source_dt, source_doc)

    if replacements is None:
        replacements = temp.get_placeholder_values(source_doc) if source_doc else {}

    if isinstance(replacements, str):
        try:
            replacements = json.loads(replacements)
        except json.JSONDecodeError:
            frappe.throw("replacements ist kein gültiges JSON")

    if isinstance(save_output_to, str):
        try:
            save_output_to = json.loads(save_output_to)
        except json.JSONDecodeError:
            frappe.throw("save_output_to ist kein gültiges JSON")

    bench_path = frappe.utils.get_bench_path()
    site_name = frappe.local.site
    file_path = False

    if temp.file_base == "Anhang":
        attachment = frappe.db.sql("""
            SELECT `file_url`
            FROM `tabFile`
            WHERE `attached_to_doctype` = 'Dokumentenvorlage'
            AND `attached_to_name` = %s
            LIMIT 1
        """, template, as_dict=True)

        if not attachment:
            frappe.throw("Die Dokumentenvorlage besitzt kein Attachment!")

        file_path = "{0}/sites/{1}{2}".format(
            bench_path,
            site_name,
            attachment[0].file_url
        )

    elif temp.file_base == "ERPNext":
        file_path = "{0}/sites/{1}{2}".format(
            bench_path,
            site_name,
            temp.file_path
        )

    elif temp.file_base == "Nextcloud":
        frappe.throw("Diese Funktionalität muss noch ausgebaut werden...")

    if file_path:
        replace_in_odt(
            input_file=file_path,
            replacements=replacements,
            test=test,
            template=template,
            source_doc=source_doc,
            save_output_to=save_output_to,
            filename=filename or "verarbeitete_vorlage.odt"
        )


def normalize_replacement(value):
    """
    Unterstützt folgende Platzhalter-Schemas:
    "Platzhalter_1": "Text"
    "Platzhalter_2": ["txt", "Text"]
    "Platzhalter_3": ["img", png_bytes]
    """

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return value[0], value[1]

    return "txt", value


def replace_in_text_node(node, replacements) -> None:
    if hasattr(node, "data") and isinstance(node.data, str):
        text = node.data

        for old, raw_value in replacements.items():
            replacement_type, value = normalize_replacement(raw_value)

            if replacement_type == "txt":
                text = text.replace(
                    old,
                    str(value) if value is not None else old
                )

        node.data = text

    if hasattr(node, "childNodes"):
        for child in node.childNodes:
            replace_in_text_node(child, replacements)


def replace_named_image(doc, image_name, png_bytes):
    """
    Ersetzt ein bestehendes Dummy-Bild im ODT anhand des Frame-Namens

    Im ODT:
    Rechtsklick auf Dummy-Bild > Eigenschaften > Name = z.B. dmc_platzhalter

    Replacement:
    "dmc_platzhalter": ["img", png_bytes]
    """

    for frame in doc.getElementsByType(draw.Frame):
        if frame.getAttribute("name") != image_name:
            continue

        href = doc.addPictureFromString(
            png_bytes,
            "image/png"
        )

        images = frame.getElementsByType(draw.Image)

        if images:
            images[0].setAttribute("href", href)
        else:
            image = draw.Image(
                href=href,
                type="simple",
                show="embed",
                actuate="onLoad"
            )
            frame.addElement(image)

        return True

    return False


def replace_images(doc, replacements):
    for old, raw_value in replacements.items():
        replacement_type, value = normalize_replacement(raw_value)

        if replacement_type != "img":
            continue

        image_name = old
        replaced = replace_named_image(doc, image_name, value)

        if not replaced:
            frappe.log_error(
                "Bildplatzhalter nicht gefunden: {0}".format(image_name),
                "ODT Template Image Replacement"
            )


def replace_texts(doc, replacements):
    for elem in doc.getElementsByType(P):
        replace_in_text_node(elem, replacements)

    for elem in doc.getElementsByType(H):
        replace_in_text_node(elem, replacements)


def replace_in_odt(input_file: str, replacements: dict, test: bool,
                   template: str, source_doc, save_output_to: list,
                   filename: str = "verarbeitete_vorlage.odt") -> None:

    doc = load(input_file)

    # Dummy-Bilder ersetzen
    replace_images(doc, replacements)

    # Textplatzhalter ersetzen
    replace_texts(doc, replacements)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    if save_output_to:
        for save_location in save_output_to:
            save_file(
                fname=filename if filename.endswith(".odt") else "{0}.odt".format(filename),
                content=buffer.getvalue(),
                dt=save_location[0],
                dn=save_location[1],
                is_private=1
            )
    else:
        save_file(
            fname=filename if filename.endswith(".odt") else "{0}.odt".format(filename),
            content=buffer.getvalue(),
            dt="Dokumentenvorlage" if test else source_doc.doctype,
            dn=template if test else source_doc.name,
            is_private=1
        )
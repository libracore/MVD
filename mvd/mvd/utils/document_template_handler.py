# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import io
import json
import hashlib
from PIL import Image, UnidentifiedImageError
from odf.opendocument import load
from odf.text import P, H
from odf import draw
from frappe.utils.file_manager import save_file
from urllib.parse import unquote


DUMMY_IMAGE_HASHES = {
    "dmc_platzhalter": frappe.get_value(
        "MVD Settings",
        "MVD Settings",
        "dmc_platzhalter_img_hash"
    ) or "a4ed9825cf1733f67a7608b3d6847396d9c069e6e333dde6064742a802b35cff"
}


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
            AND `attached_to_name` = '{0}'
            LIMIT 1
        """.format(template), as_dict=True)

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

def get_normalized_pixel_hash(image_bytes, normalized_size=(128, 128)):
    """
    Erstellt einen grössenunabhängigen SHA-256-Hash aus den Bildpixeln.
    Das Bild wird vor dem Hashen auf 128 x 128 Pixel normalisiert.
    """

    with Image.open(io.BytesIO(image_bytes)) as image:
        image.load()
        image = image.convert("RGBA")

        # Transparenz auf einen weissen Hintergrund reduzieren.
        background = Image.new(
            "RGBA",
            image.size,
            (255, 255, 255, 255)
        )

        normalized_image = Image.alpha_composite(
            background,
            image
        ).convert("RGB")

        # Kompatibel mit alten und neuen Pillow-Versionen.
        try:
            resize_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resize_filter = Image.LANCZOS

        normalized_image = normalized_image.resize(
            normalized_size,
            resize_filter
        )

        return hashlib.sha256(
            normalized_image.tobytes()
        ).hexdigest()


def get_embedded_image_bytes(doc, image_href):
    """
    Liest die Bytes eines eingebetteten ODT-Bildes aus doc.Pictures
    """

    if not image_href:
        return None

    image_path = unquote(image_href)

    while image_path.startswith("./"):
        image_path = image_path[2:]

    possible_paths = [
        image_path,
        "./{0}".format(image_path),
        "/{0}".format(image_path.lstrip("/"))
    ]

    embedded_picture = None

    for possible_path in possible_paths:
        if possible_path in doc.Pictures:
            embedded_picture = doc.Pictures[possible_path]
            break

    if embedded_picture is None:
        return None

    if isinstance(embedded_picture, bytes):
        return embedded_picture

    if isinstance(embedded_picture, bytearray):
        return bytes(embedded_picture)

    if isinstance(embedded_picture, tuple):
        if len(embedded_picture) >= 2:
            image_data = embedded_picture[1]

            if isinstance(image_data, bytes):
                return image_data

            if isinstance(image_data, bytearray):
                return bytes(image_data)

    return None


def replace_image_in_frame(doc, frame, png_bytes):
    """
    Ersetzt das Bild innerhalb eines bestehenden ODT-Frames.
    Die Grösse, Position und Verankerung des Frames bleiben erhalten.
    """

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

def replace_image_element(doc, image, png_bytes):
    """
    Ersetzt exakt das übergebene draw:image-Element
    """

    new_href = doc.addPictureFromString(
        png_bytes,
        "image/png"
    )

    image.setAttribute("href", new_href)

    return True

def replace_named_image(doc, image_name, png_bytes):
    """
    Ersetzt alle Vorkommen eines Dummy-Bildes im ODT

    Das Bild wird erkannt:
    1. über den Frame-Namen, z.B. bei LibreOffice
    2. über den normalisierten Pixel-Hash, z.B. bei ONLYOFFICE

    Es werden bewusst alle Treffer ersetzt, weil dasselbe Bild in einem ODT
    mehrfach vorkommen kann, beispielsweise in verschiedenen Masterseiten
    oder Fusszeilen
    """

    frames = doc.getElementsByType(draw.Frame)
    replaced_count = 0

    # 1. Alle Frames mit passendem Namen ersetzen
    for frame in frames:
        if frame.getAttribute("name") != image_name:
            continue

        replace_image_in_frame(
            doc=doc,
            frame=frame,
            png_bytes=png_bytes
        )

        replaced_count += 1

    # Wenn mindestens ein benannter Frame gefunden wurde,
    # ist keine Hash-Suche mehr notwendig.
    if replaced_count > 0:
        return replaced_count

    # 2. Alle Bilder mit passendem Pixel-Hash ersetzen
    expected_dummy_hash = DUMMY_IMAGE_HASHES.get(image_name)

    if not expected_dummy_hash:
        return 0

    for frame in frames:
        images = frame.getElementsByType(draw.Image)

        if not images:
            continue

        for image in images:
            image_href = image.getAttribute("href")

            embedded_image_bytes = get_embedded_image_bytes(
                doc=doc,
                image_href=image_href
            )

            if not embedded_image_bytes:
                continue

            try:
                embedded_image_hash = get_normalized_pixel_hash(
                    embedded_image_bytes
                )

            except (UnidentifiedImageError, OSError):
                continue

            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    "ODT Dummy Image Pixel Hash"
                )
                continue

            if embedded_image_hash != expected_dummy_hash:
                continue

            replace_image_element(
                doc=doc,
                image=image,
                png_bytes=png_bytes
            )

            replaced_count += 1

    return replaced_count


def replace_images(doc, replacements):
    """
    Ersetzt alle Bild-Platzhalter aus replacements
    """

    for old, raw_value in replacements.items():
        replacement_type, value = normalize_replacement(raw_value)

        if replacement_type != "img":
            continue
        
        image_name = old

        replaced_count = replace_named_image(
            doc=doc,
            image_name=image_name,
            png_bytes=value
        )

        if replaced_count == 0:
            frappe.log_error(
                (
                    "Bildplatzhalter nicht gefunden: {0}\n"
                    "Frame-Name geprüft: ja\n"
                    "Dummy-Pixel-Hash vorhanden: {1}"
                ).format(
                    image_name,
                    "ja" if DUMMY_IMAGE_HASHES.get(image_name) else "nein"
                ),
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
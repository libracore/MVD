# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import now
from frappe.utils.background_jobs import enqueue
import json
import csv
import io

class WebFormular(Document):
    def before_save(self):
        fieldname = "form_data"  # your Code field
        value = getattr(self, fieldname, None)
        if value:
            try:
                parsed = json.loads(value)
                setattr(self, fieldname, json.dumps(parsed, indent=2))
            except Exception as e:
                # optional: log invalid JSON
                frappe.log_error("Invalid JSON in {0}: {1}".format(fieldname, e))

@frappe.whitelist()
def export_form_data_as_csv(form_id, webformular):
    args = {
        'form_id': form_id,
        'webformular': webformular
    }
    enqueue("mvd.mvd.doctype.webformular.webformular._export_form_data_as_csv", queue='long', job_name='Export WebFormular JSON as CSV', timeout=5000, **args)
    return

def _export_form_data_as_csv(form_id, webformular):
    """Return CSV string of all form_data rows for given form_id."""
    records = frappe.get_all(
        "WebFormular",
        filters={"form_id": form_id},
        fields=["form_data", "entry_id", "creation", "form_id"],
        order_by="creation desc"
    )

    if not records:
        return ""

    # 1. Parse all JSON rows first
    parsed_rows = []
    all_keys = []
    seen_keys = set()
    for row in records:
        try:
            data = json.loads(row.form_data)
            flat = flatten_dict(data)

            # system fields first
            for sys_field in ["form_id", "entry_id", "creation"]:
                if sys_field not in seen_keys:
                    all_keys.append(sys_field)
                    seen_keys.add(sys_field)

            for k in flat.keys():
                if k not in seen_keys:
                    all_keys.append(k)
                    seen_keys.add(k)
            flat["form_id"] = row.form_id
            flat["entry_id"] = row.entry_id
            flat["creation"] = row.creation
            parsed_rows.append(flat)
        except Exception as e:
            frappe.log_error(f"CSV export failed for entry {row.entry_id}: {e}")

    # 2. Create CSV with full header (union of all keys)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_keys)
    writer.writeheader()
    for row in parsed_rows:
        writer.writerow(row)

    # 3. Save CSV as File and attach to WebFormual Record
    file_name = "WebFormular_{datetime}.csv".format(datetime=now().replace(" ", "_"))
    csv_content = output.getvalue()
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "folder": "Home/Attachments",
        "is_private": 1,
        "content": csv_content,
        "attached_to_doctype": 'WebFormular',
        "attached_to_name": webformular

    })
    
    _file.save()


def flatten_dict(d, parent_key="", sep="."):
    """Flatten nested dict into dot notation (for CSV)."""
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key, sep=sep))
        elif isinstance(v, list):
            items[new_key] = json.dumps(v)  # keep list as JSON string
        else:
            items[new_key] = v
    return items
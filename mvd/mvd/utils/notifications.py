# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt
import frappe

def get_notification_config():
    return {
        "for_doctype": {
            "Arbeits Backlog": {"status": 'Open'},
            "Sales Invoice": {"posting_date": "1900-01-01"}
        }
    }

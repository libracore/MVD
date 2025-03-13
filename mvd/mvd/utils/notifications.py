# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt
import frappe

def get_notification_config():
    return {
        "for_doctype": {
            "Arbeits Backlog": {"status": 'Open'},
            "Sales Invoice": {"posting_date": "1900-01-01"}
        },
        "for_other": {
            "Email": "mvd.mvd.utils.notifications.get_zero_to_hide"
        }
    }

def get_zero_to_hide():
    return 0
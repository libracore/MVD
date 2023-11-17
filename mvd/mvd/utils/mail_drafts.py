# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def save_draft_mail(doctype_reference=None, docname=None, mail=None, user=None):
    try:
        existing_test = frappe.db.exists({
            'doctype': 'Email Drafts',
            'doctype_reference': doctype_reference,
            'docname': docname,
            'user': user
        })
        if existing_test:
            draft_mail = frappe.get_doc('Email Drafts', existing_test[0][0])
            draft_mail.mail = mail
            draft_mail.save(ignore_permissions=True)
        else:
            draft_mail = frappe.get_doc({
                'doctype': 'Email Drafts',
                'doctype_reference': doctype_reference,
                'docname': docname,
                'mail': mail,
                'user': user
            }).save(ignore_permissions=True)
    except Exception as err:
        frappe.log_error("{0}".format(err), 'save_draft_mail')

@frappe.whitelist()
def load_draft_mail(doctype_reference=None, docname=None, user=None):
    try:
        existing_test = frappe.db.exists({
            'doctype': 'Email Drafts',
            'doctype_reference': doctype_reference,
            'docname': docname,
            'user': user
        })
        if existing_test:
            draft_mail = frappe.get_doc('Email Drafts', existing_test[0][0])
            mail = draft_mail.mail
            draft_mail.delete()
            return mail
    except Exception as err:
        frappe.log_error("{0}".format(err), 'load_draft_mail')

@frappe.whitelist()
def delete_draft_mail(doctype_reference=None, docname=None, user=None):
    try:
        existing_test = frappe.db.exists({
            'doctype': 'Email Drafts',
            'doctype_reference': doctype_reference,
            'docname': docname,
            'user': user
        })
        if existing_test:
            draft_mail = frappe.get_doc('Email Drafts', existing_test[0][0])
            draft_mail.delete()
    except Exception as err:
        frappe.log_error("{0}".format(err), 'delete_draft_mail')

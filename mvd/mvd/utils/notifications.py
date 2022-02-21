# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt
import frappe

def get_notification_config():
    return {
        "for_doctype": {
            "Arbeits Backlog": {"status": 'Open'}
        }
    }

def get_todo_permission_query_conditions(user):
    allowed_sektionen = frappe.get_list('Sektion', fields=['virtueller_user'])
    
    todo_users = [user or frappe.session.user]
    for virt_user in allowed_sektionen:
        todo_users.append(virt_user['virtueller_user'])

    if "System Manager" in frappe.get_roles(user):
        return None
    else:
        if allowed_sektionen:
            return """(`tabToDo`.owner IN {user} or `tabToDo`.assigned_by IN {user})"""\
                .format(user=tuple(todo_users))
        else:
            None

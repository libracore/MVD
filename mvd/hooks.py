# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "mvd"
app_title = "MVD"
app_publisher = "libracore"
app_description = "MVD"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@libracore.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/mvd/css/mvd.css"
app_include_js = "/assets/mvd/js/mvd.js"

# include js, css files in header of web template
# web_include_css = "/assets/mvd/css/mvd.css"
# web_include_js = "/assets/mvd/js/mvd.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Address" : "public/js/custom_scripts/address.js",
    "Sales Invoice" : "public/js/custom_scripts/sales_invoice.js",
    "User" : "public/js/custom_scripts/user.js",
    "Role" : "public/js/custom_scripts/role.js",
    "Payment Entry" : "public/js/custom_scripts/payment_entry.js"
}
doctype_list_js = {
    "Error Log" : "public/js/custom_scripts/error_log_list.js",
    "Payment Entry" : "public/js/custom_scripts/payment_entry_list.js"
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

jenv = {
    "methods": [
        "get_anredekonvention:mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_anredekonvention",
        "replace_mv_keywords:mvd.mvd.doctype.druckvorlage.druckvorlage.replace_mv_keywords",
        "get_mahnungs_qrrs:mvd.mvd.doctype.mahnung.mahnung.get_mahnungs_qrrs",
        "get_rg_adressblock:mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_rg_adressblock"
    ]
}
# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "mvd.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "mvd.install.before_install"
# after_install = "mvd.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "mvd.notifications.get_notification_config"
notification_config = "mvd.mvd.utils.notifications.get_notification_config"

extend_bootinfo = "mvd.mvd.utils.mvd_bootinfo.boot_session"

# Permissions
# -----------
# Permissions evaluated in scripted ways
# ~ has_permission = {
    # ~ "ToDo": "mvd.mvd.utils.hook_utils.todo_permissions"
# ~ }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Sales Invoice": {
        "on_update": "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.sinv_check_zahlung_mitgliedschaft",
        "on_update_after_submit": "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.sinv_check_zahlung_mitgliedschaft",
        "on_cancel": "mvd.mvd.utils.hook_utils.resave_mitgliedschaft",
        "before_cancel": "mvd.mvd.utils.hook_utils.unlink_fr",
        "after_insert": "mvd.mvd.utils.hook_utils.relink_fr"
    },
    "Payment Entry": {
        "on_submit": ["mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.pe_check_zahlung_mitgliedschaft", "mvd.mvd.utils.hook_utils.check_mitgliedschaft_in_pe"]
    },
    "ToDo": {
        "on_update": "mvd.mvd.utils.hook_utils.todo_permissions"
    },
    "Address": {
        "on_update": "mvd.mvd.doctype.retouren.retouren.check_dates"
    }
}

# Scheduled Tasks
# ---------------
scheduler_events = {
    "daily": [
        "mvd.mvd.utils.daily_jobs.set_inaktiv",
        "mvd.mvd.utils.daily_jobs.entferne_alte_reduzierungen",
        "mvd.mvd.utils.daily_jobs.ampel_neuberechnung",
        "mvd.mvd.utils.daily_jobs.regionen_zuteilung",
        "mvd.mvd.utils.daily_jobs.spenden_versand",
        "mvd.mvd.utils.daily_jobs.rechnungs_jahresversand"
    ],
    "all": [
        "mvd.mvd.doctype.service_platform_queue.service_platform_queue.flush_queue"
    ]
}
# scheduler_events = {
# 	"all": [
# 		"mvd.tasks.all"
# 	],
# 	"daily": [
# 		"mvd.tasks.daily"
# 	],
# 	"hourly": [
# 		"mvd.tasks.hourly"
# 	],
# 	"weekly": [
# 		"mvd.tasks.weekly"
# 	]
# 	"monthly": [
# 		"mvd.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "mvd.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "mvd.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "mvd.task.get_dashboard_data"
# }

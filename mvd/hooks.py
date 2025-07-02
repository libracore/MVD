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
web_include_js = "/assets/mvd/js/mvd_web.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Address" : "public/js/custom_scripts/address.js",
    "Sales Invoice" : "public/js/custom_scripts/sales_invoice.js",
    "User" : "public/js/custom_scripts/user.js",
    "Role" : "public/js/custom_scripts/role.js",
    "Payment Entry" : "public/js/custom_scripts/payment_entry.js",
    "Communication" : "public/js/custom_scripts/communication.js",
    "Issue" : "public/js/custom_scripts/issue.js"
}
doctype_list_js = {
    "Error Log" : "public/js/custom_scripts/error_log_list.js",
    "Payment Entry" : "public/js/custom_scripts/payment_entry_list.js"
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

jenv = {
    "methods": [
        "get_anredekonvention:mvd.mvd.doctype.mitgliedschaft.utils.get_anredekonvention",
        "replace_mv_keywords:mvd.mvd.doctype.druckvorlage.druckvorlage.replace_mv_keywords",
        "get_mahnungs_qrrs:mvd.mvd.doctype.mahnung.mahnung.get_mahnungs_qrrs",
        "get_rg_adressblock:mvd.mvd.doctype.mitgliedschaft.utils.get_rg_adressblock",
        "get_last_open_sinv:mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_last_open_sinv"
    ]
}

# allow to link incoming mails to Beratung
email_append_to = ["Beratung"]

website_redirects = [
    # absolute location
    {"source": "/nologin", "target": "https://www.mieterverband.ch/mv/prozesse/login.html"},
    {"source": "/mvd-500", "target": "https://www.mieterverband.ch/mv/500"},
    {"source": "/mvd-mvso", "target": "https://www.mieterverband.ch/mv-so/hilfe-von-fachleuten/email-beratung"},
    {"source": "/", "target": "https://www.mieterverband.ch/"}
]

# Home Pages
# ----------

# application home page (will override Website Settings)
home_page = "redirect"

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

on_login = "mvd.mvd.utils.mvd_bootinfo.login_check"

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
        "before_cancel": "mvd.mvd.utils.hook_utils.unlink_fr",
        "after_insert": "mvd.mvd.utils.hook_utils.relink_fr",
        "on_change": "mvd.mvd.doctype.mitgliedschaft.finance_utils.sinv_update",
        "validate": "mvd.mvd.utils.hook_utils.check_manual_address"
    },
    "Payment Entry": {
        "on_submit": "mvd.mvd.doctype.mitgliedschaft.finance_utils.check_mitgliedschaft_in_pe"
    },
    "ToDo": {
        "on_update": "mvd.mvd.utils.hook_utils.todo_permissions"
    },
    "Address": {
        "on_update": "mvd.mvd.doctype.retouren.retouren.check_dates"
    },
    "Communication": {
        "after_insert": "mvd.mvd.doctype.beratung.beratung.check_communication"
    },
    "File": {
        "after_insert": "mvd.mvd.doctype.beratung.beratung.sync_mail_attachements",
        "after_delete": "mvd.mvd.doctype.beratung.beratung.sync_attachments_and_beratungs_table"
    },
    "Beratung": {
        "on_update": "mvd.mvd.doctype.beratung.beratung.sync_attachments_and_beratungs_table"
    },
    "Email Queue": {
        "after_insert": "mvd.mvd.utils.hook_utils.remove_admin_and_guest_mails"
    },
    "Service Plattform Log": {
        "after_insert": "mvd.mvd.service_plattform.request_worker.check_immediately_executing"
    }
}

# Scheduled Tasks
# ---------------
scheduler_events = {
    "daily": [
        "mvd.mvd.utils.daily_jobs.create_daily_snap",
        "mvd.mvd.utils.daily_jobs.reset_geschenk_mitgliedschaften",
        "mvd.mvd.utils.daily_jobs.set_inaktiv",
        "mvd.mvd.utils.daily_jobs.entferne_alte_reduzierungen",
        "mvd.mvd.utils.daily_jobs.ampel_neuberechnung",
        "mvd.mvd.utils.daily_jobs.regionen_zuteilung",
        "mvd.mvd.utils.daily_jobs.spenden_versand",
        "mvd.mvd.utils.daily_jobs.mahnlauf_ausschluss",
        "mvd.mvd.utils.daily_jobs.cleanup_beratungen",
        "mvd.mvd.utils.daily_jobs.mark_beratungen_as_s8",
        #"mvd.mvd.doctype.mitgliedschaft.kontakt_handling.initial_rename_contacts",
        "mvd.mvd.doctype.postretouren_log.postretouren_log.start_post_retouren_process",
        "mvd.mvd.utils.daily_jobs.rechnungs_jahresversand",
        "mvd.mvd.utils.daily_jobs.daily_ampel_korrektur"
    ],
    "all": [
        "mvd.mvd.doctype.service_platform_queue.service_platform_queue.flush_queue",
        "mvd.mvd.doctype.mvd_email_queue.mvd_email_queue.mvd_mail_flush",
        "mvd.www.emailberatung.send_to_sp",
        "mvd.mvd.service_plattform.request_worker.service_plattform_log_worker",
        "mvd.mvd.doctype.serien_email.serien_email.send_mails"
    ],
    "hourly": [
        "mvd.mvd.doctype.wohnungsabgabe.wohnungsabgabe.qa_mail"
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

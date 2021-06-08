from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Mitgliederverwaltung"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "MV Mitgliedschaft",
					"label": _("MV Mitgliedschaft"),
					"description": _("MV Mitgliedschaft")
				},
				{
					"type": "doctype",
					"name": "Customer",
					"label": _("Kunden"),
					"description": _("Customers")
				}
			]
		}
	]

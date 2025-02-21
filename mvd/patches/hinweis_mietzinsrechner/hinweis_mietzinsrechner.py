import frappe

def execute():
    try:
        print("Kopiere hinweis_mietzinsrecher in hinweis_mietzinsrechner_erhoehung und hinweis_mietzinsrechner_senkung")
        frappe.reload_doc("mvd", "doctype", "Sektion") # reload Sektion doctype damit es ready ist.
        frappe.db.sql("""UPDATE tabSektion ts set hinweis_mietzinsrechner_erhoehung = ts.hinweis_mietzinsrechner;""")
        frappe.db.commit()
        print("Done")
    except Exception as err:
        print("Patch failed")
        print(str(err))
        pass
    return
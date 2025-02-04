import frappe
from frappe import _

def execute():
    try:
        overall_loop = 1
        mv_erb_users = frappe.db.sql("""SELECT `parent` AS `user` FROM `tabHas Role` WHERE `role` = 'MV_ERB'""", as_dict=True)
        total_1 = len(mv_erb_users)
        for mv_erb_user in mv_erb_users:
            print("{0} von {1}".format(overall_loop, total_1))
            mv_erb_berater = frappe.db.sql("""SELECT `parent` AS `id` FROM `tabTermin Kontaktperson Multi User` WHERE `user` = '{mv_erb_user}'""".format(mv_erb_user=mv_erb_user.user), as_dict=True)
            inside_loop = 1
            total_2 = len(mv_erb_berater)
            for mv_erb_brtr in mv_erb_berater:
                print("{0}.{1} von {2}.{3}".format(overall_loop, inside_loop, overall_loop, total_2))
                update = frappe.db.sql("""UPDATE `tabBeratung` SET `mv_erb_permission` = 'Write' WHERE `kontaktperson` = '{mv_erb_brtr}'""".format(mv_erb_brtr=mv_erb_brtr.id))
                inside_loop += 1
            overall_loop += 1
        frappe.db.commit()
        update = frappe.db.sql("""UPDATE `tabBeratung` SET `mv_erb_permission` = 'None' WHERE `mv_erb_permission` IS NULL""")
        frappe.db.commit()
        print("Done")
    except Exception as err:
        print("Patch MV_ERB Permission initial setup failed")
        print(str(err))
        pass
    return

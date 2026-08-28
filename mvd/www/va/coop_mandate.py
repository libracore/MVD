from __future__ import unicode_literals
import frappe
from frappe.utils import cint, formatdate, today
from frappe.core.doctype.communication.email import make
from frappe import sendmail
from frappe.utils.jinja import render_template

no_cache = 1

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect

    if not "rsvmandat_rsv" in frappe.get_roles():
        frappe.local.flags.redirect_location = "/desk#vbz"
        raise frappe.Redirect
    
    context.html_table = get_content()
    
    return context

def get_content():
    html = """
        <div class="rsv-table-wrapper">
            <table class="rsv-table">
                <thead>
                    <tr>
                        <th>Typ</th>
                        <th>Erstellung</th>
                        <th>Kostengutsprache</th>
                        <th>Ablehnen</th>
                        <th>Abgeschlossen</th>
                        <th>Mandat</th>
                        <th>Coop-Fallnummer</th>
                        <th>Mitglied: Name, Vorname</th>
                        <th>Mitglied: Strasse Nr, PLZ Ort (Mietobj.)</th>
                        <th>Mitglied: Eintrittsdatum</th>
                        <th>Gegenseite (Vermieterin)</th>
                        <th>Gegenseite (Verwaltung)</th>
                        <th>Thema</th>
                        <th>Vertrauensanwält*in</th>
                        <th>Gruppenmandat</th>
                        <th>Doppelversicherung</th>
                        <th>Sachbearbeiter*in</th>
                        <th>Bemerkungen</th>
                        <th>Download</th>
                    </tr>
                </thead>

                <tbody>

                    {table_content}

                </tbody>
            </table>
        </div>
    """.format(
        table_content=get_table_content()
    )

    return html

def get_table_content():
    table_content = ""
    mandate = frappe.db.sql(
        """
            SELECT
                m.`name`,
                m.`datum_va_vergabe`,
                m.`fallnummer`,
                m.`vermieterin`,
                m.`verwaltung`,
                m.`anwalt`,
                m.`typ`,
                NOT EXISTS (
                    SELECT 1
                    FROM `tabRSVMitglied` mi
                    WHERE mi.`rsvmandat` = m.`name`
                    AND IFNULL(mi.`abschluss_datum`, '') = ''
                    AND IFNULL(mi.`abgelehnt_datum`, '') = ''
                ) AS `inaktiv`
            FROM `tabRSVMandat` m
            WHERE `datum_va_vergabe` IS NOT NULL
            AND m.`anwalt` IS NOT NULL
            AND EXISTS (
                SELECT 1
                FROM `tabRSVMitglied` mi
                WHERE mi.`rsvmandat` = m.`name`
                AND mi.`status` NOT IN ('Provisorisch EM', 'Provisorisch GM', 'Vorprüfung')
            )
            ORDER BY `inaktiv` ASC, `datum_va_vergabe` DESC
        """,
        as_dict=True
    )

    for mandat in mandate:
        themen = get_themen(mandat.name)
        gruppenmandat = 'Ja' if mandat.typ != "EM" else 'Nein'
        mandat_inaktiv_class = "inaktiv" if cint(mandat.inaktiv) == 1 else ""

        table_content += """
            <tr class="mandat-row {mandat_inaktiv_class}">
                <td>{typ}</td>
                <td>{datum_va_vergabe}</td>
                <td></td>
                <td></td>
                <td></td>
                <td>{name}</td>
                <td class="fallnummer-cell" data-rsvmandat="{name}">{fallnummer}</td>
                <td></td>
                <td></td>
                <td></td>
                <td>{vermieterin}</td>
                <td>{verwaltung}</td>
                <td>{themen}</td>
                <td>{anwalt}</td>
                <td>{gruppenmandat}</td>
                <td><!-- Doppelversicherung --></td>
                <td><!-- Sachbearbeiter*in --></td>
                <td><!-- Bemerkungen --></td>
                <td><!-- Download zip --></td>
            </tr>
        """.format(
            name=mandat.name,
            datum_va_vergabe=formatdate(mandat.datum_va_vergabe, "dd.MM.yyyy"),
            fallnummer=mandat.fallnummer or '',
            vermieterin=mandat.vermieterin or '',
            verwaltung=mandat.verwaltung or '',
            themen=themen or '',
            anwalt=mandat.anwalt or '',
            gruppenmandat=gruppenmandat,
            mandat_inaktiv_class=mandat_inaktiv_class,
            typ=mandat.typ
        )

        rsv_mitglieder = frappe.db.sql(
            """
                SELECT
                    `name`,
                    `vorname`,
                    `nachname`,
                    `kostengutsprache`,
                    `kostengutsprache_datum`,
                    `abgelehnt_datum`,
                    `status`,
                    `abschluss_datum`,
                    `fallnummer`,
                    `strasse`,
                    `hausnummer`,
                    `plz`,
                    `ort`,
                    `mitglied_seit`
                FROM `tabRSVMitglied`
                WHERE `rsvmandat` = '{mandat}'
                AND `status` NOT IN ('Provisorisch EM', 'Provisorisch GM', 'Vorprüfung') -- Achtung, Filter-Duplikat in RSV-Mandat Query
            """.format(mandat=mandat.name),
            as_dict=True
        )

        for rsv_mitglied in rsv_mitglieder:
            kostengutsprache_zelle = """
                <td class="kostengutsprache-cell"
                    data-rsvmitglied="{rsv_mitglied}">
                    ✓
                </td>
            """.format(rsv_mitglied=rsv_mitglied.name)
            if cint(rsv_mitglied.kostengutsprache) == 1:
                kostengutsprache_zelle = '<td class="status">{kostengutsprache}</td>'.format(
                    kostengutsprache=formatdate(rsv_mitglied.kostengutsprache_datum, "dd.MM.yyyy")
                )
            elif rsv_mitglied.status == 'Abgelehnt':
                kostengutsprache_zelle = '<td class="status">-</td>'

            abgelehnt_zelle = """
                <td class="abgelehnt-cell"
                    data-rsvmitglied="{rsv_mitglied}">
                    ×
                </td>
            """.format(rsv_mitglied=rsv_mitglied.name)
            if rsv_mitglied.status == 'Abgelehnt':
                abgelehnt_zelle = '<td class="status">{abgelehnt_datum}</td>'.format(
                    abgelehnt_datum=formatdate(rsv_mitglied.abgelehnt_datum, "dd.MM.yyyy")
                )
            elif cint(rsv_mitglied.kostengutsprache) == 1:
                abgelehnt_zelle = '<td class="status">-</td>'

            doppelversicherung = get_doppelversicherung(rsv_mitglied.name)

            table_content += """
                <tr class="mitglied-row {mandat_inaktiv_class}">
                    <td><!-- Typ --></td>
                    <td><!-- Datum Vergabe --></td>
                    {kostengutsprache_zelle}
                    {abgelehnt_zelle}
                    <td>{abschluss_datum}</td>
                    <td><!-- RSV-Mandat --></td>
                    <td class="fallnummer-cell" data-rsvmitglied="{rsv_mitglied}">{fallnummer}</td>
                    <td>{nachname}, {vorname}</td>
                    <td>{adresse}</td>
                    <td>{mitglied_seit}</td>
                    <td><!-- Gegenseite Vermiterin --></td>
                    <td><!-- Gegenseite Verwaltung --></td>
                    <td><!-- Themen --></td>
                    <td><!-- Anwalt --></td>
                    <td><!-- Gruppenmandat --></td>
                    <td>{doppelversicherung}</td>
                    <td><!-- Sachbearbeiter*in --></td>
                    <td><!-- Bemerkungen --></td>
                    <td class="zip-cell" data-rsvmitglied="{rsv_mitglied}">zip</td>
                </tr>
            """.format(
                rsv_mitglied=rsv_mitglied.name,
                vorname=rsv_mitglied.vorname,
                nachname=rsv_mitglied.nachname,
                kostengutsprache_zelle=kostengutsprache_zelle,
                abgelehnt_zelle=abgelehnt_zelle,
                abschluss_datum=formatdate(rsv_mitglied.abschluss_datum, "dd.MM.yyyy") or '',
                fallnummer=rsv_mitglied.fallnummer or '',
                adresse="{0} {1}, {2} {3}".format(rsv_mitglied.strasse, rsv_mitglied.hausnummer, rsv_mitglied.plz, rsv_mitglied.ort),
                mitglied_seit=formatdate(rsv_mitglied.mitglied_seit, "dd.MM.yyyy"),
                doppelversicherung=doppelversicherung,
                mandat_inaktiv_class=mandat_inaktiv_class
            )

    return table_content

def get_themen(rsv_mandat):
    themen = frappe.db.sql(
        """
            SELECT `thema`
            FROM `tabRSV Thema MultiTable`
            WHERE `parent` = '{0}'
        """.format(rsv_mandat),
        as_dict=True
    )
    if len(themen) < 1:
        return ''

    return "<br>".join(x.thema for x in themen)

def get_doppelversicherung(rsv_mitglied):
    d_v = frappe.db.sql(
        """
            SELECT
                `doppelversicherung`,
                `doppelversicherung_bei`
            FROM `tabRSVMitglied`
            WHERE `name` = '{0}'
        """.format(rsv_mitglied),
        as_dict=True
    )

    if len(d_v) < 1 or cint(d_v[0].doppelversicherung) == 0:
        return 'Nein'

    return 'Ja {0}'.format("({0})".format(d_v[0].doppelversicherung_bei) if d_v[0].doppelversicherung_bei else '')

def get_inactiv_tag(rsv_mandat):
    rsv_mitglieder = frappe.db.sql(
        """
            SELECT `name`
            FROM `tabRSVMitglied`
            WHERE
                `rsvmandat` = '{0}'
                AND IFNULL()
        """.format(),
        as_dict=True
    )


    is_active = True
    abschluss = 0
    for rsv_mitglied in rsv_mitglieder:
        if rsv_mitglied.abschluss_datum:
            abschluss += 1
        

@frappe.whitelist()
def erteile_kostenfreigabe(rsvmitglied):
    rsvm = frappe.get_doc("RSVMitglied", rsvmitglied)
    rsvm.kostengutsprache = 1
    rsvm.kostengutsprache_datum = today()
    rsvm.status = "Vergeben"
    rsvm.save(ignore_permissions=True)
    tirgger_emails(rsvmitglied, rsvm.rsvmandat, rsvm.sektion_id)
    return

@frappe.whitelist()
def ablehnung(rsvmitglied):
    rsvm = frappe.get_doc("RSVMitglied", rsvmitglied)
    rsvm.status = 'Abgelehnt'
    rsvm.save(ignore_permissions=True)
    return

@frappe.whitelist()
def add_fallnummer(fallnummer=None, rsvmandat=None, rsvmitglied=None):
    rsvm = False
    print(fallnummer, rsvmandat, rsvmitglied)
    if rsvmandat:
        rsvm = frappe.get_doc("RSVMandat", rsvmandat)
    if rsvmitglied:
        rsvm = frappe.get_doc("RSVMitglied", rsvmitglied)

    if rsvm:
        rsvm.fallnummer = fallnummer
        rsvm.save(ignore_permissions=True)

    return

def tirgger_emails(rsvmitglied, rsvmandat, sektion):
    def is_email_enabled():
        return cint(frappe.db.get_value(
            "Sektion",
            sektion,
            "rsv_auto_email_enabled"
        ))

    def get_templates():
        return frappe.db.get_values(
            "Sektion",
            sektion,
            fieldname=["rsv_mail_template_va", "rsv_mail_template_mitglied"],
            as_dict=True
        )[0]

    def get_email_addresses():
        return {
            'va': get_va_mail(),
            'mitglied': get_mitglied_mail(),
            'cc': get_cc_mail()
        }

    def get_va_mail():
        va = frappe.db.get_value(
            "RSVMandat",
            rsvmandat,
            'anwalt'
        )
        if not va: return None

        users = frappe.db.sql(
            """
                SELECT `user`
                FROM `tabTermin Kontaktperson Multi User`
                WHERE `parent` = '{0}'
                LIMIT 1
            """.format(va),
            as_dict=True
        )
        if len(users) < 1: return None

        return users[0].user

    def get_mitglied_mail():
        return frappe.db.get_value(
            "Mitgliedschaft",
            frappe.db.get_value(
                "RSVMitglied",
                rsvmitglied,
                "mv_mitgliedschaft"
            ),
            "e_mail_1"
        )

    def get_cc_mail():
        return frappe.db.get_value(
            "Sektion",
            sektion,
            'rsv_team_cc'
        )

    def get_absender():
        return {
            "account": frappe.db.get_value(
                "Sektion",
                sektion,
                "rsv_absender_account"
            ),
            "name": frappe.db.get_value(
                "Sektion",
                sektion,
                "rsv_absender_name"
            )
        }

    def render_mail_template(template):
        context = dict(frappe.get_doc("RSVMitglied", rsvmitglied).as_dict())
        temp = frappe.get_doc("Email Template", template)
        subject = render_template(temp.subject, context)
        message = render_template(temp.response, context)
        return subject, message

    if not is_email_enabled(): return

    templates = get_templates()
    mail_addresses = get_email_addresses()
    absender = get_absender()

    # Send VA Mail
    print(mail_addresses.get("va"), templates.get("rsv_mail_template_va"))
    if mail_addresses.get("va") and templates.get("rsv_mail_template_va"):
        va_betreff, va_message = render_mail_template(templates.get("rsv_mail_template_va"))
        send_mail_to(
            [mail_addresses.get("va")],
            mail_addresses.get("cc") if mail_addresses.get("cc") else '',
            va_betreff,
            va_message,
            rsvmitglied,
            absender.get("name"),
            absender.get("account")
        )

    # Send Mitglied Mail
    if mail_addresses.get("mitglied") and templates.get("rsv_mail_template_mitglied"):
        mitgl_betreff, mitgl_message = render_mail_template(templates.get("rsv_mail_template_mitglied"))
        send_mail_to(
            [mail_addresses.get("mitglied")],
            '',
            mitgl_betreff,
            mitgl_message,
            rsvmitglied,
            absender.get("name"),
            absender.get("account")
        )

    return

def send_mail_to(recipient, cc, betreff, message, rsvmitglied, absender_name, absender_account):
    try:
        comm = make(
            recipients=recipient,
            cc=cc,
            sender=absender_account,
            subject=betreff,
            content=message,
            doctype='RSVMitglied',
            name=rsvmitglied,
            attachments=[],
            send_email=False,
            sender_full_name=absender_name
        )["name"]
        
        sendmail(
            recipients=recipient,
            sender=absender_account,
            subject=betreff,
            message=message,
            as_markdown=False,
            delayed=True,
            reference_doctype='RSVMitglied',
            reference_name=rsvmitglied,
            unsubscribe_method=None,
            unsubscribe_params=None,
            unsubscribe_message=None,
            attachments=[],
            content=None,
            doctype='RSVMitglied',
            name=rsvmitglied,
            reply_to=absender_account,
            cc=cc,
            bcc=[],
            message_id=frappe.get_value("Communication", comm, "message_id"),
            in_reply_to=None,
            send_after=None,
            expose_recipients=None,
            send_priority=1,
            communication=comm,
            retry=1,
            now=None,
            read_receipt=None,
            is_notification=False,
            inline_images=None,
            template=None,
            args={},
            header=None,
            print_letterhead=False
        )
        
        return 1
    except Exception as err:
        # Mail konnte nicht erstellt werden. Error-log und Überspringen...
        frappe.log_error("{0}\n\n{1}".format(err, frappe.utils.get_traceback() or ''), 'Serien Email Queue Error')
        return False
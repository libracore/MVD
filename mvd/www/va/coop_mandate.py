from __future__ import unicode_literals
import frappe
from frappe.utils import cint, formatdate, today

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
                `name`,
                `datum_va_vergabe`,
                `fallnummer`,
                `vermieterin`,
                `verwaltung`,
                `anwalt`,
                `typ`
            FROM `tabRSVMandat`
            WHERE `datum_va_vergabe` IS NOT NULL
            AND `anwalt` IS NOT NULL
        """,
        as_dict=True
    )

    for mandat in mandate:
        themen = get_themen(mandat.name)
        gruppenmandat = 'Ja' if mandat.typ != "EM" else 'Nein'

        table_content += """
            <tr class="mandat-row">
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
            gruppenmandat=gruppenmandat
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
                <tr class="mitglied-row">
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
                doppelversicherung=doppelversicherung
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

@frappe.whitelist()
def erteile_kostenfreigabe(rsvmitglied):
    rsvm = frappe.get_doc("RSVMitglied", rsvmitglied)
    rsvm.kostengutsprache = 1
    rsvm.kostengutsprache_datum = today()
    rsvm.status = "Vergeben"
    rsvm.save(ignore_permissions=True)
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
from __future__ import unicode_literals
import frappe
from frappe.utils import cint, formatdate
import io
import os
import zipfile
from urllib.parse import unquote
from mvd.mvd.doctype.rsvmandat.rsvmandat import get_rsv_mandat_languages, get_va_from_user

no_cache = 1

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect
    
    context.card_lists, context.detail_cards = get_cards()
    
    return context

def get_cards():
    def get_card(details):
        qty = 0
        if details.typ == 'KGM':
            qty = frappe.db.count('RSVMitglied', filters = dict(rsvmandat=details.name, status='Vergeben'))
        if details.typ == 'EM':
            qty = 1
        
        if qty < 1: return False

        card_template = """
            <article class="case-card" {style} data-mandat="{mandat}" data-mandattyp="{typ}" data-closestatus="{close_status}" onclick="show_detail_card('{mandat}')">
                <div class="badges">
                    <span class="badge">{typ}</span>
                    <span class="badge">Anz. Mitglieder: {qty}</span>
                    <span class="badge open">✔</span>
                    {closed_batch}
                </div>
                <h3>{titel}</h3>
                <p>{kurzbeschrieb}</p>
                <div class="case-footer">
                    <span>Frist: {frist}</span>
                    <span>Details ansehen</span>
                </div>
            </article>
        """.format(
                titel=details.bezeichnung or details.name,
                kurzbeschrieb=details.kurzbeschrieb or '',
                mandat=details.name,
                typ=details.typ,
                qty=qty,
                frist=details.frist or '-',
                close_status=mandat.get("close_status"),
                style='style="display: none;"' if cint(mandat.get("close_status")) == 1 else '',
                closed_batch='<span class="badge urgent">Abgeschlossen</span>' if cint(mandat.get("close_status")) == 1 else ''
            )

        return card_template
    
    def get_detail_card(mandat, mandat_sprachen):
        def get_einzelmandat_details(mandat):
            return_data = """"""

            einzelmandat_template = """
                <div class="section">
                    <h4>Mitglied {loop}</h4>
                    <table style="width: 90%;">
                        {doppelversicherung}
                        <tr>
                            <td>Kostengutsprache</td>
                            <td>{kostengutsprache}</td>
                        </tr>
                        <tr>
                            <td>Name Mietpartei</td>
                            <td>{mietpartei}</td>
                        </tr>
                        <tr>
                            <td>Mietobjekt</td>
                            <td>{mietobjekt}</td>
                        </tr>
                        <tr>
                            <td>RSV-Mitglied Fallnr.</td>
                            <td>{fallnummer}</td>
                        </tr>
                        <tr>
                            <td>RSV-Mitglied Status</td>
                            <td>{status}</td>
                        </tr>
                    </table>
                </div>

                <div class="section">
                    <h4>Beschreibung</h4>
                    <p>
                        {beschreibung}
                    </p>
                </div>
                <div class="section">
                    <div class="actions">
                            <button class="btn-primary" onclick="download_zip('{mandat_name}')">Daten als Zip-File herunterladen</button>
                            {close_rsvmitglied_btn}
                    </div>
                </div>
                <hr>
            """

            einzelmandate = frappe.db.sql(
                """
                    SELECT
                        m.*
                    FROM `tabRSVMitglied` m
                    WHERE m.rsvmandat = '{0}'
                    GROUP BY m.name
                """.format(mandat.name),
                as_dict=True
            )

            loop = 1
            for einzelmandat in einzelmandate:
                doppelversicherung = ''
                if cint(einzelmandat.doppelversicherung) == 1:
                    doppelversicherung = """
                        <p>⚠️ Doppelversicherung: {0}</p>
                    """.format(einzelmandat.doppelversicherung_bei)
                
                close_rsvmitglied_btn = ''
                # if einzelmandat.status != 'Abgeschlossen':
                #     close_rsvmitglied_btn = """<button class="btn-primary" onclick="close_rsvmitglied('{mandat_name}')">RSV-Mitglied schliessen</button>""".format(mandat_name=einzelmandat.name)
                
                return_data += einzelmandat_template.format(
                                                        beschreibung=einzelmandat.beschreibung or '-',
                                                        loop=loop,
                                                        mandat_name=einzelmandat.name,
                                                        mietpartei="{0} {1}".format(einzelmandat.vorname, einzelmandat.nachname),
                                                        doppelversicherung=doppelversicherung,
                                                        mietobjekt="{0} {1}, {2} {3}".format(einzelmandat.strasse, einzelmandat.hausnummer, einzelmandat.plz, einzelmandat.ort),
                                                        fallnummer=einzelmandat.fallnummer,
                                                        close_rsvmitglied_btn=close_rsvmitglied_btn,
                                                        status=einzelmandat.status,
                                                        kostengutsprache=formatdate(einzelmandat.kostengutsprache_datum, "dd.MM.yyyy") if cint(einzelmandat.kostengutsprache) == 1 else ''
                                                    )
                loop += 1
            
            return return_data
        
        if mandat.typ == 'KGM':
            qty = frappe.db.count('RSVMitglied', filters = dict(rsvmandat=mandat.name, status='Geprüft'))
        if mandat.typ == 'EM':
            qty = 1

        rsv_mandat_close_btn = ''
        if cint(mandat.get("close_status")) != 1:
            rsv_mandat_close_btn = """
                <div class="actions">
                    <button class="btn-primary" onclick="close_rsvmandat('{mandat}')">RSV-Mandat schliessen</button>
                </div>
            """.format(mandat=mandat.name)
        
        detail_card_template = """
            <section class="detail hidden" data-belongstomandat="{mandat}">
                <div class="detail-header">
                    <div>
                        <h2>{titel}</h2>
                        <p class="detail-subtitle">
                        {kurzbeschrieb}
                        </p>
                    </div>
                    {closed_batch}
                </div>

                {rsv_mandat_close_btn}

                <div class="section">
                    <table style="width: 90%;">
                        <tr>
                            <td><b>Anz. Einzelmandate</b></td>
                            <td>{qty}</td>
                        </tr>
                        <tr>
                            <td><b>RSV-Mandat Fallnr.</b></td>
                            <td>{fallnummer}</td>
                        </tr>
                        <tr>
                            <td><b>Typ</b></td>
                            <td>{typ}</td>
                        </tr>
                        <tr>
                            <td><b>Thema</b></td>
                            <td>{thema}</td>
                        </tr>
                        <tr>
                            <td><b>Sprache</b></td>
                            <td>{language}</td>
                        </tr>
                        <tr>
                            <td><b>Gegenseite Vermieterin</b></td>
                            <td>{vermieterin}</td>
                        </tr>
                        <tr>
                            <td><b>Gegenseite Verwaltung</b></td>
                            <td>{verwaltung}</td>
                        </tr>
                        <tr>
                            <td><b>Schlichtungsbehörde</b></td>
                            <td>{schlichtungsbehoerde}</td>
                        </tr>
                        <tr>
                            <td><b>Frist</b></td>
                            <td>{frist}</td>
                        </tr>
                        <tr>
                            <td><b>Verhandlungsdatum</b></td>
                            <td>{verhandlungsdatum}</td>
                        </tr>
                    </table>
                </div>

                {einzelmandat_details}
            </section>
        """.format(
                mandat=mandat.name,
                titel=mandat.bezeichnung or mandat.name,
                language=mandat_sprachen,
                qty=qty,
                typ=mandat.typ,
                kurzbeschrieb=mandat.kurzbeschrieb or '',
                frist=mandat.frist or '-',
                verhandlungsdatum=mandat.verhandlungsdatum or '-',
                einzelmandat_details=get_einzelmandat_details(mandat),
                fallnummer=mandat.fallnummer or '',
                thema=mandat.themen,
                vermieterin=mandat.vermieterin,
                verwaltung=mandat.verwaltung,
                schlichtungsbehoerde=mandat.schlichtungsbehoerde,
                rsv_mandat_close_btn=rsv_mandat_close_btn,
                closed_batch='<span class="status-pill-red">Abgeschlossen</span>' if cint(mandat.get("close_status")) == 1 else ''
            )

        return detail_card_template
    va_user = get_va_from_user(frappe.session.user)
    mandate = frappe.db.sql(
        """
            SELECT
                m.`name`,
                m.`bezeichnung`,
                m.`typ`,
                m.`publikation_per`,
                m.`kurzbeschrieb`,
                m.`frist`,
                m.`verhandlungsdatum`,
                m.`verwaltung`,
                m.`vermieterin`,
                m.`schlichtungsbehoerde`,
                m.`fallnummer`,
                GROUP_CONCAT(t.`thema` ORDER BY t.`idx` SEPARATOR '<br>') AS `themen`,
                NULL AS `close_status`
            FROM `tabRSVMandat` m
            LEFT JOIN `tabRSV Thema MultiTable` t
                ON t.`parent` = m.`name`
            WHERE m.`anwalt` = '{user}'
            GROUP BY
                m.`name`,
                m.`bezeichnung`,
                m.`typ`,
                m.`publikation_per`,
                m.`kurzbeschrieb`,
                m.`frist`,
                m.`verhandlungsdatum`,
                m.`verwaltung`,
                m.`vermieterin`,
                m.`schlichtungsbehoerde`,
                m.`fallnummer`
            ORDER BY
                m.`publikation_per` ASC,
                m.`typ` ASC
        """.format(user=va_user),
        as_dict=True
    )
    
    cards = []
    detail_cards = []
    
    # Ergänzen der Mandat-Objekte mit Close-Flags
    for mandat in mandate:
        mandat['close_status'] = 1 if check_if_is_closed(mandat.name) else 0

    # Sortieren der Mandat-Objekte nach Close-Flags
    mandate = sorted(
        mandate,
        key=lambda x: x.get("close_status") != 0
    )

    # Verarbeiten der Mandat-Objekte
    for mandat in mandate:
        card = get_card(mandat)
        if card:
            cards.append(card)
            mandat_sprachen = get_rsv_mandat_languages(mandat.name)
            detail_cards.append(get_detail_card(mandat, mandat_sprachen))
    
    return cards, detail_cards

@frappe.whitelist()
def download_zip(mandat):
    m = frappe.get_doc("RSVMitglied", mandat)
    file_urls = []
    for dokument in m.dokumente:
        if dokument.file_upload:
            file_urls.append(dokument.file_upload)
    
    if len(file_urls) < 1:
        frappe.throw("Zu diesem Mandat gibt es keine Dokumentation.")
    
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_url in file_urls:
            file_path = resolve_file_path(file_url)

            if not os.path.exists(file_path):
                frappe.log_error("File not found: {file_url}".format(file_url=file_url), "ZIP Creation")
                continue

            zipf.write(file_path, os.path.basename(file_path))

    zip_buffer.seek(0)

    frappe.local.response.filename = "{0}.zip".format(mandat)
    frappe.local.response.filecontent = zip_buffer.getvalue()
    frappe.local.response.type = "download"

def resolve_file_path(file_url):
    file_url = unquote(file_url)

    if file_url.startswith("/private/files/"):
        filename = file_url.replace("/private/files/", "", 1)
        return frappe.get_site_path("private", "files", filename)

    if file_url.startswith("/files/"):
        filename = file_url.replace("/files/", "", 1)
        return frappe.get_site_path("public", "files", filename)

    frappe.error_log("Page va/meine-mandate: ZIP CreationUnsupported file_url: {0}".format(file_url), "Page va/meine-mandate: ZIP Creation")
    return None

@frappe.whitelist()
def close_rsvmitglied(rsv_mitglied):
    rsvm = frappe.get_doc("RSVMitglied", rsv_mitglied)
    rsvm.status = 'Abgeschlossen'
    rsvm.save(ignore_permissions=True)
    return

@frappe.whitelist()
def close_rsvmandat(rsv_mandat):
    rsv_mitglieder = frappe.db.sql(
        """
            SELECT `name`
            FROM `tabRSVMitglied`
            WHERE `rsvmandat` = '{0}'
        """.format(rsv_mandat),
        as_dict=True
    )
    for rsv_mitglied in rsv_mitglieder:
        close_rsvmitglied(rsv_mitglied.name)

    return

def check_if_is_closed(rsv_mandat):
    is_closed = True
    rsv_mitglieder = frappe.db.sql(
        """
            SELECT `status`
            FROM `tabRSVMitglied`
            WHERE `rsvmandat` = '{0}'
        """.format(rsv_mandat),
        as_dict=True
    )
    for rsv_mitglied in rsv_mitglieder:
        if rsv_mitglied.status != 'Abgeschlossen':
            is_closed = False
            break

    return is_closed
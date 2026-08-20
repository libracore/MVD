from __future__ import unicode_literals
import frappe
from frappe.utils import cint
import io
import os
import zipfile
from urllib.parse import unquote
from mvd.mvd.doctype.rsvmandat.rsvmandat import get_rsv_mandat_languages

no_cache = 1

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect
    
    context.card_lists, context.detail_cards = get_cards()
    
    return context

def get_cards():
    def get_card(details):
        if details.typ == 'KGM':
            qty = frappe.db.count('RSVMitglied', filters = dict(rsvmandat=details.name, status='Geprüft'))
        if details.typ == 'EM':
            qty = 1
        
        if qty < 1: return False

        card_template = """
            <article class="case-card" data-mandat"{mandat}" data-mandattyp="{typ}" onclick="show_detail_card('{mandat}')">
                <div class="badges">
                    <span class="badge">{typ}</span>
                    <span class="badge">Anz. Mandate: {qty}</span>
                    <span class="badge open">✔</span>
                </div>
                <h3>{titel}</h3>
                <p>{kurzbeschrieb}</p>
                <div class="case-footer">
                    <span>Frist: {frist}</span>
                    <span>Details ansehen</span>
                </div>
            </article>
        """.format(titel=details.bezeichnung or details.name, kurzbeschrieb=details.kurzbeschrieb or 'Klicken sie hier für mehr Informationen.',
                   mandat=details.name, typ=details.typ, qty=qty, frist=details.frist or '-')

        return card_template
    
    def get_detail_card(mandat, mandat_sprachen):
        def get_einzelmandat_details(mandat):
            return_data = """"""

            einzelmandat_template = """
                <div class="section">
                    <h4>Mandat {loop}</h4>
                    <table style="width: 50%;">
                        {doppelversicherung}
                        <tr>
                            <td>Name Mietpartei</td>
                            <td>{mietpartei}</td>
                        </tr>
                        <tr>
                            <td>Mietobjekt</td>
                            <td>{mietobjekt}</td>
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
                    AND m.status = 'Geprüft'
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
                
                return_data += einzelmandat_template.format(
                                                        beschreibung=einzelmandat.beschreibung or '-',
                                                        loop=loop,
                                                        mandat_name=einzelmandat.name,
                                                        mietpartei="{0} {1}".format(einzelmandat.vorname, einzelmandat.nachname),
                                                        doppelversicherung=doppelversicherung,
                                                        mietobjekt="{0} {1}, {2} {3}".format(einzelmandat.strasse, einzelmandat.hausnummer, einzelmandat.plz, einzelmandat.ort)
                                                    )
                loop += 1
            
            return return_data
        
        if mandat.typ == 'KGM':
            qty = frappe.db.count('RSVMitglied', filters = dict(rsvmandat=mandat.name, status='Geprüft'))
        if mandat.typ == 'EM':
            qty = 1
        
        detail_card_template = """
            <section class="detail hidden" data-belongstomandat="{mandat}">
                <div class="detail-header">
                    <div>
                        <h2>{titel}</h2>
                        <p class="detail-subtitle">
                        {kurzbeschrieb}
                        </p>
                    </div>
                    <span class="status-pill">Mir zugewiesenes Mandat</span>
                </div>

                <div class="interest-box">
                    <label for="message">Fallnummer</label>
                    <input type="text" id="fallnummer-{mandat}" placeholder="Fallnummer hinzufügen..." value="{fallnummer}"></input>

                    <div class="actions">
                        <button class="btn-primary" onclick="add_fallnummer('{mandat}')">Fallnummer speichern</button>
                    </div>
                </div>

                <div class="section">
                    <table style="width: 90%;">
                        <tr>
                            <td>Anz. Einzelmandate</td>
                            <td>{qty}</td>
                        </tr>
                        <tr>
                            <td>Typ</td>
                            <td>{typ}</td>
                        </tr>
                        <tr>
                            <td>Thema</td>
                            <td>{thema}</td>
                        </tr>
                        <tr>
                            <td>Sprache</td>
                            <td>{language}</td>
                        </tr>
                        <tr>
                            <td>Gegenseite Vermieterin</td>
                            <td>{vermieterin}</td>
                        </tr>
                        <tr>
                            <td>Gegenseite Verwaltung</td>
                            <td>{verwaltung}</td>
                        </tr>
                        <tr>
                            <td>Schlichtungsbehörde</td>
                            <td>{schlichtungsbehoerde}</td>
                        </tr>
                        <tr>
                            <td>Frist</td>
                            <td>{frist}</td>
                        </tr>
                        <tr>
                            <td>Verhandlungsdatum</td>
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
                schlichtungsbehoerde=mandat.schlichtungsbehoerde
            )

        return detail_card_template
    
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
                m.`fallnummer`,
                m.`verwaltung`,
                m.`vermieterin`,
                m.`schlichtungsbehoerde`,
                GROUP_CONCAT(t.thema ORDER BY t.idx SEPARATOR '<br>') AS `themen`
            FROM `tabRSVMandat` m
            LEFT JOIN `tabRSV Thema MultiTable` t
                ON t.parent = m.name
            WHERE m.`name` IN (
                SELECT `parent`
                FROM `tabVA Vergabe TBL`
                WHERE `assigned` = 1
                AND `va_user` = '{user}'
            )
        """.format(user=frappe.session.user),
        as_dict=True
    )
    
    cards = []
    detail_cards = []
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

    print(file_urls)
    
    if len(file_urls) < 1:
        frappe.throw("Zu diesem Mandat gibt es keine Dokumentation.")
    
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_url in file_urls:
            file_path = resolve_file_path(file_url)

            if not os.path.exists(file_path):
                frappe.log_error(f"File not found: {file_url}", "ZIP Creation")
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
def add_fallnummer(mandat, fallnummer):
    ml = frappe.get_doc("RSVMandat", mandat)
    ml.fallnummer = fallnummer
    ml.save(ignore_permissions=True)
    return
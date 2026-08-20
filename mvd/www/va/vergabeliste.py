from __future__ import unicode_literals
import frappe
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

        va_badge = ''
        va_in_list = is_va_already_in_list(details.name)
        if va_in_list:
            va_badge = '<span class="badge open">✔</span>'

        card_template = """
            <article class="case-card" data-mandat="{mandat}" data-mandattyp="{typ}" onclick="show_detail_card('{mandat}')">
                <div class="badges">
                    <span class="badge">{typ}</span>
                    <span class="badge">Anz. Mandate: {qty}</span>
                    {va_badge}
                </div>
                <h3>{titel}</h3>
                <p>{kurzbeschrieb}</p>
                <div class="case-footer">
                    <span>Frist: {frist}</span>
                    <span>Details ansehen</span>
                </div>
            </article>
        """.format(titel=details.bezeichnung or details.name, kurzbeschrieb=details.kurzbeschrieb or 'Klicken sie hier für mehr Informationen.',
                   mandat=details.name, typ=details.typ, qty=qty, va_badge=va_badge,
                   frist=details.frist or '-')

        return card_template
    
    def get_detail_card(mandat, mandat_sprachen):
        def get_einzelmandat_details(mandat):
            return_data = """"""

            einzelmandat_template = """
                <div class="section">
                    <h4>Mandat {loop}</h4>
                    <table style="width: 90%;">
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
                return_data += einzelmandat_template.format(
                                    beschreibung=einzelmandat.beschreibung or '-', 
                                    loop=loop,
                                    mietobjekt="{0} {1}, {2} {3}".format(einzelmandat.strasse, einzelmandat.hausnummer, einzelmandat.plz, einzelmandat.ort),
                                    mietpartei="{0} {1}".format(einzelmandat.vorname, einzelmandat.nachname)
                                )
                loop += 1
            
            return return_data
        
        if mandat.typ == 'KGM':
            qty = frappe.db.count('RSVMitglied', filters = dict(rsvmandat=mandat.name, status='Geprüft'))
        if mandat.typ == 'EM':
            qty = 1
        
        status_pill = '<span class="status-pill">Offen für Interesse</span>'
        interessiert_btn = 'Ja, ich bin interessiert'
        interessiert_btn_color = 'primary'
        va_in_list = is_va_already_in_list(mandat.name)
        if va_in_list:
            status_pill = '<span class="status-pill">Interesse bereits hinterlegt</span>'
            interessiert_btn = 'kein Interesse'
            interessiert_btn_color = 'danger'
        
        detail_card_template = """
            <section class="detail hidden" data-belongstomandat="{mandat}">
                <div class="detail-header">
                    <div>
                        <h2>{titel}</h2>
                        <p class="detail-subtitle">
                        {kurzbeschrieb}
                        </p>
                    </div>
                    {status_pill}
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

                <div class="interest-box">
                    <h3>Interesse hinterlegen</h3>

                    <label for="message">Nachricht / Bemerkung</label>
                    <textarea id="message-{mandat}" placeholder="Kurze Bemerkung zu Kapazität, Erfahrung oder Rückfragen..."></textarea>

                    <div class="actions">
                        <button class="btn-{interessiert_btn_color}" onclick="take('{mandat}', '{va_in_list}')">{interessiert_btn}</button>
                    </div>
                </div>
            </section>
        """.format(mandat=mandat.name,
                    titel=mandat.bezeichnung or mandat.name,
                    schlichtungsbehoerde=mandat.schlichtungsbehoerde or '-',
                    language=mandat_sprachen or '-',
                    qty=qty or '-',
                    typ=mandat.typ,
                    kurzbeschrieb=mandat.kurzbeschrieb or '',
                    vermieterin=mandat.vermieterin or '-',
                    verwaltung=mandat.verwaltung or '-',
                    frist=mandat.frist or '-',
                    verhandlungsdatum=mandat.verhandlungsdatum or '-',
                    interessiert_btn_color=interessiert_btn_color,
                    einzelmandat_details=get_einzelmandat_details(mandat),
                    status_pill=status_pill,
                    va_in_list=va_in_list,
                    interessiert_btn=interessiert_btn,
                    thema=mandat.themen or '-'
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
                m.`verwaltung`,
                m.`vermieterin`,
                m.`schlichtungsbehoerde`,
                GROUP_CONCAT(t.thema ORDER BY t.idx SEPARATOR '<br>') AS `themen`
            FROM `tabRSVMandat` m
            LEFT JOIN `tabRSV Thema MultiTable` t
                ON t.parent = m.name
            WHERE m.`publikation_per` >= CURDATE() - INTERVAL 7 DAY
            AND m.`publikation_per` <= CURDATE()
            AND m.`typ` IN ('EM', 'KGM')
            ORDER BY m.`publikation_per` ASC, `typ` ASC
        """,
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
def add_va(mandat, bemerkung):
    ml = frappe.get_doc("RSVMandat", mandat)
    row = ml.append("va_vergabe", {})
    row.va_user = frappe.session.user
    row.remarks = bemerkung
    ml.save(ignore_permissions=True)
    return

@frappe.whitelist()
def remove_va(mandat):
    ml = frappe.get_doc("RSVMandat", mandat)
    for va in ml.va_vergabe:
        if va.va_user == frappe.session.user:
            ml.remove(va)
    ml.save(ignore_permissions=True)
    return

def is_va_already_in_list(mandat):
    qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabVA Vergabe TBL` WHERE `parent` = '{0}' AND `va_user` = '{1}'""".format(mandat, frappe.session.user), as_dict=True)[0].qty
    if qty > 0: return True
    return False
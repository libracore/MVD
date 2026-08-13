from __future__ import unicode_literals
import frappe

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
            qty = frappe.db.count('RSVMitglied', filters = dict(rsvmandatsliste=details.name, status='Geprüft'))
        if details.typ == 'EM':
            qty = 1
        
        if qty < 1: return False

        va_badge = ''
        va_in_list = is_va_already_in_list(details.name)
        if va_in_list:
            va_badge = '<span class="badge open">✔</span>'

        card_template = """
            <article class="case-card" data-mandatsliste="{mandatsliste}" data-mandatslistentyp="{typ}" onclick="show_detail_card('{mandatsliste}')">
                <div class="badges">
                    <span class="badge">{mandatsliste}</span>
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
                   mandatsliste=details.name, typ=details.typ, qty=qty, va_badge=va_badge,
                   frist=details.frist or '-')

        return card_template
    
    def get_detail_card(mandatsliste):
        def get_einzelmandat_details(mandatsliste):
            return_data = """"""

            einzelmandat_template = """
                <div class="section">
                    <h4>Mandat {loop} - {thema}</h4>
                    <table style="width: 50%;">
                        <tr>
                            <td>Name Mietpartei</td>
                            <td>{vermieterin}</td>
                        </tr>
                        <tr>
                            <td>Name Gegenpartei</td>
                            <td>{verwaltung}</td>
                        </tr>
                        <tr>
                            <td>Frist</td>
                            <td>{frist}</td>
                        </tr>
                        <tr>
                            <td>Verhandlungsdatum</td>
                            <td>{verhandlungsdatum}</td>
                        </tr>
                        <tr>
                            <td>Bezirk</td>
                            <td>{bezirk}</td>
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
                        m.*,
                        GROUP_CONCAT(t.thema ORDER BY t.idx SEPARATOR ', ') AS themen
                    FROM `tabRSVMitglied` m
                    LEFT JOIN `tabRSV Thema MultiTable` t
                        ON t.parent = m.name
                    WHERE m.rsvmandatsliste = '{0}'
                    AND m.status = 'Geprüft'
                    GROUP BY m.name
                """.format(mandatsliste.name),
                as_dict=True
            )

            loop = 1
            for einzelmandat in einzelmandate:
                return_data += einzelmandat_template.format(beschreibung=einzelmandat.beschreibung or '-', bezirk=einzelmandat.bezirk or '-',
                                                            loop=loop, thema=einzelmandat.themen or '', frist=mandatsliste.frist or '-',
                                                            verhandlungsdatum=mandatsliste.verhandlungsdatum or '-',
                                                            vermieterin=einzelmandat.vermieterin or '-', verwaltung=einzelmandat.verwaltung or '-')
                loop += 1
            
            return return_data
        
        if mandatsliste.typ == 'KGM':
            qty = frappe.db.count('RSVMitglied', filters = dict(rsvmandatsliste=mandatsliste.name, status='Geprüft'))
        if mandatsliste.typ == 'EM':
            qty = 1
        
        status_pill = '<span class="status-pill">Offen für Interesse</span>'
        interessiert_btn = 'Ja, ich bin interessiert'
        interessiert_btn_color = 'primary'
        va_in_list = is_va_already_in_list(mandatsliste.name)
        if va_in_list:
            status_pill = '<span class="status-pill">Interesse bereits hinterlegt</span>'
            interessiert_btn = 'kein Interesse'
            interessiert_btn_color = 'danger'

        detail_card_template = """
            <section class="detail hidden" data-belongstomandatsliste="{mandatsliste}">
                <div class="detail-header">
                    <div>
                        <h2>{titel}</h2>
                        <p class="detail-subtitle">
                        {kurzbeschrieb}
                        </p>
                    </div>
                    {status_pill}
                </div>

                <div class="info-grid">
                    <div class="info-box">
                        <strong>Anz. Einzelmandate</strong>
                        {qty}
                    </div>
                    <div class="info-box">
                        <strong>Typ</strong>
                        {typ}
                    </div>
                    <div class="info-box">
                        <strong>Frist</strong>
                        {frist}
                    </div>
                    <div class="info-box">
                        <strong>Sprache</strong>
                        {language}
                    </div>
                </div>

                {einzelmandat_details}

                <div class="interest-box">
                    <h3>Interesse hinterlegen</h3>

                    <label for="message">Nachricht / Bemerkung</label>
                    <textarea id="message-{mandatsliste}" placeholder="Kurze Bemerkung zu Kapazität, Erfahrung oder Rückfragen..."></textarea>

                    <div class="actions">
                        <button class="btn-{interessiert_btn_color}" onclick="take('{mandatsliste}', '{va_in_list}')">{interessiert_btn}</button>
                    </div>
                </div>
            </section>
        """.format(mandatsliste=mandatsliste.name, titel=mandatsliste.bezeichnung or mandatsliste.name,
                   language=mandatsliste.language or 'Deutsch', qty=qty, typ=mandatsliste.typ, kurzbeschrieb=mandatsliste.kurzbeschrieb or '',
                   frist=mandatsliste.frist or '-', verhandlungsdatum=mandatsliste.verhandlungsdatum or '-', interessiert_btn_color=interessiert_btn_color,
                   einzelmandat_details=get_einzelmandat_details(mandatsliste), status_pill=status_pill, va_in_list=va_in_list, interessiert_btn=interessiert_btn)

        return detail_card_template
    
    mandatslisten = frappe.db.sql(
        """
            SELECT
                `name`,
                `bezeichnung`,
                `typ`,
                `publikation_per`,
                `language`,
                `kurzbeschrieb`,
                `frist`,
                `verhandlungsdatum`
            FROM `tabRSVMandatsliste`
            WHERE `publikation_per` >= CURDATE() - INTERVAL 7 DAY
            AND `publikation_per` <= CURDATE()
            AND `typ` IN ('EM', 'KGM')
        """,
        as_dict=True
    )
    
    cards = []
    detail_cards = []
    for mandatsliste in mandatslisten:
        card = get_card(mandatsliste)
        if card:
            cards.append(card)
            detail_cards.append(get_detail_card(mandatsliste))
    
    return cards, detail_cards

@frappe.whitelist()
def add_va(mandatsliste, bemerkung):
    ml = frappe.get_doc("RSVMandatsliste", mandatsliste)
    row = ml.append("va_vergabe", {})
    row.va_user = frappe.session.user
    row.remarks = bemerkung
    ml.save(ignore_permissions=True)
    return

@frappe.whitelist()
def remove_va(mandatsliste):
    ml = frappe.get_doc("RSVMandatsliste", mandatsliste)
    for va in ml.va_vergabe:
        if va.va_user == frappe.session.user:
            ml.remove(va)
    ml.save(ignore_permissions=True)
    return

def is_va_already_in_list(mandatsliste):
    qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabVA Vergabe TBL` WHERE `parent` = '{0}' AND `va_user` = '{1}'""".format(mandatsliste, frappe.session.user), as_dict=True)[0].qty
    if qty > 0: return True
    return False
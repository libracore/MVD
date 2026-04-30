// Copyright (c) 2026, libracore AG and contributors
// For license information, please see license.txt
frappe.provide("mvd_vorlagen_baum.ui");

// Unterstützte Werte für Parameter purpose:
// email -> Zeigt nur E-Mail-Templates an
// druck -> Zeigt nur Druckvorlagen an
// dokument -> Zeigt nur Dokumentenvorlagen an

mvd_vorlagen_baum.ui.VorlagenBaumNavigator = class VorlagenBaumNavigator {
    constructor(opts) {
        this.wrapper = opts.wrapper;
        this.sektion_id = opts.sektion_id || null;
        this.purpose = opts.purpose || null;
        this.on_select = opts.on_select || function() {};
        this.parent_dialog = opts.parent_dialog || null;

        this.current_parent_name = null;
        this.path = [];
        this.is_search_mode = false;

        this.make();
    }

    make() {
        this.wrapper.html(`
            <div class="vorlagen-baum-browser">
                <div class="vb-toolbar" style="margin-bottom: 15px;">
                    <button class="btn btn-default btn-sm btn-root">Alles Schliessen</button>

                    <span style="margin-left: 12px;">
                        <input type="text"
                               class="form-control input-xs vb-search-input"
                               placeholder="Baum durchsuchen..."
                               style="display:inline-block; width:240px;">
                    </span>

                    <button class="btn btn-default btn-sm vb-search-btn" style="margin-left: 6px;">Suchen</button>

                    <span class="vb-breadcrumbs" style="margin-left: 12px;"></span>
                </div>

                <div class="vb-layout" style="display:flex; gap:20px; align-items:flex-start;">
                    <div class="vb-left" style="flex:1; min-width:320px;">
                        <div class="vb-list"></div>
                    </div>
                    <div class="vb-right" style="flex:1; min-width:320px;">
                        <div class="vb-details text-muted">Bitte einen Knoten wählen.</div>
                    </div>
                </div>
            </div>
        `);

        this.$root_btn = this.wrapper.find(".btn-root");
        this.$search_input = this.wrapper.find(".vb-search-input");
        this.$search_btn = this.wrapper.find(".vb-search-btn");
        this.$breadcrumbs = this.wrapper.find(".vb-breadcrumbs");
        this.$list = this.wrapper.find(".vb-list");
        this.$details = this.wrapper.find(".vb-details");

        this.bind_events();
        this.load_children(null, []);
    }

    bind_events() {
        this.$root_btn.on("click", () => {
            this.is_search_mode = false;
            this.$search_input.val("");
            this.load_children(null, []);
            this.clear_details();
        });

        this.$search_btn.on("click", () => {
            this.run_search();
        });

        this.$search_input.on("keypress", (e) => {
            if (e.which === 13) {
                this.run_search();
            }
        });
    }

    clear_details() {
        this.$details.html(`<div class="text-muted">Bitte einen Knoten wählen.</div>`);
    }

    load_children(parent_name, path) {
        frappe.call({
            method: "mvd.mvd.utils.vorlagen_baum.vorlagen_baum.get_children",
            args: {
                parent_name: parent_name,
                sektion_id: this.sektion_id
            },
            callback: (r) => {
                const rows = r.message || [];
                this.current_parent_name = parent_name;
                this.path = path || [];
                this.is_search_mode = false;
                this.render_list(rows);
                this.render_breadcrumbs();
            }
        });
    }

    run_search() {
        const query = (this.$search_input.val() || "").trim();

        if (!query) {
            this.is_search_mode = false;
            this.load_children(this.current_parent_name, this.path);
            return;
        }

        frappe.call({
            method: "mvd.mvd.utils.vorlagen_baum.vorlagen_baum.search_nodes",
            args: {
                query: query,
                sektion_id: this.sektion_id,
                purpose: this.purpose,
                limit: 30
            },
            callback: (r) => {
                const rows = r.message || [];
                this.is_search_mode = true;
                this.render_search_results(rows, query);
                this.$breadcrumbs.html(
                    `<span class="text-muted">Suchergebnisse für: ${frappe.utils.escape_html(query)}</span>`
                );
                this.clear_details();
            }
        });
    }

    render_breadcrumbs() {
        if (this.is_search_mode) {
            return;
        }

        let html = `<a href="#" class="vb-crumb" data-index="-1">Basis</a>`;

        this.path.forEach((item, idx) => {
            html += ` <span class="text-muted">/</span> `;
            html += `<a href="#" class="vb-crumb" data-index="${idx}">${frappe.utils.escape_html(item.label)}</a>`;
        });

        this.$breadcrumbs.html(html);

        this.$breadcrumbs.find(".vb-crumb").on("click", (e) => {
            e.preventDefault();

            const idx = parseInt($(e.currentTarget).attr("data-index"), 10);

            if (idx === -1) {
                this.is_search_mode = false;
                this.load_children(null, []);
                this.clear_details();
                return;
            }

            const new_path = this.path.slice(0, idx + 1);
            const parent = new_path[new_path.length - 1];

            this.is_search_mode = false;
            this.load_children(parent.name, new_path);
            this.clear_details();
        });
    }

    render_list(rows) {
        if (!rows.length) {
            this.$list.html(`
                <div class="text-muted" style="padding:12px; border:1px solid #d1d8dd; border-radius:6px;">
                    Keine Einträge gefunden.
                </div>
            `);
            return;
        }

        const html = rows.map(row => `
            <div class="vb-row"
                 data-name="${frappe.utils.escape_html(row.name)}"
                 data-label="${frappe.utils.escape_html(row.label)}"
                 data-is-group="${row.is_group}"
                 style="padding:12px; margin-bottom:10px; border:1px solid #d1d8dd; border-radius:6px; background:#fff;">

                <div style="display:flex; justify-content:space-between; gap:10px; align-items:flex-start;">
                    <div class="vb-open" style="cursor:pointer; flex:1;">
                        <div style="font-weight:600;">
                            ${frappe.utils.escape_html(row.label)}
                        </div>
                        <div class="text-muted" style="margin-top:4px; font-size:12px;">
                            ${row.is_group ? "Gruppenknoten" : "Endknoten"}
                            ${row.sektion_id ? " · Sektion: " + frappe.utils.escape_html(row.sektion_id) : ""}
                        </div>
                        <div style="margin-top:6px;">
                            ${row.use_for_email ? '<span class="label label-default" style="margin-right:4px;">E-Mail</span>' : ''}
                            ${row.use_for_druckvorlagen ? '<span class="label label-default" style="margin-right:4px;">Druck</span>' : ''}
                            ${row.use_for_dokumentenvorlagen ? '<span class="label label-default">Dokument</span>' : ''}
                        </div>
                    </div>

                    <div style="white-space:nowrap;">
                        <button class="btn btn-xs btn-default vb-details-btn">Details</button>
                    </div>
                </div>
            </div>
        `).join("");

        this.$list.html(html);

        this.$list.find(".vb-row").each((i, el) => {
            const $row = $(el);
            const name = $row.attr("data-name");
            const label = $row.attr("data-label");
            const is_group = cint($row.attr("data-is-group"));

            $row.find(".vb-open").on("click", () => {
                if (is_group) {
                    const new_path = this.path.concat([{ name: name, label: label }]);
                    this.load_children(name, new_path);
                    this.clear_details();
                } else {
                    this.load_details(name, false);
                }
            });

            $row.find(".vb-details-btn").on("click", () => {
                this.load_details(name, false);
            });
        });
    }

    render_search_results(rows, query) {
        if (!rows.length) {
            this.$list.html(`
                <div class="text-muted" style="padding:12px; border:1px solid #d1d8dd; border-radius:6px;">
                    Keine Treffer für "${frappe.utils.escape_html(query)}".
                </div>
            `);
            return;
        }

        const html = rows.map(row => `
            <div class="vb-row"
                 data-name="${frappe.utils.escape_html(row.name)}"
                 data-label="${frappe.utils.escape_html(row.label)}"
                 data-is-group="${row.is_group}"
                 style="padding:12px; margin-bottom:10px; border:1px solid #d1d8dd; border-radius:6px; background:#fff;">

                <div style="display:flex; justify-content:space-between; gap:10px; align-items:flex-start;">
                    <div class="vb-search-open" style="cursor:pointer; flex:1;">
                        <div style="font-weight:600;">
                            ${frappe.utils.escape_html(row.label)}
                        </div>
                        <div class="text-muted" style="margin-top:4px; font-size:12px;">
                            ${row.is_group ? "Gruppenknoten" : "Endknoten"}
                            ${row.sektion_id ? " · Sektion: " + frappe.utils.escape_html(row.sektion_id) : ""}
                        </div>
                        <div style="margin-top:6px;">
                            ${row.use_for_email ? '<span class="label label-default" style="margin-right:4px;">E-Mail</span>' : ''}
                            ${row.use_for_druckvorlagen ? '<span class="label label-default" style="margin-right:4px;">Druck</span>' : ''}
                            ${row.use_for_dokumentenvorlagen ? '<span class="label label-default">Dokument</span>' : ''}
                        </div>
                        ${row.match_label && row.match_value ? `
                            <div class="text-muted" style="margin-top:6px; font-size:12px;">
                                Treffer in ${frappe.utils.escape_html(row.match_label)}:
                                <strong>${frappe.utils.escape_html(row.match_value)}</strong>
                            </div>
                        ` : ''}
                    </div>

                    <div style="white-space:nowrap;">
                        <button class="btn btn-xs btn-default vb-search-details-btn">Details</button>
                    </div>
                </div>
            </div>
        `).join("");

        this.$list.html(html);

        this.$list.find(".vb-row").each((i, el) => {
            const $row = $(el);
            const name = $row.attr("data-name");

            $row.find(".vb-search-open, .vb-search-details-btn").on("click", () => {
                this.load_details(name, false);
            });
        });
    }

    load_details(node_name, auto_open_children) {
        frappe.call({
            method: "mvd.mvd.utils.vorlagen_baum.vorlagen_baum.get_node_details",
            args: {
                node_name: node_name
            },
            callback: (r) => {
                const details = r.message;
                this.render_details(details);

                if (auto_open_children && details.is_group) {
                    const new_path = this.path.concat([{ name: details.name, label: details.label }]);
                    this.load_children(details.name, new_path);
                }
            }
        });
    }

    trigger_item_select(payload, details, selected_row) {
        this.on_select(payload, details, selected_row, this.parent_dialog);
    }

    show_email_section(details) {
        if (this.purpose && this.purpose !== "email") {
            return false;
        }
        return !!details.use_for_email;
    }

    show_druck_section(details) {
        if (this.purpose && this.purpose !== "druck") {
            return false;
        }
        return !!details.use_for_druckvorlagen;
    }

    show_dokument_section(details) {
        if (this.purpose && this.purpose !== "dokument") {
            return false;
        }
        return !!details.use_for_dokumentenvorlagen;
    }

    render_details(details) {
        let html = `
            <div style="border:1px solid #d1d8dd; border-radius:6px; padding:14px; background:#fff;">
                <div style="display:flex; justify-content:space-between; gap:10px; align-items:flex-start;">
                    <div>
                        <div style="font-size:18px; font-weight:600;">
                            ${frappe.utils.escape_html(details.label)}
                        </div>
                        <div class="text-muted" style="margin-top:4px;">
                            Name: ${frappe.utils.escape_html(details.name)}
                        </div>
                        <div class="text-muted">
                            Sektion: ${details.sektion_id ? frappe.utils.escape_html(details.sektion_id) : "-"}
                        </div>
                    </div>
                </div>

                <hr style="margin:12px 0;">

                <div style="margin-bottom:8px;">
                    <strong>Typ:</strong> ${details.is_group ? "Gruppenknoten" : "Endknoten"}
                </div>

                <div style="margin-bottom:12px;">
                    <strong>Aktiver Bereich:</strong>
                    ${this.show_email_section(details) ? '<span class="label label-default" style="margin-left:6px;">E-Mail</span>' : ''}
                    ${this.show_druck_section(details) ? '<span class="label label-default" style="margin-left:6px;">Druckvorlagen</span>' : ''}
                    ${this.show_dokument_section(details) ? '<span class="label label-default" style="margin-left:6px;">Dokumentenvorlagen</span>' : ''}
                </div>

                <div class="vb-extra-sections"></div>
            </div>
        `;

        this.$details.html(html);

        const $extra = this.$details.find(".vb-extra-sections");

        if (this.show_email_section(details)) {
            $extra.append(this.render_email_section(details.email_vorlagen || []));
        }

        if (this.show_druck_section(details)) {
            $extra.append(this.render_druck_section(details.druckvorlagen || []));
        }

        if (this.show_dokument_section(details)) {
            $extra.append(this.render_dokument_section(details.dokumentenvorlagen || []));
        }

        this.$details.find(".vb-doc-link").on("click", function(e) {
            e.preventDefault();

            const doctype = $(this).attr("data-doctype");
            const name = $(this).attr("data-name");

            const route = `/desk#Form/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`;
            window.open(route, "_blank");
        });

        this.$details.find(".vb-item-select-btn").on("click", (e) => {
            e.preventDefault();

            const $item = $(e.currentTarget).closest(".vb-selectable-item");
            const selection_type = $item.attr("data-selection-type");
            const selection_doctype = $item.attr("data-selection-doctype");
            const selection_name = $item.attr("data-selection-name");
            const row_index = cint($item.attr("data-row-index"));

            let selected_row = null;

            if (selection_type === "email_vorlage") {
                selected_row = (details.email_vorlagen || [])[row_index] || null;
            } else if (selection_type === "druckvorlage") {
                selected_row = (details.druckvorlagen || [])[row_index] || null;
            } else if (selection_type === "dokumentenvorlage") {
                selected_row = (details.dokumentenvorlagen || [])[row_index] || null;
            }

            this.trigger_item_select({
                selection_type: selection_type,
                selection_doctype: selection_doctype,
                selection_name: selection_name,
                node_name: details.name,
                node_label: details.label,
                sektion_id: details.sektion_id
            }, details, selected_row);
        });
    }

    render_email_section(rows) {
        let html = `
            <div style="margin-top:18px;">
                <h5 style="margin-bottom:8px;">E-Mail Vorlagen</h5>
        `;

        if (!rows.length) {
            html += `<div class="text-muted">Keine E-Mail Vorlagen vorhanden.</div></div>`;
            return html;
        }

        rows.forEach((row, idx) => {
            const value = row.email_template || "";
            html += `
                <div class="vb-selectable-item"
                     data-selection-type="email_vorlage"
                     data-selection-doctype="Email Template"
                     data-selection-name="${frappe.utils.escape_html(value)}"
                     data-row-index="${idx}"
                     style="padding:10px; border:1px solid #e1e4e8; border-radius:6px; margin-bottom:8px; background:#fafbfc;">
                    <div style="display:flex; justify-content:space-between; gap:10px; align-items:flex-start;">
                        <div>
                            ${this.render_link_row("Email Template", value)}
                        </div>
                        <div style="white-space:nowrap;">
                            <button class="btn btn-xs btn-primary vb-item-select-btn">Auswählen</button>
                        </div>
                    </div>
                </div>
            `;
        });

        html += `</div>`;
        return html;
    }

    render_druck_section(rows) {
        let html = `
            <div style="margin-top:18px;">
                <h5 style="margin-bottom:8px;">Druckvorlagen</h5>
        `;

        if (!rows.length) {
            html += `<div class="text-muted">Keine Druckvorlagen vorhanden.</div></div>`;
            return html;
        }

        rows.forEach((row, idx) => {
            const value = row.druckvorlage || "";
            html += `
                <div class="vb-selectable-item"
                     data-selection-type="druckvorlage"
                     data-selection-doctype="Druckvorlage"
                     data-selection-name="${frappe.utils.escape_html(value)}"
                     data-row-index="${idx}"
                     style="padding:10px; border:1px solid #e1e4e8; border-radius:6px; margin-bottom:8px; background:#fafbfc;">
                    <div style="display:flex; justify-content:space-between; gap:10px; align-items:flex-start;">
                        <div>
                            ${this.render_link_row("Druckvorlage", value)}
                        </div>
                        <div style="white-space:nowrap;">
                            <button class="btn btn-xs btn-primary vb-item-select-btn">Auswählen</button>
                        </div>
                    </div>
                </div>
            `;
        });

        html += `</div>`;
        return html;
    }

    render_dokument_section(rows) {
        let html = `
            <div style="margin-top:18px;">
                <h5 style="margin-bottom:8px;">Dokumentenvorlagen</h5>
        `;

        if (!rows.length) {
            html += `<div class="text-muted">Keine Dokumentenvorlagen vorhanden.</div></div>`;
            return html;
        }

        rows.forEach((row, idx) => {
            const value = row.dokumentenvorlage || "";
            html += `
                <div class="vb-selectable-item"
                     data-selection-type="dokumentenvorlage"
                     data-selection-doctype="Dokumentenvorlage"
                     data-selection-name="${frappe.utils.escape_html(value)}"
                     data-row-index="${idx}"
                     style="padding:10px; border:1px solid #e1e4e8; border-radius:6px; margin-bottom:8px; background:#fafbfc;">
                    <div style="display:flex; justify-content:space-between; gap:10px; align-items:flex-start;">
                        <div>
                            ${this.render_link_row("Dokumentenvorlage", value)}
                        </div>
                        <div style="white-space:nowrap;">
                            <button class="btn btn-xs btn-primary vb-item-select-btn">Auswählen</button>
                        </div>
                    </div>
                </div>
            `;
        });

        html += `</div>`;
        return html;
    }

    render_link_row(doctype, value) {
        if (!value) {
            return `<div class="text-muted">kein Eintrag</div>`;
        }

        return `
            <div>
                <a href="#"
                   class="vb-doc-link"
                   data-doctype="${frappe.utils.escape_html(doctype)}"
                   data-name="${frappe.utils.escape_html(value)}"
                   style="font-weight:500;">
                    ${frappe.utils.escape_html(value)}
                </a>
            </div>
        `;
    }
};
// Node-Tests der tatsächlichen Frappe-Client-Scripts, ohne Browser/Site.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

let selected = [];
let calls = [];
let confirmations = [];
let messages = [];
const actions = {};
const forms = {};
const frappe = {
    listview_settings: {},
    ui: {form: {on: function(name, definition) { forms[name] = definition; }}},
    call: function(options) { calls.push(options); },
    confirm: function(message, callback) { confirmations.push(callback); },
    msgprint: function(message) { messages.push(message); },
    set_route: function() {}
};
const context = {frappe: frappe, __: function(value, args) {
    return value.replace(/\{(\d+)\}/g, function(match, index) { return args ? args[index] : match; });
}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'rechnungsbereinigung_fall',
    'rechnungsbereinigung_fall_list.js'), 'utf8'), context);
const list = {
    get_checked_items: function() { return selected; },
    page: {add_action_item: function(label, callback) { actions[label] = callback; }},
    refresh: function() {}
};
frappe.listview_settings['Rechnungsbereinigung Fall'].onload(list);

selected = [{name: 'CASE-1', prueflauf: 'RUN-1'}];
actions.Freigeben();
assert.strictEqual(calls.length, 0, 'Ohne Bestätigung keine Freigabe');
confirmations.pop()();
assert.strictEqual(calls[0].args.confirmed, 1);
assert.strictEqual(calls[0].args.approve, 1);
assert.strictEqual(calls[0].args.background, 1);
assert.strictEqual(calls[0].args.names[0], 'CASE-1');
assert.ok(calls[0].method.endsWith('review_cases'));

calls = [];
actions['Technisch prüfen']();
assert.strictEqual(calls[0].args.approve, 0);
assert.strictEqual(calls[0].args.confirmed, 0);

calls = [];
selected = [{name: 'CASE-1', prueflauf: 'RUN-1'}, {name: 'CASE-2', prueflauf: 'RUN-2'}];
actions.Freigeben();
assert.strictEqual(calls.length, 0, 'Keine gemischten Prüfläufe');
assert.ok(messages.length > 0);

selected = Array.from({length: 5001}, function(unused, index) {
    return {name: 'CASE-' + index, prueflauf: 'RUN-1'};
});
actions['Technisch prüfen']();
assert.strictEqual(calls.length, 0, 'Auswahlgrenze wird geprüft');

selected = Array.from({length: 2300}, function(unused, index) {
    return {name: 'CASE-' + index, prueflauf: 'RUN-1'};
});
actions.Freigeben();
assert.strictEqual(calls.length, 0);
confirmations.pop()();
assert.strictEqual(calls[0].args.names.length, 2300);
assert.strictEqual(calls[0].args.background, 1);
calls[0].callback({message: {queued: true, anzahl: 2300, prueflauf: 'RUN-1'}});
calls = [];

selected = [{name: 'CASE-1', prueflauf: 'RUN-1'}];
actions['Freigegebene bereinigen']();
assert.strictEqual(calls.length, 0, 'Ohne Bestätigung keine Bereinigung');
confirmations.pop()();
assert.strictEqual(calls[0].args.name, 'RUN-1');
assert.strictEqual(calls[0].args.confirmed, 1);
assert.ok(calls[0].method.endsWith('start_cleanup'));

vm.runInNewContext(fs.readFileSync(path.join(__dirname, 'rechnungsbereinigung.js'), 'utf8'), context);
const buttons = {};
const properties = {};
let headline = '';
calls = [];
const frm = {
    doc: {name: 'RUN-1', status: 'Bereit', freigegeben: 2300},
    is_new: function() { return false; },
    set_df_property: function(field, property, value) { properties[field + '.' + property] = value; },
    add_custom_button: function(label, callback) { buttons[label] = callback; },
    reload_doc: function() {},
    dashboard: {set_headline_alert: function(value) { headline = value; }}
};
forms.Rechnungsbereinigung.refresh(frm);
assert.strictEqual(calls.length, 0, 'Öffnen des Prüflaufs bereinigt nichts');
buttons['Freigegebene Fälle bereinigen']();
assert.strictEqual(calls.length, 0);
confirmations.pop()();
assert.strictEqual(calls[0].args.confirmed, 1);
assert.strictEqual(calls[0].args.name, 'RUN-1');
calls = [];
frm.doc.status = 'Prüfung läuft';
frm.doc.verarbeitet = 100;
frm.doc.job_auswahl = JSON.stringify({art: 'freigabe', faelle: Array(2300).fill({name: 'CASE'})});
forms.Rechnungsbereinigung.refresh(frm);
assert.ok(headline.includes('100 von 2300'));
assert.ok(properties['verarbeitet.label'].includes('Freigabe'));
assert.strictEqual(calls.length, 0);
console.log('Client-Aktionen: Freigabe, Stapelbereinigung und Auswahlgrenzen OK');

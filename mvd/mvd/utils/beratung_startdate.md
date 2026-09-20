# Eingangsdatum bei E-Mail-Beratungen korrigieren

Anleitung zum Korrektur-Befehl `mvd.mvd.utils.beratung_startdate`.

## Worum es geht

Beratungen, die über ein Email Account mit **„Anhängen an" = Beratung** entstehen,
bekamen bis September 2026 ein falsches Datum im Feld **Eingang/Eröffnung Fall**
(`start_date`).

Frappe legt beim Mailabruf zuerst die Beratung an und setzt dabei **kein Datum** –
es greift der DocType-Default „Today", also der Zeitpunkt des **Postfach-Abrufs**
statt des tatsächlichen Mail-Eingangs. Eine Mail von 23:50 Uhr, die erst nach
Mitternacht abgeholt wird, landet dadurch auf dem Folgetag. Dasselbe passiert,
wenn ältere Mails nachträglich abgeholt werden.

Weil der Dokumentname nach dem Muster `JJ-MM-TT-Nummer` gebildet wird, trägt auch
der Name das falsche Datum.

**Der Fehler selbst ist behoben** (in `beratung.py`, `check_communication()`):
neue Beratungen übernehmen das Datum aus dem `Date`-Header der Mail. Dieser Befehl
ist ausschliesslich für die **Altfälle** da.

## Voraussetzungen

* Zugriff auf die Bench (`~/frappe-bench`)
* Ein aktuelles Datenbank-Backup, bevor scharf gelaufen wird
* Bei grösseren Mengen: ausserhalb der Arbeitszeiten, weil Umbenennungen viele
  Tabellen anfassen

## Ablauf

### 1. Probelauf

Der Probelauf schreibt **nichts** ausser dem Protokoll-CSV.

```bash
cd ~/frappe-bench
bench --site site1.local execute mvd.mvd.utils.beratung_startdate.korrigiere \
  --kwargs "{'sektion': 'MVZH', 'dry_run': True}"
```

Ausgabe:

```
Kandidaten: 42  (dry_run=True, rename=True)
Datum korrigiert  : 42
Umbenannt         : 42
Rename ausgelassen: 0
Fehler            : 0
Protokoll         : ./site1.local/private/files/beratung_startdate_probelauf_2026-09-20_143015.csv
```

### 2. Protokoll prüfen

Das CSV liegt unter `sites/<site>/private/files/` und lässt sich direkt in Excel
öffnen (Semikolon-getrennt, UTF-8 mit BOM). Spalten:

| Spalte | Bedeutung |
| --- | --- |
| `beratung_alt` / `beratung_neu` | Name vorher / nachher |
| `start_date_alt` / `start_date_neu` | Datum vorher / nachher |
| `diff_tage` | Abweichung in Tagen |
| `sektion_id` | Sektion der Beratung |
| `communication` | die Mail, die die Beratung erzeugt hat |
| `mail_datum` | `Date`-Header dieser Mail |
| `mail_absender`, `mail_betreff`, `mail_message_id` | zur Identifikation der Mail |
| `email_account` | Postfach, über das sie kam |
| `absender_ist_raised_by` | Plausibilitätsprüfung: stimmt der Absender mit dem Feld „Gemeldet von" überein? |
| `an_sp_gemeldet` | wurde die Beratung an die Service Plattform gemeldet? |
| `aktion` | was gemacht wird bzw. wurde |
| `fehler` | Fehlermeldung, falls etwas schiefging |

Stichprobe: eine Beratung im Libracore öffnen, die verknüpfte Mail ansehen und
prüfen, ob `mail_datum` zum tatsächlichen Eingang passt.

### 3. Scharf laufen lassen

Bei grösseren Mengen in Tranchen, damit man bei einem Fehler nicht alles auf
einmal zu prüfen hat:

```bash
bench --site site1.local execute mvd.mvd.utils.beratung_startdate.korrigiere \
  --kwargs "{'sektion': 'MVZH', 'dry_run': False, 'limit': 50}"
```

Den Aufruf wiederholen, bis „Kandidaten: 0" gemeldet wird.

### 4. Kontrolle

Der Befehl ist so gebaut, dass ein zweiter Lauf mit denselben Filtern nichts mehr
findet – korrigierte Beratungen sind keine Kandidaten mehr. Das ist die einfachste
Erfolgskontrolle.

## Filter

Alle Parameter sind kombinierbar.

| Parameter | Beispiel | Wirkung |
| --- | --- | --- |
| `sektion` | `'MVZH'` oder `['MVBE','MVLU']` | Sektion oder Liste von Sektionen |
| `von` / `bis` | `'2023-06-01'` / `'2023-12-31'` | Zeitraum des **Maildatums** |
| `start_von` / `start_bis` | `'2024-01-01'` | Zeitraum des bisherigen `start_date` |
| `min_diff` / `max_diff` | `1` / `5` | Abweichung in Tagen. Standard 1/1 = nur der Mitternachtsfall |
| `beratungen` | `['26-09-19-438039']` | nur diese Beratungen |
| `limit` | `50` | Tranchengrösse |
| `rename` | `False` | nur das Datum korrigieren, **nicht** umbenennen |
| `dry_run` | `False` | scharf schalten (Standard ist `True`) |
| `nur_systembenutzer` | `False` | auch von Hand angelegte Beratungen einbeziehen (normalerweise nicht gewollt) |
| `sp_versendete_umbenennen` | `True` | auch Beratungen umbenennen, die an die SP gemeldet wurden |
| `toleranz` | `120` | Sekundenfenster für „durch diese Mail erzeugt" |
| `zusatz_bedingung` | `"b.status = 'Closed'"` | freie SQL-Bedingung |

### Freie SQL-Bedingung

Wenn die Parameter nicht reichen, nimmt `zusatz_bedingung` einen rohen
SQL-Ausdruck für die WHERE-Klausel. Aliase: `b` = `tabBeratung`,
`c` = `tabCommunication` (die erzeugende Mail).

```
"c.sender LIKE '%@gmail.com'"
"b.status = 'Closed' AND b.beratungskategorie LIKE '202%'"
```

Der Ausdruck wird **ungeprüft** eingesetzt. Nur über die Bench aufrufbar, also
kein Risiko aus der Oberfläche – aber Tippfehler führen zu SQL-Fehlern.

Weil solche Ausdrücke Anführungszeichen enthalten, ist der direkte Python-Aufruf
bequemer als `bench execute`:

```bash
cd ~/frappe-bench/sites && ../env/bin/python -c "
import frappe; frappe.init(site='site1.local'); frappe.connect()
from mvd.mvd.utils.beratung_startdate import korrigiere
korrigiere(sektion='MVBE', zusatz_bedingung=\"c.sender LIKE '%@gmail.com'\", dry_run=True)
"
```

## Weitere Einstiegspunkte

| Aufruf | Zweck |
| --- | --- |
| `...beratung_startdate.korrigiere` | macht die Arbeit, Standard `dry_run=True` |
| `...beratung_startdate.zeige` | identisch, erzwingt aber den Probelauf |
| `...beratung_startdate.finde` | liefert nur die Kandidatenliste, ohne Protokoll |

## Was genau passiert

### Welche Mail zählt

Massgebend ist die Mail, die die Beratung **erzeugt** hat – nicht die älteste
verknüpfte Mail. Eine weitergeleitete Altkorrespondenz würde sonst ein falsches
Datum liefern. Erkannt wird sie an zwei Merkmalen:

* Frappe legt erst die Beratung an, dann die Communication. Die erzeugende Mail
  hat also die kleinste `creation`, und diese liegt nie vor der Beratung.
* Der Mailabruf läuft als Benutzer `Administrator`.

### Datum

`start_date` wird auf das Datum aus `communication_date` dieser Mail gesetzt, der
Titel gleich mit – er beginnt immer mit dem Datum.

Geschrieben wird bewusst **direkt in die Datenbank**, ohne die Beratung regulär zu
speichern. Ein reguläres Speichern würde `validate()` und `on_update()` auslösen,
dabei pro Beratung einen Siedlungsfall-Job einreihen und bei Beratungen abbrechen,
die heute nicht mehr validieren (etwa Termine ohne Mitgliedschaft).

### Umbenennung

Der Name wird nur im Datumsteil geändert, der Zähler bleibt:

```
26-09-20-438039  ->  26-09-19-438039
```

Der Zähler ist systemweit eindeutig, Namenskollisionen sind damit ausgeschlossen.
Die Umbenennung läuft über `frappe.rename_doc()` und zieht Link-Felder, Dynamic
Links, Child-Tabellen, Anhänge und Versionen mit.

Zusätzlich werden Referenzen nachgezogen, die `rename_doc()` **nicht** kennt, weil
sie nicht als Link modelliert sind:

* `Email Queue` (`reference_name` ist dort ein reines Textfeld)
* `Energy Point Log`, `Milestone`
* `Beratungs Log` (Feld `beratung` ist ein Textfeld)
* Kommentartexte mit hartem Link `#Form/Beratung/<name>`

## Wichtige Hinweise

**Die Service Plattform kennt den alten Namen.** Beratungen der Sektion MVZH werden
mit `beratungId = <Name der Beratung>` an die SP gemeldet. Wird eine solche Beratung
umbenannt, passt die ID dort nicht mehr. Der Befehl überspringt solche Beratungen
beim Umbenennen deshalb standardmässig und korrigiert nur das Datum. Mit
`sp_versendete_umbenennen=True` lässt sich das übersteuern – nur tun, wenn geklärt
ist, wie die SP mit `beratungId` umgeht.

**Nextcloud-Ordner werden nicht umbenannt.** Wo Nextcloud pro Sektion aktiv ist,
heissen die Beratungsordner nach dem Dokumentnamen. Vor einer Umbenennung prüfen,
ob `nc_enabled` bei den betroffenen Sektionen gesetzt ist; die Ordner müssten sonst
separat nachgezogen werden.

**Das Anlagedatum bleibt.** `creation` wird nicht verändert – der Datensatz weiss
weiterhin, wann er wirklich angelegt wurde. Abweichung zwischen `creation` und
`start_date` ist nach der Korrektur also normal und richtig.

**Umbenennen ist optional.** Wer nur das Datum korrigieren will, setzt
`rename=False`. Das ist der risikoärmere Weg: keine Fremdsystem-Referenzen, keine
Nextcloud-Ordner, keine geänderten Aktenzeichen in bereits versandter
Korrespondenz.

## Wenn etwas schiefgeht

* Jeder Fehler pro Beratung wird im Protokoll-CSV in der Spalte `fehler` vermerkt
  und zusätzlich ins Error Log geschrieben; der Lauf bricht nicht ab.
* Es gibt **keine automatische Rücknahme**. Die Korrektur lässt sich mit Hilfe des
  Protokolls von Hand rückgängig machen (`beratung_neu` → `beratung_alt`,
  `start_date_neu` → `start_date_alt`), das Backup ist aber der verlässlichere Weg.
* Deshalb: erst Probelauf, dann Backup, dann Tranchen.

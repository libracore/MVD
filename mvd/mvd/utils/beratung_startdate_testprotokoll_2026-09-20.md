# Testprotokoll: Eingangsdatum bei E-Mail-Beratungen

**Datum:** 2026-09-20
**System:** Entwickler-VM, Site `site1.local`
**Branch:** `beratung-start-date-aus-maildatum`
**Durchgeführt von:** Christoph Laszlo / Claude Code

## Ziel

Nachweisen, dass der Fehler ohne den Fix reproduzierbar ist und dass der
Korrektur-Befehl ihn behebt – insbesondere für Mails, die **Tage später**
abgeholt werden, nicht nur für den Mitternachtsfall.

## Aufbau

| | |
| --- | --- |
| Testpostfach | `test-beratung@mvd.mieterverband.ch` |
| Email Account | `append_to = Beratung`, `sektion_id = MVZH`, `default_incoming = 0`, `enable_auto_reply = 0` |
| Andere Incoming-Konten | keine aktiv (1 von 21 Email Accounts hat `enable_incoming = 1`) |
| Scheduler | pausiert (`pause_scheduler: 1`) – Abruf ausschliesslich manuell |
| Testmails | drei echte Mails mit `Date`-Header vom 2026-09-07 |

Abruf jeweils gezielt für dieses eine Konto:

```bash
bench --site site1.local execute \
  frappe.email.doctype.email_account.email_account.pull_from_email_account \
  --kwargs "{'email_account': 'test-beratung@mvd.mieterverband.ch'}"
```

## Ausgangslage (18:00:52)

| | |
| --- | --- |
| Beratungen gesamt | 76 775 |
| Beratungen MVZH | 15 477 |
| Communications | 112 848 |
| Letzte Beratung | `26-09-19-438039` |

## Schritt 1 – Fehler ohne Fix reproduzieren

Auf Branch **`Main`** gewechselt (dort fehlt der Fix, `grep -c
_get_mail_eingangsdatum` → 0) und die Bench neu gestartet, damit alle Prozesse
den alten Code laden.

Abruf 18:02:07 – 18:02:28. Ergebnis: **3 Beratungen, 3 Communications**.

| Beratung | Betreff | Maildatum (`Date`-Header) | Abruf | `start_date` | Abweichung |
| --- | --- | --- | --- | --- | --- |
| `26-09-20-438040` | Re: Ihre Email Anfrage vom 27.08.2026 | 2026-09-07 08:17:00 | 2026-09-20 18:02:10 | **2026-09-20** | 13 Tage |
| `26-09-20-438041` | Fwd: Rückmeldung zum Antrag der Mietzinsreduktion … | 2026-09-07 14:33:57 | 2026-09-20 18:02:20 | **2026-09-20** | 13 Tage |
| `26-09-20-438042` | Re: Nachricht aus Kontaktformular: Sonstiges | 2026-09-07 15:14:32 | 2026-09-20 18:02:25 | **2026-09-20** | 13 Tage |

**Der Fehler ist damit reproduziert:** Alle drei Beratungen tragen den Abruftag
statt des Maildatums, im Feld `start_date`, im Titel und im Dokumentnamen. Die
Abweichung von 13 Tagen zeigt, dass es nicht nur um den Mitternachtsfall geht.

Sektion wurde korrekt aus dem Email Account übernommen (MVZH), ebenso Absender
und Betreff.

## Schritt 2 – Zurück auf den Feature-Branch

Auf `beratung-start-date-aus-maildatum` gewechselt (Fix vorhanden,
Korrektur-Befehl vorhanden) und die Bench erneut neu gestartet.

## Schritt 3 – Probelauf

```bash
bench --site site1.local execute mvd.mvd.utils.beratung_startdate.korrigiere \
  --kwargs "{'beratungen': ['26-09-20-438040','26-09-20-438041','26-09-20-438042'], 'dry_run': True}"
```

```
Kandidaten: 3  (dry_run=True, rename=True)
Abweichung:
  8-30 Tage        3
  groesste: 13 Tage (26-09-20-438040, Maildatum 2026-09-07)
Datum korrigiert  : 3
Umbenannt         : 3
Rename ausgelassen: 0
Fehler            : 0
```

Protokoll: `beratung_startdate_probelauf_2026-09-20_180400.csv`

Alle drei Zeilen korrekt: `start_date_neu = 2026-09-07`, `diff_tage = 13`,
`sektion_id = MVZH`, `an_sp_gemeldet = nein`, `absender_ist_raised_by = ja`,
Zielnamen `26-09-07-4380xx`. Es wurde nichts geschrieben.

## Schritt 4 – Scharfer Lauf

Derselbe Aufruf mit `'dry_run': False`, 18:04:11 – 18:05:05.

```
Kandidaten: 3  (dry_run=False, rename=True)
Datum korrigiert  : 3
Umbenannt         : 3
Rename ausgelassen: 0
Fehler            : 0
```

Protokoll: `beratung_startdate_ausgefuehrt_2026-09-20_180505.csv`

## Schritt 5 – Prüfung

| Prüfung | 438040 | 438041 | 438042 |
| --- | --- | --- | --- |
| Alter Name entfernt | ✅ | ✅ | ✅ |
| Neuer Name `26-09-07-…` | ✅ | ✅ | ✅ |
| `start_date = 2026-09-07` | ✅ | ✅ | ✅ |
| Titel mitgezogen | ✅ | ✅ | ✅ |
| `creation` unverändert | ✅ | ✅ | ✅ |
| Mail hängt am neuen Namen | ✅ | ✅ | ✅ |
| Verwaiste Referenzen | 0 | 0 | 0 |

Auf Verwaisung geprüft wurden je Beratung neun Stellen: Communication, Comment,
Version, Email Queue, File, Beratungs Log, ToDo sowie die Child-Tabellen
`Beratung Termin` und `Beratungsdateien`.

Ein zweiter Durchlauf mit denselben Filtern findet **0 Kandidaten** – die
Korrektur ist also abgeschlossen und wiederholbar ohne Nebenwirkung.

## Ergebnis

**Beide Teile bestanden.**

1. Der Fehler tritt ohne den Fix zuverlässig auf und betrifft auch Mails, die
   Tage später abgeholt werden (hier 13 Tage).
2. Der Korrektur-Befehl stellt Datum, Titel und Dokumentnamen richtig und zieht
   sämtliche Referenzen mit, ohne etwas verwaisen zu lassen.

## Anmerkungen

* Die drei Testberatungen liegen in MVZH und sind nach dem Test unter
  `26-09-07-438040/438041/438042` erreichbar. Sie wurden bewusst nicht gelöscht.
* `enable_auto_reply` wurde auf dem Testkonto für den Test von 1 auf 0 gesetzt,
  damit die Entwicklungsumgebung keine echten Antwortmails verschickt. Der Wert
  steht weiterhin auf 0.
* Der Hook-Fix selbst wurde bereits am selben Tag separat bestätigt: Mail mit
  `Date`-Header 2026-09-19, Abruf am 2026-09-20, `start_date` = 2026-09-19.
* Ein Neustart der Bench erfolgt auf dieser VM **nicht** über `bench restart`
  (wirkungslos), sondern über Ctrl-C und `bench start` in der tmux-Session.

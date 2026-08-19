# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
import requests
import frappe

from frappe.model.document import Document
from frappe.utils import now


class SPDataTransferLog(Document):
    pass


ENDPOINT = "/api/method/mvd.mvd.service_plattform.api.mitglieder"


def transfer_service_plattform_logs(
    target_url,
    api_key=None,
    api_secret=None,
    from_date=None,
    limit=None
):
    """
    Überträgt noch nicht erfolgreich übertragene
    Service Plattform Logs von System A (z.B. Prod) nach System B (z.B. Test).

    Bereits erfolgreich übertragene Records werden anhand
    von SP Data Transfer Log.success = 1 übersprungen.

    Fehlerhafte Übertragungen werden bei einem späteren Lauf
    automatisch erneut versucht.

    Beispiel:

        bench --site system-a execute \
            mvd.mvd.utils.sp_data_transfer.transfer_service_plattform_logs \
            --kwargs "{
                'target_url': 'https://test.example.ch',
                'api_key': 'xxxx',
                'api_secret': 'xxxx',
                'from_date': '2026-08-01',
                'limit': 10
            }"
    """

    endpoint = "{0}{1}".format(
        target_url.rstrip("/"),
        ENDPOINT
    )

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    if api_key and api_secret:
        headers["Authorization"] = "token {0}:{1}".format(
            api_key,
            api_secret
        )

    records = get_records_to_transfer(
        from_date=from_date,
        limit=limit
    )

    total = len(records)

    print("")
    print("SP Data Transfer")
    print("================")
    print("Ziel:    {0}".format(endpoint))
    print("Records: {0}".format(total))
    print("")

    if not records:
        print("Keine Records zum Uebertragen vorhanden.")
        return

    success_count = 0
    error_count = 0

    with requests.Session() as session:
        session.headers.update(headers)

        for index, record in enumerate(records, 1):

            print(
                "[{0}/{1}] {2}".format(
                    index,
                    total,
                    record.name
                )
            )

            transfer_log = frappe.get_doc({
                "doctype": "SP Data Transfer Log",
                "sp_record": record.name,
                "success": 0,
                "transfer_date": now(),
                "transfer_data": record.json or ""
            })

            try:
                # -----------------------------------------------------
                # JSON prüfen
                # -----------------------------------------------------

                if not record.json:
                    raise Exception(
                        "Service Plattform Log enthaelt kein JSON."
                    )

                try:
                    payload = json.loads(record.json)
                    # Frappe-internes Routing-Feld entfernen.
                    # Dieses wurde beim ursprünglichen API-Aufruf automatisch
                    # in api_request aufgenommen und darf beim Replay nicht
                    # erneut als Request-Parameter gesendet werden.
                    payload.pop("cmd", None)
                except Exception as e:
                    raise Exception(
                        "Ungueltiges JSON: {0}".format(e)
                    )

                if not isinstance(payload, dict):
                    raise Exception(
                        "JSON Root muss ein Objekt/Dict sein."
                    )

                # -----------------------------------------------------
                # Request an System B
                # -----------------------------------------------------

                response = session.post(
                    endpoint,
                    json=payload,
                    timeout=60
                )

                transfer_log.http_status = response.status_code

                # -----------------------------------------------------
                # Erfolg
                # -----------------------------------------------------

                if response.status_code == 200:

                    transfer_log.success = 1
                    success_count += 1

                    print(
                        "    OK - HTTP {0}".format(
                            response.status_code
                        )
                    )

                # -----------------------------------------------------
                # Fehlerantwort von B
                # -----------------------------------------------------

                else:

                    transfer_log.success = 0
                    transfer_log.error = get_response_error(
                        response
                    )

                    error_count += 1

                    print(
                        "    FEHLER - HTTP {0}".format(
                            response.status_code
                        )
                    )

                    if transfer_log.error:
                        print(
                            "    {0}".format(
                                transfer_log.error[:500]
                            )
                        )

            # ---------------------------------------------------------
            # Request-, JSON-, Netzwerkfehler etc.
            # ---------------------------------------------------------

            except Exception as e:

                transfer_log.success = 0
                transfer_log.error = str(e)

                error_count += 1

                print(
                    "    FEHLER - {0}".format(e)
                )

            # ---------------------------------------------------------
            # Transferlog speichern
            # ---------------------------------------------------------

            try:
                transfer_log.insert(
                    ignore_permissions=True
                )

                # Absichtlich pro Datensatz committen.
                # Falls der Prozess später abbricht, bleiben alle bis
                # dahin protokollierten Transfers erhalten.
                frappe.db.commit()

            except Exception:

                frappe.db.rollback()

                print(
                    "    KRITISCH: Transferlog konnte nicht gespeichert werden."
                )

                frappe.log_error(
                    frappe.get_traceback(),
                    "SP Data Transfer Log Error"
                )

                raise

    # -----------------------------------------------------------------
    # Zusammenfassung
    # -----------------------------------------------------------------

    print("")
    print("================")
    print("Transfer beendet")
    print("----------------")
    print("Erfolgreich: {0}".format(success_count))
    print("Fehler:      {0}".format(error_count))
    print("Gesamt:      {0}".format(total))
    print("================")
    print("")


def get_records_to_transfer(from_date=None, limit=None):
    """
    Holt alle Service Plattform Logs, für die noch kein
    erfolgreicher SP Data Transfer Log existiert.

    NOT EXISTS wird verwendet, damit auch bei vielen Records
    keine grosse NOT-IN-Liste erzeugt wird.
    """

    conditions = []
    values = {}

    if from_date:
        conditions.append(
            "spl.`creation` >= %(from_date)s"
        )

        values["from_date"] = from_date

    additional_conditions = ""

    if conditions:
        additional_conditions = "AND {0}".format(
            " AND ".join(conditions)
        )

    limit_sql = ""

    if limit:
        limit_sql = "LIMIT {0}".format(
            int(limit)
        )

    return frappe.db.sql("""
        SELECT
            spl.`name`,
            spl.`creation`,
            spl.`json`
        FROM
            `tabService Plattform Log` spl
        WHERE
            NOT EXISTS (
                SELECT
                    1
                FROM
                    `tabSP Data Transfer Log` dtl
                WHERE
                    dtl.`sp_record` = spl.`name`
                    AND dtl.`success` = 1
            )
            AND spl.`status` = 'Done'
            {additional_conditions}
        ORDER BY
            spl.`creation` ASC,
            spl.`name` ASC
        {limit}
    """.format(
        additional_conditions=additional_conditions,
        limit=limit_sql
    ), values=values, as_dict=True)


def get_response_error(response):
    """
    Holt eine möglichst sinnvolle Fehlermeldung aus
    der Frappe-Response.

    Der raise_xxx() in System B setzt:
        frappe.local.response.http_status_code
        frappe.local.response.message

    Deshalb wird zuerst 'message' ausgewertet.
    """

    try:
        data = response.json()

    except Exception:
        return response.text or "HTTP {0}".format(
            response.status_code
        )

    # raise_xxx()
    if data.get("message"):
        message = data.get("message")

        if isinstance(message, (dict, list)):
            return json.dumps(
                message,
                indent=2,
                ensure_ascii=False
            )

        return str(message)

    # Typischer Frappe Exception Response
    if data.get("exc"):
        return str(
            data.get("exc")
        )

    if data.get("_server_messages"):
        return str(
            data.get("_server_messages")
        )

    # Falls nichts Bekanntes vorhanden ist
    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False
    )
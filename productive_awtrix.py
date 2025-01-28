#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Productive-AWTRIX Updater
=========================
Ein Python-Skript, das Daten aus der Productive-API abruft,
aufbereitet und an AWTRIX 3 schickt. Läuft alle 10 Minuten
mit Hilfe von APScheduler.

Voraussetzungen:
- requests
- python-dotenv
- APScheduler
- logging (Standard-Bibliothek)

.env-Datei mit folgenden Einträgen:
----------------------------------
PRODUCTIVE_API_KEY=<dein_api_key>
PRODUCTIVE_ORG_ID=<deine_organisation_id>
AWTRIX_IP=<ip_der_awtrix>
----------------------------------

Beispiel für .env:
----------------------------------
PRODUCTIVE_API_KEY=ad388f96-xxxx-xxxx-xxxx-c7a986ed74aa
PRODUCTIVE_ORG_ID=30971
AWTRIX_IP=192.168.0.100
----------------------------------

Start:
----------------------------------
pip install -r requirements.txt
python productive_awtrix.py
----------------------------------
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict

import requests
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

# -------------------------------------------------------------------
# Logger-Konfiguration
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# -------------------------------------------------------------------
# Globale Konfigurationen laden
# -------------------------------------------------------------------
load_dotenv()  # Lädt die .env-Datei

PRODUCTIVE_API_KEY = os.getenv("PRODUCTIVE_API_KEY")
PRODUCTIVE_ORG_ID = os.getenv("PRODUCTIVE_ORG_ID")
AWTRIX_IP = os.getenv("AWTRIX_IP")

if not (PRODUCTIVE_API_KEY and PRODUCTIVE_ORG_ID and AWTRIX_IP):
    logging.error("Fehlende .env-Konfiguration. Bitte PRODUCTIVE_API_KEY, "
                  "PRODUCTIVE_ORG_ID und AWTRIX_IP in .env setzen.")
    exit(1)

BASE_URL = "https://api.productive.io/api/v2/reports/"
AWTRIX_URL = f"http://{AWTRIX_IP}/api/custom?name=Productive_Report"

# Lokale Zwischenspeicherung für den Fall, dass AWTRIX nicht erreichbar ist
PENDING_DATA_FILE = "awtrix_pending_data.json"

# -------------------------------------------------------------------
# API-Parameter (kannst du natürlich dynamischer gestalten)
# -------------------------------------------------------------------
current_year = datetime.now().year
CONFIG = {
    "report_endpoint": "financial_item_reports",
    "filters": {
        "date": {
            "gt_eq": f"{current_year}-01-01",
            "lt_eq": f"{current_year}-12-31"
        }
    },
    "groups": ["organization", "date:year"],
    "pagination": {"page_size": 100},
    "fields": ["total_recognized_revenue", "total_cost", "total_recognized_profit"]
}

HEADERS = {
    "X-Auth-Token": PRODUCTIVE_API_KEY,
    "X-Organization-Id": PRODUCTIVE_ORG_ID,
    "Content-Type": "application/vnd.api+json"
}

# -------------------------------------------------------------------
# Hilfsfunktionen
# -------------------------------------------------------------------

def build_url(endpoint: str, filters: Dict, groups: List[str], pagination: Dict) -> str:
    """
    Baut die URL für den GET-Request an Productive zusammen.
    """
    filter_parts = []
    for index, (field, operations) in enumerate(filters.items()):
        for op, value in operations.items():
            filter_parts.append(f"filter[{index}][{field}][{op}]={value}")
    filter_parts.append("filter[$op]=and")
    filter_string = "&".join(filter_parts)
    group_string = ",".join(groups)
    pagination_string = (
        f"page[number]={pagination.get('page_number', 1)}&per_page={pagination['page_size']}"
    )

    url = f"{BASE_URL}{endpoint}"
    url += f"?{filter_string}&{pagination_string}&group={group_string}&report_currency=1&sort=date:year"
    return url

def fetch_all_data(config: dict) -> List[dict]:
    """
    Lädt alle Seiten der paginierten Productive-Antwort und gibt sie als Liste zurück.
    """
    endpoint = config["report_endpoint"]
    filters = config["filters"]
    groups = config["groups"]
    page = 1
    all_data = []

    while True:
        url = build_url(endpoint, filters, groups, {"page_size": 100, "page_number": page})
        try:
            logging.info(f"Rufe URL auf: {url}")
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()

            data = response.json()
            if not data.get("data"):
                break

            all_data.extend(data["data"])

            # Prüfen, ob es weitere Seiten gibt
            meta = data.get("meta", {}).get("pagination", {})
            total_pages = meta.get("total_pages", 1)

            if page >= total_pages:
                break

            page += 1

        except requests.exceptions.RequestException as e:
            logging.error(f"Fehler beim Abrufen der Productive-Daten: {e}")
            break
        except ValueError as e:
            logging.error(f"Fehler beim Verarbeiten der JSON-Daten: {e}")
            break

    return all_data

def format_data(raw_data: List[dict], fields: List[str]) -> List[dict]:
    """
    Filtert pro Eintrag nur die konfigurierten Felder heraus, rechnet ggf. in EUR um.
    Gibt eine Liste von Dicts mit den fertigen Werten zurück.
    """
    formatted = []
    for item in raw_data:
        attributes = item.get("attributes", {})
        single_entry = {}
        for field in fields:
            value = attributes.get(field, 0)
            try:
                # Angenommen: values kommen in Cent
                value_in_eur = value / 100
            except TypeError:
                value_in_eur = 0

            # Formatierung, z.B. 123456.78 -> "123,456.78"
            value_str = f"{value_in_eur:,.2f}"  # Kommagruppierung und 2 Nachkommastellen
            single_entry[field] = f"{value_str} EUR"
        formatted.append(single_entry)
    return formatted

def create_awtrix_payload(data: List[dict]) -> List[dict]:
    """
    Wandelt die formatierten Daten in das Format um,
    das AWTRIX 3 erwartet.

    Neu gewünscht:
    - pro Feldname ein eigenes Objekt (spalte)
    - pro Wert ein eigenes Objekt (wert)
    - 'text' = spaltenname / wert
    - 'noScroll' = False (Scroll ist an)
    - 'color' = #FFFFFF / #FFFF00
    - alle Objekte hintereinander in einem Array
    """
    payload = []
    for entry in data:
        for field_name, field_value in entry.items():
            # Feldname in weiß
            payload.append({
                "text": field_name,
                "duration": 5,
                "color": "#FFFFFF",
                "noScroll": False
            })
            # Feldwert in gelb
            payload.append({
                "text": field_value,
                "duration": 5,
                "color": "#FFFF00",
                "noScroll": False
            })
    return payload

def send_to_awtrix(payload: List[dict]) -> None:
    """
    Sendet das JSON-Array in einem POST-Request an die AWTRIX 3 API.
    Wenn AWTRIX nicht erreichbar ist, speichert das Skript die Payload
    in einer lokalen JSON-Datei, um sie beim nächsten Durchlauf erneut
    zu versuchen.
    """
    try:
        logging.info(f"Sende Daten an AWTRIX: {AWTRIX_URL}")
        response = requests.post(AWTRIX_URL, json=payload, timeout=5)
        response.raise_for_status()
        logging.info("Daten erfolgreich an AWTRIX gesendet.")
    except requests.exceptions.RequestException as e:
        logging.error(f"AWTRIX nicht erreichbar oder Fehler beim Senden: {e}")
        store_pending_data(payload)

def store_pending_data(payload: List[dict]) -> None:
    """
    Speichert das Payload in einer lokalen JSON-Datei,
    falls der Versand an AWTRIX fehlgeschlagen ist.
    """
    try:
        if os.path.exists(PENDING_DATA_FILE):
            with open(PENDING_DATA_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        else:
            existing_data = []
        # Neue Daten hinten anhängen
        existing_data.extend(payload)

        with open(PENDING_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        logging.info(f"Payload lokal in {PENDING_DATA_FILE} zwischengespeichert.")
    except Exception as e:
        logging.error(f"Fehler beim Speichern der Pending-Daten: {e}")

def send_pending_data_if_any() -> None:
    """
    Schickt ggf. zwischengespeicherte Daten an AWTRIX,
    falls welche vorhanden sind.
    """
    if not os.path.exists(PENDING_DATA_FILE):
        return  # Keine Pending-Daten

    try:
        with open(PENDING_DATA_FILE, "r", encoding="utf-8") as f:
            pending_data = json.load(f)
        if not pending_data:
            return

        logging.info("Sende zwischengespeicherte Daten an AWTRIX...")
        response = requests.post(AWTRIX_URL, json=pending_data, timeout=5)
        response.raise_for_status()

        logging.info("Zwischengespeicherte Daten erfolgreich gesendet. Datei wird geleert.")
        # Datei leeren oder löschen
        open(PENDING_DATA_FILE, "w").close()

    except requests.exceptions.RequestException as e:
        logging.error(f"Erneuter Fehler beim Senden der Pending-Daten: {e}")
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Fehler beim Lesen der Pending-Daten: {e}")

# -------------------------------------------------------------------
# Hauptjob für den Scheduler
# -------------------------------------------------------------------
def job_fetch_and_send():
    """
    Job, der alle 10 Minuten ausgeführt wird:
    1. Altdaten aus Pending-File senden (falls vorhanden)
    2. Neue Daten von Productive abrufen und an AWTRIX senden
    """
    logging.info("Starte Job: Fetch Productive-Daten und sende an AWTRIX.")
    # 1) Versuche, alte Pending-Daten zu senden
    send_pending_data_if_any()

    # 2) Neue Daten holen
    raw_data = fetch_all_data(CONFIG)
    if not raw_data:
        logging.warning("Keine oder fehlerhafte Daten aus Productive erhalten.")
        return

    # 3) Formatieren
    cleaned_data = format_data(raw_data, CONFIG["fields"])

    # 4) AWTRIX-Payload bauen
    payload = create_awtrix_payload(cleaned_data)

    # 5) An AWTRIX senden
    send_to_awtrix(payload)

# -------------------------------------------------------------------
# Scheduler einrichten und Skript ausführen
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Sofort einmalig ausführen
    job_fetch_and_send()

    # Scheduler starten, alle 10 Minuten das Ganze
    scheduler = BlockingScheduler()
    scheduler.add_job(job_fetch_and_send, 'interval', minutes=10)
    logging.info("Scheduler gestartet, führt alle 10 Minuten den Job aus.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Beende Scheduler...")

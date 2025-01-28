# apps/productive_report.py
"""
App, die Daten aus der Productive-API abholt und für AWTRIX aufbereitet.
Nutzt ein Dictionary für die Felder, damit wir pro Feld Label/Type haben.
"""

import os
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # falls noch nicht von main_awtrix.py gemacht

PRODUCTIVE_API_KEY = os.getenv("PRODUCTIVE_API_KEY")
PRODUCTIVE_ORG_ID = os.getenv("PRODUCTIVE_ORG_ID")
APP_NAME = "Productive_Report"

BASE_URL = "https://api.productive.io/api/v2/reports/"

HEADERS = {
    "X-Auth-Token": PRODUCTIVE_API_KEY,
    "X-Organization-Id": PRODUCTIVE_ORG_ID,
    "Content-Type": "application/vnd.api+json"
}

def get_config():
    """
    Beispiel-Config: 
    Statt einer Liste 'fields' -> Dictionary mit:
      {
        "<feldname_in_der_API>": {
          "label": "Anzeigename",
          "type": "currency" | "hours" | ...
        },
        ...
      }
    """
    current_year = datetime.now().year
    config = {
        "report_endpoint": "financial_item_reports",
        "filters": {
            "date": {
                "gt_eq": f"{current_year}-01-01",
                "lt_eq": f"{current_year}-12-31"
            }
        },
        "groups": ["organization", "date:year"],
        "pagination": {"page_size": 100},

        "fields": {
            "total_recognized_revenue": {
                "label": "Umsatz",
                "type": "currency"
            },
            "total_recognized_profit": {
                "label": "Gewinn",
                "type": "currency"
            },
            "total_recognized_time": {
                "label": "Arbeitsstunden",
                "type": "hours"
            }
            # Füge beliebig weitere Felder mit passendem 'type' hinzu
        }
    }
    return config


# -- Hilfsfunktionen --

def build_url(endpoint, filters, groups, pagination):
    filter_parts = []
    idx = 0
    for field, ops in filters.items():
        for op, val in ops.items():
            filter_parts.append(f"filter[{idx}][{field}][{op}]={val}")
        idx += 1
    filter_parts.append("filter[$op]=and")
    filter_string = "&".join(filter_parts)
    group_string = ",".join(groups)
    page_string = f"page[number]={pagination.get('page_number', 1)}&per_page={pagination['page_size']}"

    url = (
        f"{BASE_URL}{endpoint}"
        f"?{filter_string}&{page_string}&group={group_string}&report_currency=1&sort=date:year"
    )
    return url

def fetch_all_data(cfg):
    endpoint = cfg["report_endpoint"]
    filters = cfg["filters"]
    groups = cfg["groups"]
    pagination = cfg["pagination"]

    all_data = []
    page = 1
    while True:
        custom_pag = {
            "page_size": pagination["page_size"],
            "page_number": page
        }
        url = build_url(endpoint, filters, groups, custom_pag)
        logging.info(f"Rufe URL auf: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("data"):
                break

            all_data.extend(data["data"])

            meta = data.get("meta", {}).get("pagination", {})
            total_pages = meta.get("total_pages", 1)
            if page >= total_pages:
                break
            page += 1
        except requests.exceptions.RequestException as e:
            logging.error(f"Fehler beim Abrufen von Productive: {e}")
            break
    return all_data

def parse_value(raw_val, field_def):
    """
    Hier entscheidest du je nach 'type', wie du den Wert formatierst.
    Z.B. 'currency' => Cent -> Euro,
         'hours' => vielleicht 'value / 60' oder so,
         etc.
    """
    field_type = field_def.get("type", "currency")  # default: currency

    if field_type == "currency":
        # Angenommen raw_val kommt in Cent
        try:
            eur = raw_val / 100
        except (TypeError, ZeroDivisionError):
            eur = 0
        return f"{eur:,.2f} EUR"

    elif field_type == "hours":
        # Vielleicht sind das 'Minuten' oder 'Sekunden'? 
        # Das musst du wissen. 
        # Beispiel: raw_val = 60 -> 1,00 h
        try:
            hours = raw_val / 60.0
        except (TypeError, ZeroDivisionError):
            hours = 0
        return f"{hours:,.2f} h"

    else:
        # Fallback (einfach so anzeigen)
        return str(raw_val)


def format_data(raw, fields_cfg):
    """
    'fields_cfg' ist ein Dictionary:
      {
        "<field_name>": {
          "label": "...",
          "type": "currency"|"hours"|...
        },
        ...
      }

    Wir holen aus item[\"attributes\"] den Rohwert, 
    rufen parse_value() auf und speichern das in 'single[field_name]'.
    """
    results = []
    for item in raw:
        attrs = item.get("attributes", {})
        single = {}

        for field_name, field_def in fields_cfg.items():
            raw_val = attrs.get(field_name, 0)
            formatted_val = parse_value(raw_val, field_def)
            single[field_name] = formatted_val

        results.append(single)
    return results

def build_awtrix_payload(data, fields_cfg):
    """
    Baut das JSON-Array für AWTRIX, 
    in dem Field-Name (label) + Field-Value nacheinander kommen.
    """
    payload = []
    for entry in data:
        for field_name, field_val in entry.items():
            # Hol dir das Label aus fields_cfg
            field_def = fields_cfg[field_name]
            label = field_def.get("label", field_name)

            # Feldname in Weiß
            payload.append({
                "text": label,
                "duration": 4,
                "color": "#FFFFFF",
                "noScroll": False
            })
            # Feldwert in Gelb
            payload.append({
                "text": field_val,
                "duration": 6,
                "color": "#FFFF00",
                "noScroll": False
            })
    return payload

def get_payload():
    """
    Hauptfunktion, die von main_awtrix.py aufgerufen wird.
    Gibt (app_name, payload) zurück.
    """
    cfg = get_config()
    raw = fetch_all_data(cfg)
    if not raw:
        logging.warning("Keine Daten aus Productive erhalten - leeres Payload.")
        return APP_NAME, []

    # fields_cfg ist unser Dictionary mit 'label' und 'type'
    fields_cfg = cfg["fields"]
    cleaned_data = format_data(raw, fields_cfg)
    payload = build_awtrix_payload(cleaned_data, fields_cfg)

    return APP_NAME, payload

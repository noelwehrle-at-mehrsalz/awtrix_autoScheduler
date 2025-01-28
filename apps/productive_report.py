# apps/productive_report.py
"""
Diese App holt Daten aus der Productive-API und bereitet
einen AWTRIX-Payload auf. 
"""

import os
import logging
import requests
from datetime import datetime

# Du kannst .env-Geschichten auch hier machen,
# oder in main_awtrix.py. 
# Falls main_awtrix.py schon load_dotenv() aufgerufen hat,
# kannst du einfach getenv() nutzen.
from dotenv import load_dotenv
load_dotenv()  # optional, falls nicht schon vorher passiert

# --- Globale Variablen / ENV ---
PRODUCTIVE_API_KEY = os.getenv("PRODUCTIVE_API_KEY")
PRODUCTIVE_ORG_ID = os.getenv("PRODUCTIVE_ORG_ID")

# AWTRIX-APP-NAME
APP_NAME = "Productive_Report"

# BASE URL für Productive
BASE_URL = "https://api.productive.io/api/v2/reports/"

# Standard-Header für die Productive-API
HEADERS = {
    "X-Auth-Token": PRODUCTIVE_API_KEY,
    "X-Organization-Id": PRODUCTIVE_ORG_ID,
    "Content-Type": "application/vnd.api+json"
}

# Beispiel-Config für das Reporting
def get_config():
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
        "fields": ["total_recognized_revenue", "total_cost", "total_recognized_profit"]
    }
    return config

# Optional: Label-Mapping
FIELD_LABELS = {
    "total_recognized_revenue": "Umsatz",
    "total_cost": "Kosten",
    "total_recognized_profit": "Profit"
}

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

    url = f"{BASE_URL}{endpoint}?{filter_string}&{page_string}&group={group_string}&report_currency=1&sort=date:year"
    return url

def fetch_all_data(cfg):
    endpoint = cfg["report_endpoint"]
    filters = cfg["filters"]
    groups = cfg["groups"]
    pagination = cfg["pagination"]

    all_data = []
    page = 1
    while True:
        custom_pag = {"page_size": pagination["page_size"], "page_number": page}
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

def format_data(raw, fields):
    """
    Filtert pro Eintrag nur bestimmte Felder, rechnet Cent in Euro, formatiert sie.
    """
    results = []
    for item in raw:
        attrs = item.get("attributes", {})
        single = {}
        for f in fields:
            val = attrs.get(f, 0)
            try:
                val_eur = val / 100
            except:
                val_eur = 0
            val_str = f"{val_eur:,.2f} EUR"
            single[f] = val_str
        results.append(single)
    return results

def build_awtrix_payload(data):
    """
    Baut ein JSON-Array für AWTRIX, 
    in dem Field-Name + Field-Value nacheinander kommen.
    """
    payload = []
    for entry in data:
        for field_name, field_value in entry.items():
            label = FIELD_LABELS.get(field_name, field_name)
            # Feldname in Weiß
            payload.append({
                "text": label,
                "duration": 5,
                "color": "#FFFFFF",
                "noScroll": False
            })
            # Feldwert in Gelb
            payload.append({
                "text": field_value,
                "duration": 5,
                "color": "#FFFF00",
                "noScroll": False
            })
    return payload

# -- Hauptfunktion: get_payload() --
def get_payload():
    """
    Muss von main_awtrix.py aufgerufen werden.
    Liefert (app_name, payload).
    """
    cfg = get_config()
    raw = fetch_all_data(cfg)
    if not raw:
        logging.warning("Keine Daten aus Productive erhalten - leeres Payload.")
        return APP_NAME, []

    cleaned_data = format_data(raw, cfg["fields"])
    payload = build_awtrix_payload(cleaned_data)

    # App-Name: Der Name, unter dem AWTRIX unsere Daten anzeigt
    return APP_NAME, payload

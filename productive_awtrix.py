#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main_awtrix.py
==============
Zentrales Skript, das:
- Alle App-Skripte im Ordner ./apps lädt
- (App-Entfernung erkannt und an AWTRIX gemeldet)
- Läuft alle 10 Minuten mit APScheduler
"""

import os
import json
import logging
import requests
import importlib.util
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

load_dotenv()

PRODUCTIVE_API_KEY = os.getenv("PRODUCTIVE_API_KEY")
PRODUCTIVE_ORG_ID = os.getenv("PRODUCTIVE_ORG_ID")
AWTRIX_IP = os.getenv("AWTRIX_IP")

if not (PRODUCTIVE_API_KEY and PRODUCTIVE_ORG_ID and AWTRIX_IP):
    logging.error("Fehlende .env-Einträge! Bitte PRODUCTIVE_API_KEY, PRODUCTIVE_ORG_ID und AWTRIX_IP definieren.")
    exit(1)

APPS_DIR = "./apps"

KNOWN_APPS_FILE = "known_apps.json"  # speichert die App-Namen

def load_known_apps():
    """Lädt die Liste bekannter App-Namen aus known_apps.json (falls vorhanden)."""
    if not os.path.exists(KNOWN_APPS_FILE):
        return []
    try:
        with open(KNOWN_APPS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.warning(f"Fehler beim Laden von {KNOWN_APPS_FILE}: {e}")
        return []

def save_known_apps(apps_list):
    """Speichert die Liste bekannter App-Namen in known_apps.json."""
    try:
        with open(KNOWN_APPS_FILE, "w", encoding="utf-8") as f:
            json.dump(apps_list, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logging.warning(f"Fehler beim Speichern von {KNOWN_APPS_FILE}: {e}")

def load_apps_from_folder(folder_path=APPS_DIR):
    """
    Durchläuft den Ordner, sucht nach .py-Dateien,
    lädt diese dynamisch via importlib.
    Erwartet in jeder Datei eine Funktion get_payload() -> (app_name, payload).
    """
    if not os.path.isdir(folder_path):
        logging.warning(f"Ordner '{folder_path}' existiert nicht.")
        return

    for filename in os.listdir(folder_path):
        if filename.endswith(".py"):
            module_name = filename[:-3]  # Dateiname ohne .py
            file_path = os.path.join(folder_path, filename)
            try:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    yield module
            except Exception as e:
                logging.error(f"Fehler beim Laden von {filename}: {e}")

def send_to_awtrix(payload, app_name):
    """
    Sendet das Payload an AWTRIX:
    http://[AWTRIX_IP]/api/custom?name=[app_name]
    """
    url = f"http://{AWTRIX_IP}/api/custom?name={app_name}"
    try:
        logging.info(f"Sende Daten an AWTRIX-App '{app_name}'...")
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        logging.info(f"App '{app_name}' erfolgreich aktualisiert.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Fehler beim Senden an AWTRIX '{app_name}': {e}")

def remove_awtrix_app(app_name):
    """
    Schickt eine leere Payload an AWTRIX, um eine App zu löschen.
    """
    url = f"http://{AWTRIX_IP}/api/custom?name={app_name}"
    try:
        logging.info(f"Entferne App '{app_name}' von der AWTRIX...")
        # Leeres Array oder leeres Object => App löschen
        response = requests.post(url, json=[], timeout=5)
        response.raise_for_status()
        logging.info(f"App '{app_name}' erfolgreich entfernt.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Fehler beim Entfernen von App '{app_name}': {e}")

def update_awtrix_apps():
    """
    1) Alte Liste bekannter Apps laden
    2) Alle App-Module laden -> get_payload()
    3) Erkannten Apps Payload schicken
    4) Prüfen, ob es Apps gibt, die nicht mehr existieren => leeres Payload schicken
    5) Neue Liste bekannter Apps speichern
    """
    logging.info("Starte Aktualisierung aller Apps...")

    # 1) Bekannte Apps laden
    known_apps = set(load_known_apps())

    current_apps = set()  # Hier sammeln wir die Namen aller vorhandenen Apps

    # 2) Alle Module durchgehen
    for module in load_apps_from_folder(APPS_DIR):
        if hasattr(module, "get_payload") and callable(module.get_payload):
            try:
                app_name, payload = module.get_payload()
                current_apps.add(app_name)
                # 3) Payload an AWTRIX senden
                send_to_awtrix(payload, app_name)
            except Exception as e:
                logging.error(f"Fehler beim Abruf der Payload in Modul {module}: {e}")
        else:
            logging.warning(f"Modul {module} hat keine Funktion get_payload(). Wird übersprungen.")

    # 4) Prüfen, welche Apps in known_apps, aber nicht in current_apps sind
    removed_apps = known_apps - current_apps
    for old_app in removed_apps:
        remove_awtrix_app(old_app)

    # 5) Neue Liste bekannter Apps speichern
    save_known_apps(list(current_apps))

if __name__ == "__main__":
    # Einmalig ausführen
    update_awtrix_apps()

    # Alle 10 Minuten
    scheduler = BlockingScheduler()
    scheduler.add_job(update_awtrix_apps, 'interval', minutes=10)
    logging.info("Scheduler gestartet (alle 10 Minuten).")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Beende Scheduler...")

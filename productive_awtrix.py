#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main_awtrix.py
==============
Zentrales Skript, das:
- Die AWTRIX-API anspricht
- Alle App-Skripte im Ordner ./apps lädt
- Den Payload jeder App abruft und an AWTRIX sendet
- Läuft alle 10 Minuten mit APScheduler
"""

import os
import json
import logging
import requests
import importlib.util
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

# ----------------------------------------
# Logger/Umgebung konfigurieren
# ----------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

load_dotenv()

AWTRIX_IP = os.getenv("AWTRIX_IP")

if not (AWTRIX_IP):
    logging.error("Fehlende .env-Einträge! Bitte AWTRIX_IP definieren.")
    exit(1)

# ----------------------------------------
# Einstellungen
# ----------------------------------------
APPS_DIR = "./apps"  # Ordner, der die App-Files enthält

# ----------------------------------------
# Funktion: Alle Python-Dateien im ./apps-Ordner laden und yielden
# ----------------------------------------
def load_apps_from_folder(folder_path=APPS_DIR):
    """
    Durchläuft den Ordner, sucht nach .py-Dateien,
    lädt diese dynamisch via importlib.
    Erwartet in jeder Datei eine Funktion get_payload().
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

# ----------------------------------------
# AWTRIX-Sendefunktion
# ----------------------------------------
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

# ----------------------------------------
# Haupt-Job
# ----------------------------------------
def update_awtrix_apps():
    """
    1) Alle App-Module laden,
    2) get_payload() aufrufen,
    3) An AWTRIX senden.
    """
    logging.info("Starte Aktualisierung aller Apps...")

    found_any_app = False
    for module in load_apps_from_folder(APPS_DIR):
        # Prüfen, ob 'get_payload' existiert
        if hasattr(module, "get_payload") and callable(module.get_payload):
            try:
                app_name, payload = module.get_payload()
                # Payload an AWTRIX senden
                send_to_awtrix(payload, app_name)
                found_any_app = True
            except Exception as e:
                logging.error(f"Fehler beim Abruf der Payload in {module}: {e}")
        else:
            logging.warning(f"Modul {module} hat keine Funktion get_payload(). Wird übersprungen.")

    if not found_any_app:
        logging.warning("Keine App-Module gefunden oder keines hatte get_payload().")

# ----------------------------------------
# Scheduler / main
# ----------------------------------------
if __name__ == "__main__":
    # 1) Einmal sofort
    update_awtrix_apps()

    # 2) Alle 10 Minuten
    scheduler = BlockingScheduler()
    scheduler.add_job(update_awtrix_apps, 'interval', minutes=10)
    logging.info("Scheduler gestartet (alle 10 Minuten).")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Beende Scheduler...")

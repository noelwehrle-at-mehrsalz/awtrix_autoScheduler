#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
import requests
import importlib.util
import threading
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

# Unser Scheduler-Objekt global definieren
scheduler = BlockingScheduler()

def load_apps_from_folder(folder_path=APPS_DIR):
    import os

    if not os.path.isdir(folder_path):
        logging.warning(f"Ordner '{folder_path}' existiert nicht.")
        return

    for filename in os.listdir(folder_path):
        if filename.endswith(".py"):
            module_name = filename[:-3]
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
    url = f"http://{AWTRIX_IP}/api/custom?name={app_name}"
    try:
        logging.info(f"Sende Daten an AWTRIX-App '{app_name}'...")
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        logging.info(f"App '{app_name}' erfolgreich aktualisiert.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Fehler beim Senden an AWTRIX '{app_name}': {e}")

def update_awtrix_apps():
    logging.info("Starte Aktualisierung aller Apps...")

    any_app_found = False
    for module in load_apps_from_folder(APPS_DIR):
        if hasattr(module, "get_payload") and callable(module.get_payload):
            try:
                app_name, payload = module.get_payload()
                send_to_awtrix(payload, app_name)
                any_app_found = True
            except Exception as e:
                logging.error(f"Fehler in Modul {module}: {e}")
        else:
            logging.warning(f"Modul {module} hat keine Funktion get_payload(). Wird übersprungen.")

    if not any_app_found:
        logging.warning("Keine Apps gefunden oder keine gültige get_payload-Funktion.")

def scheduler_thread():
    """
    Läuft im eigenen Thread.
    Startet den BlockingScheduler (der blockiert dann diesen Thread),
    bis wir scheduler.shutdown() aufrufen.
    """
    logging.info("Scheduler-Thread gestartet.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    logging.info("Scheduler-Thread beendet.")

def main():
    """
    Main-Funktion:
    1. Einmal sofort update
    2. Scheduler-Thread starten
    3. Eingabeschleife im Hauptthread => 'u' Update, 'q' Quit
    """
    # 1) Einmaliges Update direkt
    update_awtrix_apps()

    # 2) Scheduler-Thread starten
    scheduler.add_job(update_awtrix_apps, 'interval', minutes=10)
    sched_thread = threading.Thread(target=scheduler_thread, daemon=True)
    sched_thread.start()

    # 3) Eingabeschleife
    logging.info("Eingabemodus: (u=Update, q=Quit)")
    while True:
        cmd = input().strip().lower()
        if cmd == "u":
            logging.info("Manuelles Update ausgelöst...")
            update_awtrix_apps()
        elif cmd == "q":
            logging.info("Beende Script aufgrund Nutzer-Eingabe...")
            # Scheduler ordentlich beenden
            scheduler.shutdown(wait=False)
            # Thread beenden:
            break
        else:
            logging.info("Unbekannter Befehl. (u=Update, q=Quit)")

    # Warten, bis der Scheduler-Thread wirklich durch ist:
    sched_thread.join()
    logging.info("Script sauber beendet.")

if __name__ == "__main__":
    main()

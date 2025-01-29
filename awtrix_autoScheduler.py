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

AWTRIX_IP = os.getenv("AWTRIX_IP")

if not (AWTRIX_IP):
    logging.error("Fehlende .env-Einträge! Bitte AWTRIX_IP definieren.")
    exit(1) 

APPS_DIR = "./apps"

# Datei, in der wir den letzten Stand bekannter Apps speichern.
KNOWN_APPS_FILE = "known_apps.json"

# Unser Scheduler-Objekt global definieren
scheduler = BlockingScheduler()

#####################
# Hilfsfunktionen
#####################

def load_known_apps():
    """Lädt eine Liste bekannter App-Namen aus known_apps.json."""
    if not os.path.exists(KNOWN_APPS_FILE):
        return set()
    try:
        with open(KNOWN_APPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data)
    except (json.JSONDecodeError, IOError) as e:
        logging.warning(f"Fehler beim Laden von {KNOWN_APPS_FILE}: {e}")
        return set()


def save_known_apps(apps_list):
    """Speichert die Liste bekannter App-Namen in known_apps.json."""
    try:
        with open(KNOWN_APPS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(apps_list), f, ensure_ascii=False, indent=2)
    except IOError as e:
        logging.warning(f"Fehler beim Speichern von {KNOWN_APPS_FILE}: {e}")


def remove_awtrix_app(app_name: str):
    """
    Schickt eine komplett leere Payload an AWTRIX, um die App zu löschen.
    Siehe Doku: http://[IP]/api/custom?name=[appname] (Empty Body => Remove)
    """
    url = f"http://{AWTRIX_IP}/api/custom?name={app_name}"
    try:
        logging.info(f"Entferne App '{app_name}' von der AWTRIX...")
        response = requests.post(url, data="", headers={"Content-Type": "application/json"}, timeout=5)
        response.raise_for_status()
        logging.info(f"App '{app_name}' erfolgreich entfernt.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Fehler beim Entfernen von App '{app_name}': {e}")


def load_apps_from_folder(folder_path=APPS_DIR):
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

#####################
# Haupt-Update-Funktion
#####################

def update_awtrix_apps():
    """
    Lädt alle Apps (Module) und ruft get_payload() auf.
    - Speichert aktuelle Apps in current_apps.
    - Prüft, ob aus known_apps welche entfernt wurden => schickt Leer-Payload
    - Speichert neue known_apps.
    """
    logging.info("Starte Aktualisierung aller Apps...")

    known_apps = load_known_apps()
    current_apps = set()

    any_app_found = False

    for module in load_apps_from_folder(APPS_DIR):
        if hasattr(module, "get_payload") and callable(module.get_payload):
            try:
                app_name, payload = module.get_payload()
                # Payload senden
                send_to_awtrix(payload, app_name)
                current_apps.add(app_name)
                any_app_found = True
            except Exception as e:
                logging.error(f"Fehler in Modul {module}: {e}")
        else:
            logging.warning(f"Modul {module} hat keine Funktion get_payload(). Wird übersprungen.")

    if not any_app_found:
        logging.warning("Keine Apps gefunden oder keine gültige get_payload-Funktion.")

    # Herausfinden, welche Apps nicht mehr existieren
    removed_apps = known_apps - current_apps
    for old_app in removed_apps:
        remove_awtrix_app(old_app)

    # Speichern
    save_known_apps(current_apps)

#####################
# Scheduler-Thread
#####################

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

#####################
# main
#####################

def main():
    """
    Main-Funktion:
    1. Einmal sofort update
    2. Scheduler-Thread starten
    3. Eingabeschleife im Hauptthread => 'u' Update, 'q' Quit
    """
    # 1) Einmaliges Update direkt
    update_awtrix_apps()

    # 2) Scheduler-Thread starten (alle 10 Min)
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

# AWTRIX Productive Report Script

Dieses Skript sammelt Daten aus der Productive-API und sendet sie an eine AWTRIX-App. Es verwendet einen Scheduler, um die Daten regelmäßig zu aktualisieren.

## Voraussetzungen

- Python 3.x
- Virtuelle Umgebung (empfohlen)
- Abhängigkeiten aus `requirements.txt`
- `.env` Datei mit den notwendigen Umgebungsvariablen

## Installation

1. Klone das Repository:

    ```sh
    git clone <repository-url>
    cd <repository-name>
    ```

2. Erstelle eine virtuelle Umgebung und aktiviere sie:

    ```sh
    python -m venv venv
    source venv/bin/activate  # Auf Windows: venv\Scripts\activate
    ```

3. Installiere die Abhängigkeiten:

    ```sh
    pip install -r requirements.txt
    ```

4. Erstelle eine [.env](http://_vscodecontentref_/0) Datei im Hauptverzeichnis und füge die folgenden Einträge hinzu:

    ```env
    PRODUCTIVE_API_KEY=<Dein Productive API Key>
    PRODUCTIVE_ORG_ID=<Deine Productive Organisations-ID>
    AWTRIX_IP=<IP-Adresse deiner AWTRIX>
    ```

## Verwendung

1. Starte das Skript:

    ```sh
    python main_awtrix.py
    ```

2. Das Skript führt sofort ein Update durch und startet dann einen Scheduler, der alle 10 Minuten ein Update durchführt.

3. Du kannst manuell ein Update auslösen oder das Skript beenden, indem du die folgenden Befehle in die Konsole eingibst:
    - `u`: Manuelles Update
    - `q`: Beenden des Skripts

## Struktur

- [main_awtrix.py](http://_vscodecontentref_/1): Hauptskript, das den Scheduler startet und die Updates verwaltet.
- [productive_report.py](http://_vscodecontentref_/2): Modul, das die Daten aus der Productive-API abholt und das Payload für AWTRIX erstellt.
- [.env](http://_vscodecontentref_/3): Datei mit den notwendigen Umgebungsvariablen.
- [requirements.txt](http://_vscodecontentref_/4): Liste der Python-Abhängigkeiten.

## Funktionen

### [main_awtrix.py](http://_vscodecontentref_/5)

- [send_to_awtrix(payload, app_name)](http://_vscodecontentref_/6): Sendet das Payload an die AWTRIX-App.
- [update_awtrix_apps()](http://_vscodecontentref_/7): Aktualisiert alle Apps, indem es die Payloads von den Modulen abruft und an AWTRIX sendet.
- [scheduler_thread()](http://_vscodecontentref_/8): Startet den Scheduler in einem eigenen Thread.
- [main()](http://_vscodecontentref_/9): Hauptfunktion, die das Skript steuert.

### [productive_report.py](http://_vscodecontentref_/10)

- [get_payload()](http://_vscodecontentref_/11): Hauptfunktion, die von [main_awtrix.py](http://_vscodecontentref_/12) aufgerufen wird und das Payload für AWTRIX erstellt.

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert. Siehe die LICENSE Datei für Details.

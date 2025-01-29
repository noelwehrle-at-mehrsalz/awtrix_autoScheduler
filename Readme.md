# AWTRIX AutoScheduler

Dieses Skript lädt automatisch Apps aus dem `apps`-Ordner und sendet die dort definierte Payload an AWTRIX.

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

4. Erstelle eine `.env` Datei im Hauptverzeichnis und füge die folgenden Einträge hinzu:

    ```env
    AWTRIX_IP=<IP-Adresse deiner AWTRIX>
    ```

## Verwendung

1. Starte das Skript:

    ```sh
    python awtrix_autoScheduler.py
    ```

2. Das Skript führt sofort ein Update durch und startet dann einen Scheduler, der alle 10 Minuten ein Update durchführt.

3. Du kannst manuell ein Update auslösen oder das Skript beenden, indem du die folgenden Befehle in die Konsole eingibst:
    - `u`: Manuelles Update
    - `q`: Beenden des Skripts

## Struktur

- [`awtrix_autoScheduler.py`](./awtrix_autoScheduler.py): Hauptskript, das den Scheduler startet und die Updates verwaltet.
- [`apps`](./apps): Verzeichnis, das die einzelnen App-Module enthält.
- [`.env`](./.env): Datei mit den notwendigen Umgebungsvariablen.
- [`requirements.txt`](./requirements.txt): Liste der Python-Abhängigkeiten.

## Funktionen

### [`awtrix_autoScheduler.py`](awtrix_autoScheduler.py )

- `send_to_awtrix(payload, app_name)`: Sendet das Payload an die AWTRIX-App.
- `update_awtrix_apps()`: Aktualisiert alle Apps, indem es die Payloads von den Modulen abruft und an AWTRIX sendet.
- `scheduler_thread()`: Startet den Scheduler in einem eigenen Thread.
- `main()`: Hauptfunktion, die das Skript steuert.

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert. Siehe die LICENSE Datei für Details.

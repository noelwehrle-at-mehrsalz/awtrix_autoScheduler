# apps/example_app.py

"""
Beispiel-App-Skript für AWTRIX.
Erwartet vom Hauptskript, dass es hier eine Funktion get_payload() gibt,
die (app_name, payload) zurückgibt.
"""

def get_payload():
    app_name = "ExampleApp"  # das ist der Custom-App-Name in AWTRIX
    payload = [
        {
            "text": "Hello from Example App!",
            "duration": 5,
            "color": "#FFFFFF",
            "noScroll": False
        },
        {
            "text": "Noch eine Zeile",
            "duration": 5,
            "color": "#FFFF00",
            "noScroll": False
        }
    ]
    return app_name, payload

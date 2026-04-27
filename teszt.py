import requests

API_KEY = "AIzaSyDpKsXMK2DqcA0awy2rnKd8qmPIk4veK90"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

try:
    response = requests.get(url)
    models = response.json().get('models', [])
    print("✅ A te kulcsoddal elérhető modellek:")
    for m in models:
        # Csak a szövegalkotó modelleket írjuk ki
        if 'generateContent' in m.get('supportedGenerationMethods', []):
            print(f" - {m['name']}")
except Exception as e:
    print("Hiba a lekérdezésnél:", e)
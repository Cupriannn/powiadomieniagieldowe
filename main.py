import os
import requests
import csv
import xml.etree.ElementTree as ET
from io import StringIO
from datetime import datetime, timedelta

# --- KONFIGURACJA BEZPIECZEŃSTWA (Zmienne środowiskowe) ---
GOOGLE_SHEETS_CSV_URL = os.environ.get("GOOGLE_SHEETS_CSV_URL")
FINNHUB_TOKEN = os.environ.get("FINNHUB_TOKEN")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Nagłówki HTTP, aby Yahoo Finance nie blokowało naszego skryptu
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def pobierz_i_skonfiguruj_uzytkownikow():
    if not GOOGLE_SHEETS_CSV_URL:
        print("BŁĄD: Brak zmiennej GOOGLE_SHEETS_CSV_URL!")
        return {}
        
    try:
        response = requests.get(GOOGLE_SHEETS_CSV_URL)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            return {}

        f = StringIO(response.text)
        reader = csv.reader(f)
        next(reader)
        
        uzytkownicy_i_spolki = {}
        for wiersz in reader:
            if len(wiersz) < 3:
                continue
            discord_id = wiersz[1].strip()
            surowe_spolki = wiersz[2]
            lista_spolek = [spolka.strip().upper() for spolka in surowe_spolki.split(",") if spolka.strip()]
            uzytkownicy_i_spolki[discord_id] = lista_spolek
            
        return uzytkownicy_i_spolki
    except Exception as e:
        print(f"Błąd bazy danych: {e}")
        return {}


def pobierz_newsy_usa(ticker):
    """Silnik podstawowy (Finnhub API) dla rynku amerykańskiego."""
    if not FINNHUB_TOKEN:
        return []
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={yesterday}&to={today}&token={FINNHUB_TOKEN}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Błąd Finnhub dla {ticker}: {e}")
        return []


def pobierz_newsy_gpw(ticker):
    """Silnik awaryjny (Yahoo RSS Fallback) dla Giełdy w Warszawie."""
    print(f"-> Finnhub brak danych dla {ticker}. Odpalanie silnika GPW (Yahoo RSS)...")
    # Yahoo Finance oznacza GPW przy pomocy końcówki .WA (np. CDR.WA, KGH.WA)
    url = f"https://finance.yahoo.com/rss/headline?s={ticker}.WA"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            return None
            
        # Parsujemy surowy plik XML ze struktury RSS kanału Yahoo
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        
        if items:
            pierwszy = items[0]
            return {
                'headline': pierwszy.find('title').text,
                'url': pierwszy.find('link').text,
                'source': 'Yahoo Finance (GPW)'
            }
        return None
    except Exception as e:
        print(f"Błąd silnika GPW dla {ticker}: {e}")
        return None


def wyslij_na_discorda(discord_id, ticker, tytul, link, zrodlo):
    if not DISCORD_WEBHOOK_URL:
        return
        
    payload = {
        "username": "Asystent Giełdowy IAM",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2704/2704332.png",
        "content": f"🚨 **Nowy raport dla Twojej spółki!** <@{discord_id}>",
        "embeds": [{
            "title": f"Wiadomość z rynku dla: {ticker}",
            "description": tytul,
            "url": link,
            "color": 15158332 if "GPW" in zrodlo else 3066993,  # Czerwony pasek dla Polski, zielony dla USA!
            "footer": {
                "text": f"System Monitoringu | Źródło: {zrodlo}"
            }
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Błąd Discorda: {e}")


def monitoruj_gielde():
    baza_iam = pobierz_i_skonfiguruj_uzytkownikow()
    if not baza_iam:
        print("Baza danych jest pusta lub brak konfiguracji.")
        return

    wszystkie_spolki = set()
    for lista_spolek in baza_iam.values():
        wszystkie_spolki.update(lista_spolek)
        
    print(f"Rozpoczynam skanowanie globalne dla: {list(wszystkie_spolki)}\n")

    for ticker in wszystkie_spolki:
        # Krok 1: Próbujemy pobrać dane z USA (Finnhub)
        newsy = pobierz_newsy_usa(ticker)
        
        tytul, link, zrodlo = None, None, None
        
        if newsy:
            # Sukces - to spółka z USA
            najnowszy = newsy[0]
            tytul = najnowszy.get('headline')
            link = najnowszy.get('url')
            zrodlo = f"Finnhub API ({najnowszy.get('source', 'Wiadomości')})"
        else:
            # Krok 2: Fallback do silnika GPW
            news_gpw = pobierz_newsy_gpw(ticker)
            if news_gpw:
                tytul = news_gpw['headline']
                link = news_gpw['url']
                zrodlo = news_gpw['source']
        
        # Jeśli którykolwiek silnik zwrócił wiadomość, mapujemy uprawnienia i wysyłamy
        if tytul and link:
            for discord_id, subskrybowane_spolki in baza_iam.items():
                if ticker in subskrybowane_spolki:
                    wyslij_na_discorda(discord_id, ticker, tytul, link, zrodlo)
        else:
            print(f"Brak nowych wieści globalnych dla {ticker}.")


if __name__ == "__main__":
    monitoruj_gielde()

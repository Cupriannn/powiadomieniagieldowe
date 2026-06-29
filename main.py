import os
import requests
import csv
import xml.etree.ElementTree as ET
from io import StringIO
from datetime import datetime, timedelta

# --- KONFIGURACJA BEZPIECZEŃSTWA ---
GOOGLE_SHEETS_CSV_URL = os.environ.get("GOOGLE_SHEETS_CSV_URL")
FINNHUB_TOKEN = os.environ.get("FINNHUB_TOKEN")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Nazwa pliku, w którym bot będzie przechowywał pamięć o wysłanych newsach
PLIK_STANU = "wyslane.txt"


def wczytaj_wyslane():
    """Wczytuje z pliku listę linków, które już zostały wysłane na Discorda."""
    if os.path.exists(PLIK_STANU):
        with open(PLIK_STANU, "r", encoding="utf-8") as f:
            return set(linia.strip() for linia in f if linia.strip())
    return set()


def zapisz_wyslane(wyslane_linki):
    """Zapisuje zaktualizowaną listę linków do pliku tekstowego."""
    with open(PLIK_STANU, "w", encoding="utf-8") as f:
        for link in wyslane_linki:
            f.write(f"{link}\n")


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
        return []


def pobierz_newsy_gpw(ticker):
    url = f"https://finance.yahoo.com/rss/headline?s={ticker}.WA"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            return None
            
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
            "color": 15158332 if "GPW" in zrodlo else 3066993,
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

    # Wczytujemy historię wysłanych wiadomości
    wyslane_szablony = wczytaj_wyslane()

    wszystkie_spolki = set()
    for lista_spolek in baza_iam.values():
        wszystkie_spolki.update(lista_spolek)
        
    print(f"Rozpoczynam skanowanie globalne dla: {list(wszystkie_spolki)}\n")

    nowo_wyslane = False

    for ticker in wszystkie_spolki:
        newsy = pobierz_newsy_usa(ticker)
        tytul, link, zrodlo = None, None, None
        
        if newsy:
            najnowszy = newsy[0]
            tytul = najnowszy.get('headline')
            link = najnowszy.get('url')
            zrodlo = f"Finnhub API ({najnowszy.get('source', 'Wiadomości')})"
        else:
            news_gpw = pobierz_newsy_gpw(ticker)
            if news_gpw:
                tytul = news_gpw['headline']
                link = news_gpw['url']
                zrodlo = news_gpw['source']
        
        if tytul and link:
            # --- KLUCZOWY FILTR ANTYSAMOWY ---
            if link in wyslane_szablony:
                print(f"-> Wiadomość dla {ticker} była już wysłana w przeszłości. Pomijam.")
                continue
                
            # Jeśli linku nie ma w pliku, wysyłamy i dodajemy do pamięci bota
            for discord_id, subskrybowane_spolki in baza_iam.items():
                if ticker in subskrybowane_spolki:
                    wyslij_na_discorda(discord_id, ticker, tytul, link, zrodlo)
            
            wyslane_szablony.add(link)
            nowo_wyslane = True
        else:
            print(f"Brak nowych wieści globalnych dla {ticker}.")

    # Jeśli pojawiły się nowe wiadomości, zapisujemy zaktualizowaną listę do pliku stanu
    if nowo_wyslane:
        zapisz_wyslane(wyslane_szablony)
        print("\nZaktualizowano rejestr wysłanych wiadomości.")


if __name__ == "__main__":
    monitoruj_gielde()

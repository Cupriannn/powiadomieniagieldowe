import requests
from bs4 import BeautifulSoup
import smtplib
import os
from email.mime.text import MIMEText

# --- KONFIGURACJA ---
OBSERWOWANE = ["KGHM", "CD PROJEKT", "SYNEKTIK", "ORLEN"]
URL_ZRODLO = "https://www.bankier.pl/gielda/wiadomosci/komunikaty-espi-ebi"
BASE_URL = "https://www.bankier.pl" # Potrzebne do budowy pełnego linku

EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')

def wyslij_mail(spolka, tytul, link_raportu):
    # Treść maila z linkiem
    tresc = f"Wykryto nowy raport dla spółki {spolka}:\n\n{tytul}\n\nLink bezpośredni: {link_raportu}\n\nStrona zbiorcza: {URL_ZRODLO}"
    msg = MIMEText(tresc, 'plain', 'utf-8')
    msg['Subject'] = f"ALERT GPW: {spolka}"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER

    try:
        with smtplib.SMTP_SSL('smtp.poczta.onet.pl', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f">>> Wysłano maila z linkiem dla {spolka}")
    except Exception as e:
        print(f">>> Błąd wysyłki: {e}")

def monitoruj():
    print("Sprawdzanie raportów...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(URL_ZRODLO, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Pobieramy linki, które mają w sobie tytuły (entry-title)
        wpisy = soup.find_all('a', class_='entry-title')
        
        history_file = "history.txt"
        if not os.path.exists(history_file):
            open(history_file, 'w').close()
        
        with open(history_file, 'r', encoding='utf-8') as f:
            wyslane = f.read().splitlines()

        nowe = []
        for wpis in wpisy:
            tytul = wpis.get_text().strip()
            # Pobieramy atrybut 'href', czyli link
            link_relatywny = wpis.get('href')
            pelny_link = BASE_URL + link_relatywny if link_relatywny.startswith('/') else link_relatywny
            
            tytul_up = tytul.upper()
            for spolka in OBSERWOWANE:
                if spolka in tytul_up and tytul not in wyslane:
                    wyslij_mail(spolka, tytul, pelny_link)
                    nowe.append(tytul)
        
        if nowe:
            with open(history_file, 'a', encoding='utf-8') as f:
                for n in nowe: f.write(n + "\n")
            print(f"Dodano {len(nowe)} raportów do historii.")
    except Exception as e:
        print(f"Błąd: {e}")

if __name__ == "__main__":
    monitoruj()

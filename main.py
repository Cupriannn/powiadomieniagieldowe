import requests
from bs4 import BeautifulSoup
import smtplib
import os
from email.mime.text import MIMEText

# --- KONFIGURACJA ---
# Tutaj wpisz spółki, które Cię interesują (WIELKIMI LITERAMI)
OBSERWOWANE = ["KGHM", "CD PROJEKT", "SYNEKTIK", "ORLEN","BACTEROMIC"]
URL_ZRODLO = "https://www.bankier.pl/gielda/wiadomosci/komunikaty-espi-ebi"

# Dane pobierane z "Secrets" GitHuba dla bezpieczeństwa
EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')
EMAIL_RECEIVER = os.environ.get('EMAIL_USER') # Wysyłasz do samego siebie

def wyslij_mail(spolka, tytul):
    msg = MIMEText(f"Nowy raport dla {spolka}:\n\n{tytul}\n\nLink: {URL_ZRODLO}")
    msg['Subject'] = f"ALERT: {spolka} - Nowy Raport"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_RECEIVER

    try:
        # Konfiguracja specyficzna dla Onet (Port 465 i SSL)
        with smtplib.SMTP_SSL('smtp.poczta.onet.pl', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"Wysłano powiadomienie dla {spolka}")
    except Exception as e:
        print(f"Błąd wysyłki: {e}")

def monitoruj():
    response = requests.get(URL_ZRODLO, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Pobieramy najnowsze wpisy
    wpisy = soup.find_all('span', class_='entry-title')
    
    # Wczytujemy historię z pliku, żeby nie dublować maili
    history_file = "history.txt"
    if not os.path.exists(history_file):
        open(history_file, 'w').close()
    
    with open(history_file, 'r') as f:
        wyslane = f.read().splitlines()

    nowe_wpisy = []
    for wpis in wpisy:
        tytul = wpis.get_text().strip()
        tytul_up = tytul.upper()
        
        for spolka in OBSERWOWANE:
            if spolka in tytul_up and tytul not in wyslane:
                wyslij_mail(spolka, tytul)
                nowe_wpisy.append(tytul)
    
    # Dopisz nowe do historii
    with open(history_file, 'a') as f:
        for n in nowe_wpisy:
            f.write(n + "\n")

if __name__ == "__main__":
    monitoruj()

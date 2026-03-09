import requests
from bs4 import BeautifulSoup
import smtplib
import os
from email.mime.text import MIMEText

# --- KONFIGURACJA ---
# Wpisz tu spółki, które chcesz śledzić (WIELKIMI LITERAMI)
OBSERWOWANE = ["KGHM", "CD PROJEKT", "SYNEKTIK", "ORLEN"]
URL_ZRODLO = "https://www.bankier.pl/gielda/wiadomosci/komunikaty-espi-ebi"

# Pobieranie danych z Secrets GitHuba
EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')

def wyslij_mail(spolka, tytul):
    # Tworzenie treści maila z obsługą polskich znaków
    msg = MIMEText(f"Wykryto nowy raport dla spółki {spolka}:\n\n{tytul}\n\nSzczegóły: {URL_ZRODLO}", 'plain', 'utf-8')
    msg['Subject'] = f"ALERT GPW: {spolka}"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER # Wysyłka na Twój własny adres Onet

    try:
        # SMTP dla Onet.pl (Port 465 + SSL)
        with smtplib.SMTP_SSL('smtp.poczta.onet.pl', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f">>> Sukces: Wysłano maila o raporcie {spolka}")
    except Exception as e:
        print(f">>> Błąd wysyłki maila: {e}")

def monitoruj():
    print(f"Sprawdzam stronę: {URL_ZRODLO}")
    try:
        # Nagłówki udające prawdziwą przeglądarkę
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(URL_ZRODLO, headers=headers)
        response.encoding = 'utf-8' # Poprawne kodowanie znaków ze strony
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Szukamy tytułów raportów na Bankier.pl (najczęstszy selektor to span.entry-title)
        wpisy = soup.find_all('span', class_='entry-title')
        
        # Obsługa bazy wysłanych raportów (plik history.txt)
        history_file = "history.txt"
        if not os.path.exists(history_file):
            with open(history_file, 'w', encoding='utf-8') as f:
                f.write("")
        
        with open(history_file, 'r', encoding='utf-8') as f:
            wyslane_juz = f.read().splitlines()

        znaleziono_nowe = []
        
        for wpis in wpisy:
            tytul = wpis.get_text().strip()
            tytul_up = tytul.upper()
            
            # Sprawdzanie czy nazwa spółki jest w tytule
            for spolka in OBSERWOWANE:
                if spolka in tytul_up:
                    # Sprawdzanie czy raport nie był już wysłany wcześniej
                    if tytul not in wyslane_juz:
                        print(f"!!! Trafienie: {spolka} - {tytul}")
                        wyslij_mail(spolka, tytul)
                        znaleziono_nowe.append(tytul)
        
        # Zapisywanie nowych raportów do historii, aby nie wysyłać ich ponownie
        if znaleziono_nowe:
            with open(history_file, 'a', encoding='utf-8') as f:
                for t in znaleziono_nowe:
                    f.write(t + "\n")
            print(f"Zakończono: Wysłano {len(znaleziono_nowe)} nowych powiadomień.")
        else:
            print("Zakończono: Brak nowych raportów dla obserwowanych spółek.")

    except Exception as e:
        print(f"Wystąpił błąd krytyczny: {e}")

if __name__ == "__main__":
    monitoruj()

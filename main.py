import requests
from bs4 import BeautifulSoup
import smtplib
import os
from email.mime.text import MIMEText

# --- KONFIGURACJA ---
# Skrypt monitoruje teraz strumień wiadomości (raporty ESPI + newsy redakcyjne)
OBSERWOWANE = ["KGHM", "CD PROJEKT", "SYNEKTIK", "ORLEN", "BUDIMEX"]
URL_ZRODLO = "https://www.bankier.pl/gielda/wiadomosci/wiadomosci-ze-spolek"
BASE_URL = "https://www.bankier.pl"

EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')

def wyslij_mail(spolka, tytul, link_raportu):
    # Tworzenie czytelnej treści maila
    tresc = (f"UWAGA! Nowa wiadomość/raport dla spółki {spolka}:\n\n"
             f"Tytuł: {tytul}\n\n"
             f"Link bezpośredni: {link_raportu}\n\n"
             f"Źródło: {URL_ZRODLO}")
    
    msg = MIMEText(tresc, 'plain', 'utf-8')
    msg['Subject'] = f"ALERT GPW: {spolka} - {tytul[:40]}..."
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER

    try:
        # SMTP dla Onet.pl (Port 465 + SSL)
        with smtplib.SMTP_SSL('smtp.poczta.onet.pl', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f">>> Sukces: Wysłano powiadomienie o {spolka}")
    except Exception as e:
        print(f">>> Błąd wysyłki dla {spolka}: {e}")

def monitoruj():
    print(f"Rozpoczynam sprawdzanie Bankiera pod kątem newsów i raportów...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(URL_ZRODLO, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Pobieramy wszystkie linki (a), ponieważ w tej sekcji tytuły newsów 
        # mogą mieć różne klasy w zależności od typu artykułu.
        wpisy = soup.find_all('a')
        
        history_file = "history.txt"
        if not os.path.exists(history_file):
            with open(history_file, 'w', encoding='utf-8') as f:
                f.write("")
        
        with open(history_file, 'r', encoding='utf-8') as f:
            wyslane_juz = f.read().splitlines()

        nowe_znaleziska = []
        
        for wpis in wpisy:
            tytul = wpis.get_text().strip()
            link_rel = wpis.get('href', '')
            
            # Filtry: tytuł musi mieć sensowną długość, a link musi prowadzić do wiadomości
            if len(tytul) < 15 or "/wiadomosc/" not in link_rel:
                continue
                
            tytul_up = tytul.upper()
            for spolka in OBSERWOWANE:
                # Jeśli nazwa spółki jest w tytule i jeszcze tego nie wysyłaliśmy
                if spolka in tytul_up and tytul not in wyslane_juz:
                    pelny_link = BASE_URL + link_rel if link_rel.startswith('/') else link_rel
                    
                    print(f"🎯 Znaleziono pasujący temat: {spolka} -> {tytul}")
                    wyslij_mail(spolka, tytul, pelny_link)
                    nowe_znaleziska.append(tytul)
                    # Zatrzymujemy sprawdzanie innych spółek dla tego jednego tytułu
                    break 
        
        # Zapisujemy nowe tytuły do historii, żeby nie spamować przy kolejnym uruchomieniu
        if nowe_znaleziska:
            with open(history_file, 'a', encoding='utf-8') as f:
                for t in nowe_znaleziska:
                    f.write(t + "\n")
            print(f"Historia zaktualizowana o {len(nowe_znaleziska)} pozycji.")
        else:
            print("Nie znaleziono nowych wiadomości dla Twoich spółek.")
            
    except Exception as e:
        print(f"Wystąpił błąd podczas pracy skryptu: {e}")

if __name__ == "__main__":
    monitoruj()

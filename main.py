import requests
from bs4 import BeautifulSoup
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- KONFIGURACJA ---
OBSERWOWANE = ["KGHM", "CD PROJEKT", "SYNEKTIK", "ORLEN", "BUDIMEX"]
URL_ZRODLO = "https://www.bankier.pl/gielda/wiadomosci/wiadomosci-ze-spolek"
BASE_URL = "https://www.bankier.pl"

EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')

# Szablon HTML (Zdefiniowany jako zwykły tekst, aby nie psuć kolorowania)
HTML_TEMPLATE = """
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f5f5f7; color: #1d1d1f; margin: 0; padding: 0;">
    <div style="width: 100%; padding: 40px 0;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
            <div style="padding: 40px;">
                <p style="font-size: 14px; font-weight: 500; color: #06c; margin-bottom: 8px;">Monitor Giełdowy | Powiadomienie</p>
                <h2 style="font-size: 24px; font-weight: 700; color: #1d1d1f; margin-top: 0; margin-bottom: 24px; line-height: 1.2;">{{spolka}}</h2>
                <p style="font-size: 16px; color: #515154; line-height: 1.6; margin-bottom: 30px;">
                    Pojawiła się nowa informacja dotycząca Twojej obserwowanej spółki:<br><br>
                    <strong>{{tytul}}</strong>
                </p>
                <div style="text-align: center;">
                    <a href="{{link}}" style="background-color: #06c; color: white; padding: 10px 22px; text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 600; display: inline-block;">
                        Dowiedz się więcej >
                    </a>
                </div>
            </div>
            <div style="background-color: #fbfbfd; color: #86868b; padding: 20px 40px; text-align: center; font-size: 12px; border-top: 1px solid #d2d2d7;">
                <p style="margin: 0;">Źródło: Bankier.pl | System Automatyczny</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

def wyslij_mail(spolka, tytul, link_raportu):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"INFO: Nowy raport dla spółki {spolka}"
    msg['From'] = f"Monitor Finansowy <{EMAIL_USER}>"
    msg['To'] = EMAIL_USER

    # Wstawianie danych do szablonu w bezpieczny sposób
    html_final = HTML_TEMPLATE.replace("{{spolka}}", spolka).replace("{{tytul}}", tytul).replace("{{link}}", link_raportu)

    part_html = MIMEText(html_final, 'html', 'utf-8')
    msg.attach(part_html)

    try:
        with smtplib.SMTP_SSL('smtp.poczta.onet.pl', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f">>> Wysłano: {spolka}")
    except Exception as e:
        print(f">>> Błąd wysyłki: {e}")

def monitoruj():
    print("Skanowanie wiadomości...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(URL_ZRODLO, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        wpisy = soup.find_all('a')
        
        history_file = "history.txt"
        if not os.path.exists(history_file):
            open(history_file, 'w', encoding='utf-8').close()
        
        with open(history_file, 'r', encoding='utf-8') as f:
            wyslane = f.read().splitlines()

        for wpis in wpisy:
            tytul = wpis.get_text().strip()
            link_rel = wpis.get('href', '')
            
            if len(tytul) < 15 or "/wiadomosc/" not in link_rel:
                continue
                
            tytul_up = tytul.upper()
            for spolka in OBSERWOWANE:
                if spolka in tytul_up and tytul not in wyslane:
                    pelny_link = BASE_URL + link_rel if link_rel.startswith('/') else link_rel
                    wyslij_mail(spolka, tytul, pelny_link)
                    with open(history_file, 'a', encoding='utf-8') as f:
                        f.write(tytul + "\n")
                    break 
    except Exception as e:
        print(f"Błąd: {e}")

if __name__ == "__main__":
    monitoruj()

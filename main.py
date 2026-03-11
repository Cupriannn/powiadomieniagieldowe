import requests
from bs4 import BeautifulSoup
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- KONFIGURACJA ---
OBSERWOWANE = ["KGHM", "CD PROJEKT", "SYNEKTIK", "ORLEN"]
URL_ZRODLO = "https://www.bankier.pl/gielda/wiadomosci/wiadomosci-ze-spolek"
BASE_URL = "https://www.bankier.pl"

EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')

def wyslij_mail(spolka, tytul, link_raportu):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🔔 ALERT GPW: {spolka}"
    msg['From'] = f"Monitor Giełdowy <{EMAIL_USER}>"
    msg['To'] = EMAIL_USER

    # Budujemy HTML w sposób, który nie "psuje" kolorowania składni w edytorze
    html_template = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 20px auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #1a73e8; color: white; padding: 20px; text-align: center;">
                <h2 style="margin: 0;">Nowa wiadomość: {spolka}</h2>
            </div>
            <div style="padding: 25px; background-color: #ffffff;">
                <p style="font-size: 16px; font-weight: bold; color: #000;">{tytul}</p>
                <div style="text-align: center; margin-top: 25px;">
                    <a href="{link}" style="background-color: #1a73e8; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                        PRZECZYTAJ ARTYKUŁ
                    </a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Wstrzykujemy dane do szablonu (bezpieczniejsza metoda formatowania)
    html_final = html_template.format(spolka=spolka, tytul=tytul, link=link_raportu)

    part_html = MIMEText(html_final, 'html', 'utf-8')
    msg.attach(part_html)

    try:
        with smtplib.SMTP_SSL('smtp.poczta.onet.pl', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f">>> Sukces: {spolka}")
    except Exception as e:
        print(f">>> Błąd: {e}")

def monitoruj():
    print("Sprawdzanie Bankiera...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
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

import os
import time
import requests
import telebot
import zipfile
import shutil
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread

# ═══════════════════════════════════════════
# अपना BOT TOKEN यहाँ डालें 👇
BOT_TOKEN = "8911047284:AAHASm2LGSByYJO8OsqBVJnFwlpcHsqrnNU"
# ═══════════════════════════════════════════

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Render को जगाए रखने के लिए वेब सर्वर
@app.route('/')
def home():
    return "Aryan's Advanced Code Scraper is Running!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port)

# एंटी-स्लीप सिस्टम
def keep_alive_ping():
    while True:
        time.sleep(600) 
        try:
            url = os.environ.get('RENDER_EXTERNAL_URL', f"http://127.0.0.1:{os.environ.get('PORT', 8080)}")
            requests.get(url, timeout=10)
        except:
            pass

# फाइल का नाम सेट करने वाला फंक्शन (हर नाम के आगे Aryan_ लगाएगा)
def get_aryan_filename(url, default_name):
    name = os.path.basename(urlparse(url).path)
    if not name or "." not in name:
        name = default_name
    return f"Aryan_{name}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "नमस्ते आर्यन! मुझे किसी भी वेबसाइट का लिंक भेजो। मैं उसकी HTML, CSS, और JS सब अलग-अलग निकालकर ZIP फाइल में दे दूंगा।")

@bot.message_handler(func=lambda message: True)
def fetch_website_files(message):
    url = message.text.strip()
    
    if not url.startswith("http"):
        url = "https://" + url
        
    status_msg = bot.reply_to(message, "⏳ वेबसाइट को स्कैन किया जा रहा है... इसमें कुछ सेकंड लग सकते हैं।")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # एक टेम्प्रेरी फोल्डर बनाना जहाँ सारी फाइलें रखी जाएंगी
        folder_name = f"Aryan_Scraped_{message.chat.id}"
        os.makedirs(folder_name, exist_ok=True)
        files_to_zip = []
        
        content_type = response.headers.get('Content-Type', '').lower()
        
        # अगर लिंक किसी HTML वेबसाइट का है, तो उसका ऑपरेशन शुरू करो
        if 'text/html' in content_type:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. HTML फाइल सेव करना
            html_path = os.path.join(folder_name, "Aryan_index.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            files_to_zip.append(html_path)
            
            # 2. CSS फाइलें ढूँढना और डाउनलोड करना (Limit: Top 10 files)
            css_links = soup.find_all("link", rel="stylesheet")
            for i, link in enumerate(css_links[:10]):
                href = link.get("href")
                if href:
                    css_url = urljoin(url, href)
                    try:
                        css_res = requests.get(css_url, headers=headers, timeout=5)
                        if css_res.status_code == 200:
                            css_name = get_aryan_filename(css_url, f"style_{i}.css")
                            css_path = os.path.join(folder_name, css_name)
                            with open(css_path, "w", encoding="utf-8") as f:
                                f.write(css_res.text)
                            files_to_zip.append(css_path)
                    except:
                        continue # अगर कोई एक CSS फेल हो जाए तो बाकी को जारी रखो
                        
            # 3. JS (JavaScript) फाइलें ढूँढना (Limit: Top 10 files)
            js_links = soup.find_all("script", src=True)
            for i, script in enumerate(js_links[:10]):
                src = script.get("src")
                if src:
                    js_url = urljoin(url, src)
                    try:
                        js_res = requests.get(js_url, headers=headers, timeout=5)
                        if js_res.status_code == 200:
                            js_name = get_aryan_filename(js_url, f"script_{i}.js")
                            js_path = os.path.join(folder_name, js_name)
                            with open(js_path, "w", encoding="utf-8") as f:
                                f.write(js_res.text)
                            files_to_zip.append(js_path)
                    except:
                        continue

        # अगर लिंक किसी डायरेक्ट कोड (जैसे .py, .js) का है, तो सिर्फ उसे सेव करो
        else:
            ext = os.path.splitext(urlparse(url).path)[1]
            if not ext: ext = ".txt"
            file_path = os.path.join(folder_name, f"Aryan_Code{ext}")
            with open(file_path, "wb") as f:
                f.write(response.content)
            files_to_zip.append(file_path)

        # 4. सारी फाइलों को एक ZIP में पैक करना
        zip_filename = f"Aryan_Website_Files.zip"
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file in files_to_zip:
                # फोल्डर स्ट्रक्चर हटाकर सिर्फ फाइल का नाम ZIP में डालना
                zipf.write(file, os.path.basename(file))
                
        # 5. ZIP फाइल को टेलीग्राम पर भेजना
        with open(zip_filename, "rb") as f:
            bot.send_document(
                message.chat.id, 
                f, 
                caption=f"✅ **लिंक:** {url}\n\nइस ZIP में HTML, CSS और JS सब अलग-अलग फाइलों में है।\n**(हर फाइल का नाम Aryan_ से शुरू होता है)**", 
                parse_mode="Markdown"
            )
            
        # 6. सफाई (कचरा डिलीट करना ताकि सर्वर फुल न हो)
        shutil.rmtree(folder_name)
        os.remove(zip_filename)
        bot.delete_message(message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ एरर आ गया:\n`{e}`\n\n(शायद लिंक गलत है या सर्वर ने ब्लॉक कर दिया है)", 
                              chat_id=message.chat.id, 
                              message_id=status_msg.message_id,
                              parse_mode="Markdown")

if __name__ == "__main__":
    t_web = Thread(target=run)
    t_web.start()
    
    t_ping = Thread(target=keep_alive_ping)
    t_ping.daemon = True  
    t_ping.start()
    
    print("[BOT STARTED] Aryan's Advanced Scraper Bot is running...")
    bot.polling(none_stop=True)

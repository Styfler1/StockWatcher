import streamlit as st
import requests
import time
import yfinance as yf
import plotly.express as px
import datetime
import pandas as pd # <- EZ HIÁNYZOTT!
import concurrent.futures
import google.generativeai as genai
from openai import OpenAI
import re
from streamlit_local_storage import LocalStorage
import json

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from streamlit_autorefresh import st_autorefresh


# ==========================================
# --- 1.2 MULTILANGUAGE DICTIONARY ---
# ==========================================
# Ebben a szótárban tároljuk az összes szöveget mindkét nyelven.
translations = {
    'hu': {
        'page_title': "Tőzsde Figyelő",
        'sidebar_central': "📈 Tőzsde Központ",
        'sidebar_menu': ["📈 Tőzsde Figyelő", "💰 Portfólióm", "ℹ️ A programról"],
        'sidebar_search': "🔍 Keresés",
        'sidebar_trending': "🔥 Trending",
        'sidebar_popular': "🌟 Népszerű",
        'search_placeholder': "Írd be a nevet vagy kódot:",
        'favorites': "⭐ Kedvencek",
        'fav_check': "⭐ Kedvencnek jelölöm",
        'buy_price': "Vásárlási ár (USD):",
        'qty': "Mennyiség (db):",
        'add_btn': "Hozzáadás",
        'delete_btn': "Törlés",
        'portfolio_title': "💰 Saját Portfólióm",
        'portfolio_empty': "Még nincs semmi a portfóliódban.",
        'add_stock_expander': "➕ Új részvény hozzáadása",
        'search_stock': "🔍 Keress rá egy eszközre:",
        'groq_help': "Ide másold be a gsk_ kezdetű kulcsod.",
        'groq_warning': "⚠️ Adj meg egy Groq kulcsot az AI elemzésekhez!",
        'current_price': "Aktuális ár:",
        'period_radio': "Időtáv:",
        'historical_fig_labels': {'Close': 'Árfolyam (USD)', 'index': 'Dátum'},
        'notification_subheader': "🔔 Értesítések beállítása",
        'news_and_analysis': "**Hírek és Elemzések**",
        'request_news_toggle': "Hírek kérése",
        'email_label': "E-mail a riasztásokhoz:",
        'email_placeholder': "pelda@email.hu",
        'email_saved': "✅ Mentve!",
        'email_error': "❌ Érvénytelen formátum!",
        'lower_limit': "**Alsó limit (Stop-Loss)**",
        'upper_limit': "**Felső limit (Célár)**",
        'about_usage_title': "📖 Használati útmutató",
        'about_usage_text': """
            ### 🤖 AI Szolgáltatások aktiválása
            A teljes élményhez kérjen egy ingyenes **Groq API kulcsot** a [Groq Console](https://console.groq.com/) oldalon, majd illessze be a bal oldali sávban található **AI Beállítások** mezőbe. Ekkor a portfólió elemző és a hírek gyorselemzése is elérhetővé válik.

            ### 🔔 Értesítések és Frissítés
            A program az **árfolyamokat 1 percenként**, a **híreket pedig 30 percenként** ellenőrzi automatikusan.
            
            > **⚠️ FONTOS FIGYELMEZTETÉS:**
            > Mivel az alkalmazás nem használ központi szervert az adatok tárolására, az értesítések **csak akkor működnek**, ha:
            > 1. A böngészőben **nyitva van az oldal**.
            > 2. A számítógép **bekapcsolt állapotban** van.
            > 3. Az **Auto-Refresh** (automatikus frissítés) funkció aktív.
            
            A legprecízebb élmény érdekében ajánlott a programot egy folyamatosan futó szerveren vagy egy dedikált, állandóan működő számítógépen nyitva hagyni.

            ### 🔒 Adatkezelés és Mentés
            Minden adatot (e-mail, API kulcs, portfólió) a böngésző **LocalStorage** (helyi tároló) része őriz meg. Ez azt jelenti, hogy ha másik gépet vagy másik böngészőt használ, az adatok nem lesznek ott. 
            **Tipp:** Használja az **Exportálás** funkciót a *Portfólióm* menüpont legalján, hogy biztonsági mentést készítsen vagy átvigye adatait egy másik eszközre!
        """,
        'limit_placeholder': "USD érték",
        'toast_low': "🛑 beeett {low} USD alá!",
        'toast_high': "💰 elérte a {high} USD-t!",
        'chat_title': "💬 AI Pénzügyi Asszisztens",
        'chat_init_msg': "Szia! Én vagyok az AI asszisztensed. Miben segíthetek a(z) {symbol} részvénnyel kapcsolatban?",
        'chat_input_placeholder': "Kérj véleményt a(z) {symbol} részvényről...",
        'ai_spinner': "Elemzés folyamatban...",
        'system_prompt_base': "Te egy profi magyar pénzügyi asszisztens vagy. A felhasználó a(z) {selected} részvényt elemzi. A részvény jelenlegi ára: {current_price} USD.",
        'ai_disclaimer': "⚠️ Az AI asszisztens által adott válaszok kizárólag edukációs és tájékoztató jellegűek, nem minősülnek pénzügyi tanácsadásnak.",
        'about_title': "ℹ️ A programról",
        'about_intro': "Üdvözlünk a Tőzsde Figyelő alkalmazásban!",
        'about_goal_title': "🎯 A program célja",
        'about_goal_text': """
            Ez a program egy modern részvénykövető és portfóliómenedzser alkalmazás. Legfőbb funkciói:
            * Valós idejű árfolyamok követése a világpiacon.
            * Portfólió kezelés, nyereség és veszteség számítása.
            * Okos értesítések kérése hírekről és árfolyamokról.
            * AI alapú elemzés a hírek és a portfólió gyors értékelésére.
            """,
        'about_ai_title': "🤖 Mesterséges Intelligencia",
        'about_ai_text': """
            A program a villámgyors **Groq AI** technológiát használja.
            Ennek használatához egy saját, ingyenes API kulcsra van szükséged, amelyet mindössze 2 perc alatt igényelhetsz a [Groq Console](https://console.groq.com/) weboldalán.
            """,
        'about_data_title': "🔒 Adatvédelem és Adatkezelés",
        'about_data_info': """
            **Semmilyen adatot nem tárolunk rólad szervereken!**
            
            Minden megadott adatod kizárólag a te saját böngésződ memóriájában (LocalStorage) tárolódik.
            
            *💡 Fontos: Ha egy másik számítógépről, másik böngészőből nyitod meg az oldalt, vagy törlöd a böngészési adatokat, a beállításaidat újra meg kell adnod!*
            """,
        'about_notif_title': "🔔 Értesítési rendszer",
        'about_notif_text': """
            Minden egyes részvényhez egyedi szabályokat állíthatsz be. A program e-mailen keresztül képes értesíteni téged, ha:
            * Új, piacmozgató hír jelenik meg a cégről.
            * Az árfolyam eléri az általad beállított **célárat** (Felső limit).
            * Az árfolyam beesik a **kockázati szinted** alá (Alsó limit).
            """,
        'about_disclaimer_title': "⚠️ JOGI NYILATKOZAT",
        'about_disclaimer_text': """
            Az AI által készített elemzések, összefoglalók és a Portfólió Asszisztens válaszai **kizárólag tájékoztató jellegűek**.
            
            Az AI **nem helyettesíti a képesített pénzügyi szakembereket**, és az általa generált tartalom **semmilyen formában nem minősül befektetési vagy pénzügyi tanácsadásnak**.
            """,
        'port_chat_title': "🤖 Portfólió Menedzser Asszisztens",
        'port_chat_init': "Szia! Én vagyok az AI Portfólió Menedzsered. Átnéztem a fenti adataidat. Miben segíthetek?",
        'port_chat_input': "Kérj véleményt a portfóliódról...",
        'port_chat_system_base': "Te egy profi magyar pénzügyi elemző vagy. A felhasználó portfóliója így néz ki:"
    },
    'en': {
        'page_title': "Stock Watcher",
        'sidebar_central': "📈 Stock Hub",
        'sidebar_menu': ["📈 Stock Hub", "💰 My Portfolio", "ℹ️ About"],
        'sidebar_search': "🔍 Search",
        'sidebar_trending': "🔥 Trending",
        'sidebar_popular': "🌟 Popular",
        'search_placeholder': "Enter name or symbol:",
        'favorites': "⭐ Favorites",
        'fav_check': "⭐ Add to Favorites",
        'buy_price': "Purchase Price (USD):",
        'qty': "Quantity (pcs):",
        'add_btn': "Add",
        'delete_btn': "Delete",
        'portfolio_title': "💰 My Portfolio",
        'portfolio_empty': "Your portfolio is currently empty.",
        'add_stock_expander': "➕ Add New Stock",
        'search_stock': "🔍 Search for an asset:",
        'groq_help': "Paste your key starting with gsk_ here.",
        'groq_warning': "⚠️ Provide a Groq key for AI analysis!",
        'current_price': "Current Price:",
        'period_radio': "Time Period:",
        'historical_fig_labels': {'Close': 'Price (USD)', 'index': 'Date'},
        'notification_subheader': "🔔 Set Notifications",
        'news_and_analysis': "**News & Analysis**",
        'request_news_toggle': "Request News",
        'email_label': "Email for Alerts:",
        'about_usage_title': "📖 User Guide",
        'about_usage_text': """
            ### 🤖 Activating AI Features
            To get the full experience, request a free **Groq API key** at [Groq Console](https://console.groq.com/) and paste it into the **AI Settings** field in the sidebar. This enables the Portfolio Assistant and instant News Analysis.

            ### 🔔 Notifications and Updates
            The app refreshes **stock prices every minute** and checks for **news every 30 minutes**.
            
            > **⚠️ CRITICAL NOTE:**
            > Since the app does not store data on a central server, notifications **will only work if**:
            > 1. The website is **kept open** in your browser.
            > 2. Your computer remains **turned on**.
            > 3. The **Auto-Refresh** feature is enabled.
            
            For the best reliability, it is recommended to run the app on a 24/7 server or a dedicated, always-on computer.

            ### 🔒 Data and Backups
            All settings (email, API keys, portfolio) are saved in your browser's **LocalStorage**. They will not be available on other devices or browsers. 
            **Tip:** Use the **Export** function at the bottom of the *My Portfolio* menu to back up your data or transfer it to another device!
        """,
        'email_placeholder': "example@email.com",
        'email_saved': "✅ Saved!",
        'email_error': "❌ Invalid format!",
        'lower_limit': "**Lower Limit (Stop-Loss)**",
        'upper_limit': "**Upper Limit (Target Price)**",
        'limit_placeholder': "USD value",
        'toast_low': "🛑 beesett {low} USD alá!",
        'toast_high': "💰 elérte a {high} USD-t!",
        'chat_title': "💬 AI Financial Assistant",
        'chat_init_msg': "Hi! I am your AI assistant. How can I help with {symbol}?",
        'chat_input_placeholder': "Request AI opinion on {symbol}...",
        'ai_spinner': "Analysis in progress...",
        'system_prompt_base': "You are a professional financial assistant. User is analyzing {selected}. Current price is {current_price} USD.",
        'ai_disclaimer': "⚠️ AI-generated analysis is for educational purposes only, not financial advice.",
        'about_title': "ℹ️ About the App",
        'about_intro': "Welcome to the Stock Watcher application!",
        'about_goal_title': "🎯 App Purpose",
        'about_goal_text': """
            This software is a modern stock tracker and portfolio manager. Key features:
            * Tracking real-time world market prices.
            * Portfolio management, calculation of profit and loss.
            * Setting smart news and price notifications.
            * AI-powered analysis for rapid news and portfolio assessment.
            """,
        'about_ai_title': "🤖 Artificial Intelligence",
        'about_ai_text': """
            The app uses the blazing-fast **Groq AI** technology.
            You need a free API key, which you can get in 2 minutes on the [Groq Console](https://console.groq.com/) website.
            """,
        'about_data_title': "🔒 Data Privacy",
        'about_data_info': """
            **We do not store any of your data on servers!**
            
            All your entered data is stored exclusively in your own browser's memory (LocalStorage).
            
            *💡 Important: If you use another browser or clear browsing data, you must re-enter your data!*
            """,
        'about_notif_title': "🔔 Notification System",
        'about_notif_text': """
            You can set custom rules for each stock. The app sends email notifications when:
            * New, market-moving news appears about the company.
            * The price reaches your **target price** (Upper limit).
            * The price drops below your **risk level** (Lower limit).
            """,
        'about_disclaimer_title': "⚠️ LEGAL DISCLAIMER",
        'about_disclaimer_text': """
            AI-generated analysis, summaries, and Portfolio Assistant responses are **for informational purposes only**.
            
            The AI **is not a substitute for qualified financial professionals**, and the content **does not constitute investment or financial advice**.
            """
    }
}


localS = LocalStorage()

# --- 1. WEBOLDAL BEÁLLÍTÁSAI ---
st.set_page_config(page_title="Tőzsde Figyelő", page_icon="📈", layout="wide")

st.markdown("""
    <style>
        /* Alapesetben (mobilon) nincs nagy margó */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        /* Ha a kijelző szélesebb, mint 800px (asztali gép), akkor jöhet a 5rem margó */
        @media (min-width: 800px) {
            .block-container {
                padding-left: 5rem !important;
                padding-right: 5rem !important;
                padding-top: 2rem !important;
            }
        }

        /* Az első elem feletti üres hely finomhangolása */
        [data-testid="stAppViewBlockContainer"] {
            padding-top: 1rem !important;
        }

        /* Sidebar fejléc igazítása */
        [data-testid="stSidebarHeader"] {
            padding-top: 0.5rem !important;
            min-height: 2rem !important; 
        }
        
        /* Metrikák (kártyák) mobilbarát méretezése */
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# Természetesen ide a saját, valódi Gemini API kulcsodat kell beírnod majd!


# --- 2. SESSION STATE (Állapotok inicializálása) ---

if 'language' not in st.session_state:
    st.session_state.language = 'hu'

# 1. LÉPÉS: Alapváltozók létrehozása
if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = "AAPL"
if 'subscribed_news' not in st.session_state:
    st.session_state.subscribed_news = set()
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []
if 'favorites' not in st.session_state:
    st.session_state.favorites = set()
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'price_alerts' not in st.session_state:
    st.session_state.price_alerts = {}
if 'ai_analyses' not in st.session_state:
    st.session_state.ai_analyses = {}

# 2. LÉPÉS: Adatok lekérése a böngésző memóriájából
saved_portfolio = localS.getItem("stored_portfolio")
saved_favorites = localS.getItem("stored_favorites")
saved_email = localS.getItem("stored_email")
saved_alerts = localS.getItem("stored_alerts")
saved_news_subs = localS.getItem("stored_news_subs") # ÚJ: Hír feliratkozások



# 3. LÉPÉS: Betöltés a memóriába (Csak legelső alkalommal)

# --- SESSION STATE ELEJÉN ---
if 'subscribed_alerts' not in st.session_state:
    st.session_state.subscribed_alerts = set()
    
if 'seen_news' not in st.session_state:
    # Betöltjük a korábban már elküldött hírek azonosítóit
    saved_seen_news = localS.getItem("stored_seen_news")
    st.session_state.seen_news = set(saved_seen_news) if saved_seen_news else set()


if 'sent_alerts' not in st.session_state:
    st.session_state.sent_alerts = {} # Formátum: {"AAPL_low": "2024-03-20"}

# Betöltés LocalStorage-ból
saved_alert_subs = localS.getItem("stored_alert_subs")
if saved_alert_subs is not None and 'loaded_alert_subs' not in st.session_state:
    st.session_state.subscribed_alerts = set(saved_alert_subs)
    st.session_state.loaded_alert_subs = True

if saved_portfolio and 'loaded_port' not in st.session_state:
    st.session_state.portfolio = saved_portfolio
    st.session_state.loaded_port = True

if saved_favorites and 'loaded_fav' not in st.session_state:
    st.session_state.favorites = set(saved_favorites)
    st.session_state.loaded_fav = True

# --- SESSION STATE INICIALIZÁLÁSA (A kód elején) ---
if 'ai_analyses' not in st.session_state:
    st.session_state.ai_analyses = {}

# JAVÍTÁS ITT: "is not None" kell ide, nem csak "saved_news_subs"
if saved_news_subs is not None and 'loaded_news' not in st.session_state:
    st.session_state.subscribed_news = set(saved_news_subs)
    st.session_state.loaded_news = True

if saved_email and 'loaded_email' not in st.session_state:
    st.session_state.user_email = saved_email
    st.session_state.loaded_email = True

# JAVÍTÁS ITT IS:
if saved_alerts is not None and 'loaded_alerts' not in st.session_state:
    st.session_state.price_alerts = saved_alerts
    st.session_state.loaded_alerts = True

# --- 3. FÜGGVÉNYEK DEFINIÁLÁSA ---
@st.cache_data(ttl=3600)
def search_stock(query):
    if not query: return []
    # A Yahoo Finance belső keresőjét hívjuk meg, ehhez nem kell token!
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        results = data.get('quotes', [])
        
        # Átalakítjuk a formátumot, hogy ugyanúgy működjön a kódod többi részével
        formatted_results = []
        for res in results:
            if 'symbol' in res:
                formatted_results.append({
                    'symbol': res['symbol'],
                    'description': res.get('longname') or res.get('shortname') or res['symbol']
                })
        return formatted_results[:5]
    except Exception as e:
        return []
    


def send_email_alert(target_email, subject, body):
    # ELLENŐRZÉS: Vannak-e titkok beállítva?
    if "EMAIL_USER" not in st.secrets or "EMAIL_PASSWORD" not in st.secrets:
        st.error("❌ E-mail küldési hiba: Hiányzó API titkok (Secrets)!")
        return False
        
    sender_email = st.secrets["EMAIL_USER"]
    sender_password = st.secrets["EMAIL_PASSWORD"]
    # ... a többi rész marad ugyanaz ...
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = target_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Hiba az e-mail küldésekor: {e}")
        return False


def get_market_sentiment():
    """Lekéri az S&P 500 RSI-jét, ami jól mutatja a félelem/kapzsiság szintjét (0-100)"""
    try:
        spy = yf.Ticker("^GSPC")
        hist = spy.history(period="1mo")
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1+rs))
        return round(rsi.iloc[-1])
    except:
        return 50 # Középérték, ha hiba van


def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None


@st.cache_data(ttl=86400)
def analyze_news_with_groq(title, summary, stock_symbol, api_key): # Új paraméter: summary
    if not api_key:
        return "❌ Kérlek, add meg a Groq API kulcsodat!"
    
    # Ha nincs összefoglaló, csak a címet használjuk
    context = f"Cím: {title}\nÖsszefoglaló: {summary}" if summary else f"Cím: {title}"
    
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Te egy profi tőzsdei elemző vagy."},
                {"role": "user", "content": f"Elemezd a(z) {stock_symbol} részvényt érintő hírt.\n\n{context}\n\nKérlek, adj egy rövid magyar nyelvű összefoglalót a várható hatásokról emojikkal."}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Hiba: {str(e)}"

@st.cache_data(ttl=3600)
def get_stocks_from_screener(screener_type="trending"):
    if screener_type == "trending":
        url = "https://query1.finance.yahoo.com/v1/finance/trending/US"
    else:
        url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=most_active&count=6"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        quotes = data['finance']['result'][0]['quotes']
        return [q['symbol'] for q in quotes if '^' not in q['symbol'] and '=' not in q['symbol']][:6]
    except:
        return ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "GOOGL"]

@st.cache_data(ttl=60)
def get_live_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        
        # 1. Lekérünk 2 napnyi adatot, hogy tudjunk viszonyítani a tegnapihoz
        hist = ticker.history(period="2d")
        
        if not hist.empty:
            # Az utolsó sor (mai nap) záróára
            current_price = hist['Close'].iloc[-1]
            
            # 2. Változás kiszámítása (ha megvan a tegnapi adat is)
            if len(hist) > 1:
                prev_price = hist['Close'].iloc[-2]
                change = current_price - prev_price
            else:
                # Kriptóknál vagy friss listázásnál előfordulhat, hogy csak 1 nap jön le
                change = 0
                
            # 3. Visszaadjuk a 'c' (current) és 'd' (difference) értékeket a gomboknak
            return {
                'c': round(current_price, 2),
                'd': round(change, 2)
            }
        return None
    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def get_stock_details(symbol):
    ticker = yf.Ticker(symbol)
    try:
        # Megpróbáljuk lekérni az adatokat
        info = ticker.info
        if not info or len(info) < 5: # Ha üres vagy hiányos szótárt kapunk
            raise Exception("Hiányos adatok")
        return info
    except Exception as e:
        # Ha Rate Limit vagy bármi hiba van, visszaadunk egy alap szótárat, hogy ne omoljon össze az app
        return {
            'longName': symbol,
            'currency': 'USD',
            'sector': 'Unknown',
            'marketCap': 0,
            'trailingPE': 'N/A',
            'fiftyTwoWeekHigh': 'N/A'
        }


@st.cache_data(ttl=3600) # 1 óráig megjegyzi az adatokat
def get_cached_ticker_data(symbol):
    t = yf.Ticker(symbol)
    # A .info a leglassabb, ezt csak egyszer kérjük le
    return t.info, t.history(period="1d")

@st.cache_data(ttl=3600)
def get_eur_usd_rate():
    try:
        return yf.Ticker("EURUSD=X").history(period="1d")['Close'].iloc[-1]
    except:
        return 1.08

@st.cache_data(ttl=3600)
def get_historical_data(symbol, period):
    ticker = yf.Ticker(symbol)
    return ticker.history(period=period)

@st.cache_data(ttl=1800) 
def get_stock_news(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.news

def draw_stock_buttons(stock_list, key_prefix):
    fetched_data = {}
    
    # 1. Párhuzamos letöltés (Multithreading)
    # A max_workers=5 azt jelenti, hogy maximum 5 szálon kérjük le az adatokat egyszerre.
    # Nem érdemes sokkal többre állítani, mert a Finnhub API blokkolhat a "támadás" miatt.
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Elküldjük a kéréseket egyszerre a háttérben
        future_to_sym = {executor.submit(get_live_price, sym): sym for sym in stock_list}
        
        # Ahogy megérkeznek a válaszok, elmentjük őket egy szótárba
        for future in concurrent.futures.as_completed(future_to_sym):
            sym = future_to_sym[future]
            fetched_data[sym] = future.result()

    # 2. Gombok kirajzolása az eredeti sorrendben
    for symbol in stock_list:
        data = fetched_data.get(symbol)
        
        if data == "RATE_LIMIT":
            st.sidebar.error(f"⚠️ {symbol} blokkolva (Túl gyors lekérés!).")
            continue
        elif not data or not isinstance(data, dict) or not data.get('c'):
            continue
            
        price = data['c']
        change = data.get('d', 0)
        arrow = "🟩 ⬆" if change > 0 else "🟥 ⬇" if change < 0 else "⬜ ➖"
        
        if st.sidebar.button(f"{symbol} | {price} USD {arrow}", key=f"{key_prefix}_{symbol}", use_container_width=True):
            st.session_state.selected_stock = symbol
            st.rerun()

# ==========================================
# --- 1.1 NYELVVÁLASZTÓ (Sidebar Teteje) ---
# ==========================================
# Két oszlopot csinálunk a bal oldali sávban, hogy a gombok egymás mellett legyenek

st.sidebar.header("📈 Tőzsde Központ")


lang_c1, lang_c2 = st.sidebar.columns(2)

with lang_c1:
    # A use_container_width=True miatt szépen kitöltik a rendelkezésre álló helyet
    if st.button("🇭🇺 HU", use_container_width=True):
        st.session_state.language = 'hu'
        st.rerun()

with lang_c2:
    if st.button("🇺🇸 EN", use_container_width=True):
        st.session_state.language = 'en'
        st.rerun()

st.sidebar.divider() # Egy vékony elválasztó vonal a gombok és a menü közé


# --- GLOBÁLIS ÉRTESÍTÉSI RENDSZER (Minden oldalon fut) ---
def run_global_alerts():
    # Összegyűjtjük az összes olyan ticker-t, amire van bármilyen feliratkozás
    all_watched = st.session_state.subscribed_alerts.union(st.session_state.subscribed_news)
    
    today_str = datetime.date.today().isoformat()
    
    for ticker_sym in all_watched:
        # Adatok lekérése a figyeléshez (Cache-ből jön, ha friss)
        price_data = get_live_price(ticker_sym)
        if not price_data: continue
        
        curr_p = price_data['c']
        alert_limits = st.session_state.price_alerts.get(ticker_sym, {"low": 0.0, "high": 0.0})
        
        # 1. ÁR RIASZTÁSOK ELLENŐRZÉSE
        if ticker_sym in st.session_state.subscribed_alerts and st.session_state.user_email:
            # Alsó limit
            if 0 < float(alert_limits["low"]) > curr_p:
                alert_key = f"{ticker_sym}_low"
                if st.session_state.sent_alerts.get(alert_key) != today_str:
                    if send_email_alert(st.session_state.user_email, f"⚠️ {ticker_sym} Stop-Loss!", f"Ár: {curr_p} USD"):
                        st.session_state.sent_alerts[alert_key] = today_str
            # Felső limit
            if 0 < float(alert_limits["high"]) < curr_p:
                alert_key = f"{ticker_sym}_high"
                if st.session_state.sent_alerts.get(alert_key) != today_str:
                    if send_email_alert(st.session_state.user_email, f"🚀 {ticker_sym} Célár!", f"Ár: {curr_p} USD"):
                        st.session_state.sent_alerts[alert_key] = today_str

        # 2. HÍR RIASZTÁSOK + AI ELEMZÉS
        if ticker_sym in st.session_state.subscribed_news and st.session_state.user_email:
            news = get_stock_news(ticker_sym)
            if news:
                latest = news[0]
                n_data = latest.get('content', latest)
                n_uuid = latest.get('uuid') or n_data.get('url')
                
                if n_uuid not in st.session_state.get('seen_news', []):
                    title = n_data.get('title', 'Új hír')
                    summary = n_data.get('summary', '')
                    # AI elemzés (ha van kulcs)
                    analysis = analyze_news_with_groq(title, summary, ticker_sym, st.session_state.get('groq_api_key', '')) if st.session_state.get('groq_api_key') else "AI elemzés nem készült."
                    
                    body = f"Hír: {title}\nLink: {n_data.get('url')}\n\nAI Elemzés:\n{analysis}"
                    if send_email_alert(st.session_state.user_email, f"📰 Új hír: {ticker_sym}", body):
                        if 'seen_news' not in st.session_state: st.session_state.seen_news = set()
                        st.session_state.seen_news.add(n_uuid)
                        localS.setItem("stored_seen_news", list(st.session_state.seen_news))

# Meghívjuk a figyelőt - ez minden oldalfrissítéskor lefut az összes részvényre!
run_global_alerts()


# --- 4. NAVIGÁCIÓ (FŐ ELÁGAZÁS) ---

menu = st.sidebar.selectbox("Válassz menüpontot:", ["📈 Tőzsde Figyelő", "💰 Portfólióm","📚 Befektetési kisokos", "ℹ️ A programról"])

# --- AUTO REFRESH KAPCSOLÓ A SIDEBARON ---
st.sidebar.divider()
auto_refresh_enabled = st.sidebar.toggle(
    "Automatikus frissítés (1 perc)",
    value=False,
    help="Ha bekapcsolod, az oldal percenként automatikusan újratölt. Ez szükséges ahhoz, hogy a program folyamatosan figyelje az árakat és a híreket, majd e-mailt küldjön neked, ha átlépik a limitet."
)

if auto_refresh_enabled:
    from streamlit_autorefresh import st_autorefresh
    # 60.000 miliszekundum = 1 perc
    st_autorefresh(interval=60000, key="stock_watcher_refresh")

# --- API KULCS BEKÉRÉSE GLOBÁLISAN ---
with st.sidebar.expander("🔑 AI Beállítások (Ingyenes)"):
        st.markdown("Kérj egy ingyenes kulcsot a [Groq Console](https://console.groq.com/)-ban!")
        
        saved_key = localS.getItem("stored_groq_key")
        if 'groq_api_key' not in st.session_state:
            st.session_state.groq_api_key = saved_key if saved_key else ""
            
        current_input = st.text_input(
            "Groq API Key:", 
            value=st.session_state.groq_api_key, 
            type="password", 
            help="A böngésződ biztonságosan megjegyzi a kulcsot!"
        )
        
        if current_input != st.session_state.groq_api_key:
            st.session_state.groq_api_key = current_input
            localS.setItem("stored_groq_key", current_input)
            
        user_api_key = current_input

        if not user_api_key:
            st.warning("⚠️ Adj meg egy Groq kulcsot az AI elemzésekhez!")

if menu == "💰 Portfólióm":
    # ==========================================
    # PORTFÓLIÓ OLDAL (Minden diagrammal)
    # ==========================================
    st.title("💰 Saját Portfólióm")

    with st.expander("➕ Új részvény hozzáadása", expanded=True):
        
        st.write("Keress rá a cég nevére vagy kódjára, majd add meg a vásárlás részleteit!")
        
        search_q = st.text_input(
            "🔍 Keresés (pl. Apple, Tesla, NVDA):", 
            key="port_search",
            help="Nem találod a részvényt, amit keresel? Győződj meg róla, hogy helyesen gépelted be az azonosítót! Ha európai papírt keresel, próbáld a kód végére tenni a '.DE' (német) vagy '.AS' (holland) végződést. Ellenőrizd a pontos kódot a finance.yahoo.com oldalon!"
        )
                
        selected_ticker = None
        
        # 2. Dinamikus találati lista és kiválasztás
        # 2. Dinamikus találati lista és kiválasztás
        if search_q:
            results = search_stock(search_q)
            
            # Adjuk hozzá a manuálisan beírt szöveget is opcióként (Kriptók és Indexek miatt!)
            options = [f"{search_q.upper()} (Közvetlen megadás)"]
            
            if results:
                options += [f"{r['symbol']} ({r['description']})" for r in results]
                
            chosen = st.selectbox("Válaszd ki a pontos eszközt:", options, key="port_select")
            
            # Kinyerjük csak a kódot
            selected_ticker = chosen.split(" ")[0]
        
        st.divider()
        
        # 3. Vásárlási adatok megadása
        st.write("### 💵 Vásárlás részletei")
        
        # Felhasználóbarát választó
        input_type = st.radio("Hogyan szeretnéd megadni az árat?", ["Teljes kifizetett összeg (Befektetés)", "1 db részvény ára (Darabár)"], horizontal=True)
        
        col1, col2 = st.columns(2)
        # Itt levettük a min_value-t 0.0001-re, hogy a nagyon apró törtrészvényeket (vagy kriptót) is kezelje!
        new_qty = col2.number_input("Vásárolt mennyiség (db):", min_value=0.0001, step=0.01, format="%.4f")
        
        if input_type == "Teljes kifizetett összeg (Befektetés)":
            total_cost = col1.number_input("Összesen fizetett összeg (USD):", min_value=0.0, step=1.0)
            # Kiszámoljuk a darabárat a memóriának (Total / Mennyiség)
            actual_buy_price = (total_cost / new_qty) if new_qty > 0 else 0
            if total_cost > 0 and new_qty > 0:
                st.info(f"💡 **A rendszer által kiszámolt darabár:** {actual_buy_price:.2f} USD / db")
        else:
            actual_buy_price = col1.number_input("1 db ára vásárláskor (USD):", min_value=0.0, step=0.1)
            total_cost = actual_buy_price * new_qty
            if actual_buy_price > 0 and new_qty > 0:
                st.info(f"💡 **Összesen befektetett összeg:** {total_cost:.2f} USD")

        # 4. Mentés gomb (Itt a new_price helyett az actual_buy_price-t mentjük!)
        if st.button("Hozzáadás a portfólióhoz", use_container_width=True):
            if selected_ticker and new_qty > 0 and actual_buy_price > 0:
                with st.spinner("Ellenőrzés a piacon..."):
                    test_ticker = yf.Ticker(selected_ticker)
                    test_hist = test_ticker.history(period="1d")
                    if test_hist.empty:
                        st.error(f"❌ Érvénytelen kód: '{selected_ticker}'.")
                    else:
                        st.session_state.portfolio.append({
                            'symbol': selected_ticker, 
                            'buy_price': actual_buy_price, # <-- JAVÍTVA
                            'qty': new_qty
                        })
                        localS.setItem("stored_portfolio", st.session_state.portfolio)
                        st.success(f"✅ {selected_ticker} sikeresen hozzáadva!")
                        time.sleep(1)
                        st.rerun()
            elif not selected_ticker:
                st.error("Kérlek előbb keress rá és válassz ki egy részvényt!")
            else:
                st.warning("A mennyiségnek és az árnak is nagyobbnak kell lennie, mint 0!")

        # --- RÉSZVÉNY ELADÁSA / ELTÁVOLÍTÁSA ---
    with st.expander("➖ Részvény eladása (Teljes vagy részleges)"):
        if not st.session_state.portfolio:
            st.write("Nincs eladható részvényed.")
        else:
            # 1. Kiválasztjuk, melyiket akarjuk eladni
            stock_options = [f"{i}: {item['symbol']} ({item['qty']} db)" for i, item in enumerate(st.session_state.portfolio)]
            selected_to_sell = st.selectbox("Melyik részvényből adsz el?", stock_options)
            
            # Kinyerjük az indexet a szövegből
            idx = int(selected_to_sell.split(":")[0])
            current_item = st.session_state.portfolio[idx]
            
            col_s1, col_s2 = st.columns(2)
            sell_qty = col_s1.number_input("Eladni kívánt mennyiség:", min_value=0.01, max_value=float(current_item['qty']), step=1.0)
            sell_price = col_s2.number_input("Eladási ár (USD):", min_value=0.0, value=float(current_item['buy_price']))

            if st.button("Eladás végrehajtása", use_container_width=True, type="primary"):
                # Számolunk egy gyors profitot az eladásra
                profit = (sell_price - current_item['buy_price']) * sell_qty
                
                if sell_qty < current_item['qty']:
                    # Részleges eladás: csak csökkentjük a darabszámot
                    st.session_state.portfolio[idx]['qty'] -= sell_qty
                    st.toast(f"Eladva {sell_qty} db {current_item['symbol']}. Profit: {profit:.2f} USD", icon="💰")
                else:
                    # Teljes eladás: töröljük a listából
                    st.session_state.portfolio.pop(idx)
                    localS.setItem("stored_portfolio", st.session_state.portfolio)
                    st.toast(f"A teljes {current_item['symbol']} pozíció lezárva. Profit: {profit:.2f} USD", icon="✅")
                
                time.sleep(1)
                st.rerun()

    if not st.session_state.portfolio:
        st.info("Még nincs semmi a portfóliódban. Add meg az első vételedet fentebb!")
    else:
       # --- ADATOK ÖSSZEGYŰJTÉSE ÉS DEVIZAVÁLTÁS (OSZTALÉKKAL) ---
        portfolio_data = []
        total_invested_usd = 0
        current_total_value_usd = 0
        total_annual_dividend_usd = 0  # <--- ÚJ: Ebben gyűjtjük az összes osztalékot
        
        # Lekérjük az aktuális EUR/USD árfolyamot
        try:
            eur_usd_rate = yf.Ticker("EURUSD=X").history(period="1d")['Close'].iloc[-1]
        except:
            # Lekérjük az árfolyamot (cache-ből jön, ha már megvan)
            eur_usd_rate = get_eur_usd_rate()
        
        for item in st.session_state.portfolio:
            # 1. Adatlekérés cache-ből
            info, hist = get_cached_ticker_data(item['symbol'])
            
            # 2. Alapadatok kinyerése biztonságosan
            currency = info.get('currency', 'USD')
            current_price = hist['Close'].iloc[-1] if not hist.empty else item['buy_price']
            sector = info.get('sector', 'Information Technology') # Alapértelmezett, ha nincs meg
            
            # 3. Osztalék számítás (CSAK EGYSZER!)
           # 2. Osztalék számítás egy helyen, tisztán
            div_yield = info.get('dividendYield', 0)
            if div_yield is None: 
                div_yield = 0
            elif div_yield > 0.2: # Javítás a százalékos formátumhoz
                div_yield /= 100
            
            annual_div_native = (current_price * item['qty']) * div_yield

            # 4. Értékek számítása
            invested_native = item['buy_price'] * item['qty']
            current_value_native = current_price * item['qty']
            p_l_native = current_value_native - invested_native
            
            # 5. Átváltás USD-re az összesítéshez
            if currency == 'EUR':
                invested_usd = invested_native * eur_usd_rate
                current_value_usd = current_value_native * eur_usd_rate
                annual_div_usd = annual_div_native * eur_usd_rate
            else:
                invested_usd = invested_native
                current_value_usd = current_value_native
                annual_div_usd = annual_div_native
                
            # 6. Összesítők frissítése
            total_invested_usd += invested_usd
            current_total_value_usd += current_value_usd
            total_annual_dividend_usd += annual_div_usd
            
            portfolio_data.append({
                'Részvény': item['symbol'],
                'Deviza': currency,
                'Befektetve': invested_native,
                'Jelenlegi Érték': current_value_native,
                'Profit/Veszteség': p_l_native,
                'Szektor': sector,
                'Osztalék (Éves)': annual_div_native,
                'Jelenlegi Érték (USD)': current_value_usd, 
                'Befektetve (USD)': invested_usd
            })

        df_portfolio = pd.DataFrame(portfolio_data)

        # --- 1. ÖSSZESÍTŐ METRIKÁK (Javítva) ---
        p_l_total = current_total_value_usd - total_invested_usd
        p_l_percent = (p_l_total / total_invested_usd) * 100 if total_invested_usd > 0 else 0

        # --- 1. ÖSSZESÍTŐ METRIKÁK ---
        c1, c2, c3, c4 = st.columns(4) # 3 helyett 4 oszlop
        c1.metric("Befektetés", f"{total_invested_usd:.2f} $")
        c2.metric("Jelenlegi érték", f"{current_total_value_usd:.2f} $")
        c3.metric("Profit/Veszteség", f"{p_l_total:.2f} $", f"{p_l_percent:.2f}%")
        c4.metric("Várható éves osztalék", f"{total_annual_dividend_usd:.2f} $")

        st.divider()

        # --- DIVERZIFIKÁCIÓ ELLENŐRZÉSE ---
        all_sectors = [
            "Information Technology", "Health Care", "Financials", "Consumer Discretionary", 
            "Communication Services", "Industrials", "Consumer Staples", "Energy", 
            "Utilities", "Real Estate", "Materials"
        ]

        # Kiszámoljuk, melyik szektor hány százalékot tesz ki
        sector_distribution = df_portfolio.groupby('Szektor')['Jelenlegi Érték (USD)'].sum() / current_total_value_usd  

        # 1. Túlkoncentráció figyelmeztetés (60% felett)
        for sector, weight in sector_distribution.items():
            if weight > 0.6:
                st.warning(f"⚠️ **A portfólió nem elég diverzifikált!** Túl nagy része ({weight:.1%}) a(z) **{sector}** szektorból származik.")

        # 2. Hiányzó szektorok figyelmeztetés
        portfolio_sectors = df_portfolio['Szektor'].unique()
        missing_sectors = [s for s in all_sectors if s not in portfolio_sectors]

        if len(missing_sectors) > 5: # Ha például a szektorok több mint fele hiányzik
            st.warning(f"⚠️ **Vigyázat!** A portfólióból számos kulcsfontosságú szektor hiányzik (pl. {', '.join(missing_sectors[:3])}).")


        # --- 2. A 2 DB KÖRDIAGRAM (Kért funkció) ---
        col_pie1, col_pie2 = st.columns(2)
        
        with col_pie1:
            st.write("### 🥧 Részvények eloszlása")
            fig_stock = px.pie(df_portfolio, values='Jelenlegi Érték (USD)', names='Részvény', hole=0.4)
            fig_stock.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_stock, use_container_width=True)
            
        with col_pie2:
            st.write("### 🏢 Szektorok szerinti részesedés")
            # Szektorok szerinti aggregálás a kördiagramhoz
            fig_sector = px.pie(df_portfolio, values='Jelenlegi Érték (USD)', names='Szektor', hole=0.4)
            fig_sector.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_sector, use_container_width=True)

        st.divider()

        

        # --- 3. OSZLOPDIAGRAM (Javítva) ---
        st.write("### 📊 Portfólió Teljesítménye (Összesített és Részvényenként)")

        
        # Létrehozzuk az "Összesen" sort az új változókkal
        df_total = pd.DataFrame({
            'Részvény': ['📊 ÖSSZESEN'],
            'Befektetve (USD)': [total_invested_usd],
            'Jelenlegi Érték (USD)': [current_total_value_usd],
            'Szektor': ['Összesített']
        })

        # Összefűzzük a részvényenkénti USD adatokkal
        df_plot = pd.concat([df_total, df_portfolio.sort_values('Jelenlegi Érték (USD)', ascending=False)], ignore_index=True)

        # Az adatok "melt"-elése a csoporthoz (Marad a régi logika, de az USD oszlopokkal)
        df_melted = df_plot.melt(
            id_vars='Részvény', 
            value_vars=['Befektetve (USD)', 'Jelenlegi Érték (USD)'], 
            var_name='Típus', 
            value_name='Összeg (USD)'
        )

        fig_bar = px.bar(
            df_melted, 
            x='Részvény', 
            y='Összeg (USD)', 
            color='Típus', 
            barmode='group',
            color_discrete_map={'Befektetve (USD)': '#6c757d', 'Jelenlegi Érték (USD)': '#28a745'},
            # Itt a titok: a '.2f' jelentése: fixen 2 tizedesjegy (float)
            text_auto='.2f' 
        )

        # TÁVOLSÁGOK ÉS STÍLUS BEÁLLÍTÁSA
        fig_bar.update_layout(
            bargap=0.35,
            bargroupgap=0.1,
            xaxis={'fixedrange': True}, 
            yaxis={'fixedrange': True}, 
            dragmode=False,
            # Beállítjuk, hogy a feliratok az oszlopokon belül/felett jól látszódjanak
            uniformtext_minsize=8, 
            uniformtext_mode='hide',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        # Figyelem: A kódodban kétszer szerepelt a plotly_chart hívás, 
        # elég csak egyszer, a config-os verziót meghagyni!
        st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

        # --- 4. RÉSZLETES TÁBLÁZAT ---
        # --- 4. RÉSZLETES TÁBLÁZAT ---
        with st.expander("📝 Részletes adatok táblázata (Eredeti devizában)"):
            # Csak a látható oszlopokat mutatjuk (a rejtett USD oszlopokat nem)
            display_columns = ['Részvény', 'Deviza', 'Befektetve', 'Jelenlegi Érték', 'Profit/Veszteség', 'Szektor']
            st.dataframe(df_portfolio[display_columns].style.format({
                'Befektetve': '{:.2f}', 
                'Jelenlegi Érték': '{:.2f}', 
                'Profit/Veszteség': '{:.2f}'
            }), use_container_width=True)


        with st.expander("💰 Részletes Osztalék Elemzés"):
            st.write("Az alábbi összegek éves becsült kifizetések a saját devizájukban:")
            
            # Csak azokat mutatjuk, ahol van értelmezhető osztalék (0-nál nagyobb)
            # Ha látni akarod a nullásokat is, vedd ki a query-t
            df_div_display = df_portfolio[['Részvény', 'Deviza', 'Osztalék (Éves)', 'Szektor']]
            
            # Formázott táblázat megjelenítése
            st.dataframe(df_div_display.style.format({
                'Osztalék (Éves)': '{:.2f}'
            }), use_container_width=True, hide_index=True)
            
            # Egy kis magyarázat a végére
            st.caption("Megjegyzés: Az 'Accumulating' (visszaforgató) ETF-ek (mint a VUAA) 0.00 értéket mutatnak, mivel nem fizetnek készpénzt.")

        if total_annual_dividend_usd > 0:
                st.write("### 🏆 Legnagyobb osztalékfizetőid")
                # Oszlopdiagram az osztalékokról
                fig_div = px.bar(
                    df_portfolio[df_portfolio['Osztalék (Éves)'] > 0], 
                    x='Részvény', 
                    y='Osztalék (Éves)',
                    color='Részvény',
                    text_auto='.2f',
                    title="Éves Osztalék Részvényenként (Eredeti devizában)"
                )
                st.plotly_chart(fig_div, use_container_width=True, key="div_bar_chart")

        
        # ==========================================
        # --- AI PORTFÓLIÓ ELEMZŐ CHATBOX ---
        # ==========================================
        st.divider()
        st.subheader("🤖 Portfólió Menedzser Asszisztens")
        st.info("Kérdezz rá a portfóliódra! Pl.: 'Mennyire kockázatos ez az összeállítás?' vagy 'Milyen szektort javasolsz még hozzáadni?'")

        # Külön chat memória csak a portfólióhoz
        port_chat_key = "messages_portfolio_main"
        if port_chat_key not in st.session_state:
            st.session_state[port_chat_key] = [{"role": "assistant", "content": "Szia! Én vagyok az AI Portfólió Menedzsered. Átnéztem a fenti adataidat. Miben segíthetek a portfólióddal kapcsolatban?"}]

        # Chat ablak kirajzolása
        port_chat_container = st.container(height=400, border=True)
        with port_chat_container:
            for message in st.session_state[port_chat_key]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.chat_input("Kérj véleményt a portfóliódról..."):
            st.session_state[port_chat_key].append({"role": "user", "content": prompt})
            
            with port_chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                    
            with port_chat_container:
                with st.chat_message("assistant"):
                    if not user_api_key:
                        st.error("❌ Kérlek, add meg a Groq API kulcsodat a bal oldali sávban a chateléshez!")
                    else:
                        with st.spinner("Portfólió elemzése folyamatban..."):
                            try:
                                # 1. A Jelenlegi Portfólió Szöveggé alakítása az AI-nak
                                portfolio_context = ""
                                for p_item in portfolio_data:
                                    portfolio_context += f"- {p_item['Részvény']}: {p_item['Jelenlegi Érték (USD)']:.2f} USD érték ({p_item['Szektor']} szektor)\n"
                                
                                # 2. Az Utasítás (System Prompt) felépítése
                                system_prompt = {
                                    "role": "system", 
                                    "content": f"""Te egy profi magyar pénzügyi elemző és portfólió menedzser vagy. 
                                    A felhasználó jelenlegi portfóliója így néz ki:
                                    Összesített érték: {current_total_value_usd:.2f} USD.
                                    Tartalom:
                                    {portfolio_context}
                                    
                                    Kérlek, válaszolj a felhasználó kérdéseire a portfóliójával kapcsolatban. 
                                    Adj építő kritikát a diverzifikációról, szektor-koncentrációról és lehetséges kockázatokról. 
                                    Legyél tárgyilagos, és emeld ki, ha valami túl kockázatos. 
                                    Ne adj direkt befektetési tanácsot, de javasolhatsz elemzésre érdemes iparágakat."""
                                }

                                client = OpenAI(api_key=user_api_key, base_url="https://api.groq.com/openai/v1")
                                
                                # 3. Üzenetek küldése
                                api_messages = [system_prompt] + st.session_state[port_chat_key]
                                
                                response = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=api_messages,
                                    max_tokens=1024
                                )
                                
                                ai_response = response.choices[0].message.content
                                
                                st.markdown(ai_response)
                                st.session_state[port_chat_key].append({"role": "assistant", "content": ai_response})
                                
                            except Exception as e:
                                st.error(f"⚠️ Hálózati vagy API hiba: {str(e)}")


        # --- 5. GYORSJELENTÉSI NAPTÁR (EARNINGS CALENDAR) ---
        st.divider()
        st.header("📅 Közelgő Gyorsjelentések")
        st.write("A portfóliódban és a kedvenceid között szereplő cégek következő negyedéves jelentései.")

        # Összegyűjtjük az összes ticker-t: portfólió + kedvencek
        # Feltételezzük, hogy a kedvencek a st.session_state.favorites-ben vannak
        tracked_tickers = set([item['symbol'] for item in st.session_state.portfolio])
        if 'favorites' in st.session_state:
            tracked_tickers.update(st.session_state.favorites)

        earnings_data = []

        if tracked_tickers:
            with st.spinner('Naptár frissítése...'):
                for symbol in tracked_tickers:
                    try:
                        ticker = yf.Ticker(symbol)
                        calendar = ticker.calendar
                        
                        # A yfinance 'Earnings Date' néven adja vissza a dátumot (lista formátumban)
                        if calendar is not None and 'Earnings Date' in calendar:
                            next_report = calendar['Earnings Date'][0]
                            # Formázzuk a dátumot olvashatóbbra
                            date_str = next_report.strftime('%Y-%m-%d')
                            
                            earnings_data.append({
                                "Részvény": symbol,
                                "Jelentés Dátuma": date_str,
                                "Típus": "Portfólió" if any(item['symbol'] == symbol for item in st.session_state.portfolio) else "Kedvenc"
                            })
                    except:
                        continue # Ha egy tickerhez nincs adat (pl. kripto), kihagyjuk

            if earnings_data:
                # Időrendbe rakjuk, hogy a legközelebbi legyen legfelül
                df_earnings = pd.DataFrame(earnings_data).sort_values(by="Jelentés Dátuma")
                
                # Megjelenítés egy szép táblázatban
                st.dataframe(df_earnings, use_container_width=True, hide_index=True)
                
                st.info("💡 **Miért fontos ez?** A jelentés napján az árfolyam gyakran jelentősen elmozdul a várakozásoktól függően.")
            else:
                st.info("Jelenleg nincs elérhető jelentési dátum a követett papírokhoz.")
        else:
            st.warning("Még nincsenek részvények a portfóliódban vagy a kedvenceid között.")
    

    st.divider()
    st.subheader("💾 Adatok mentése és betöltése")
        
    col_exp, col_imp = st.columns(2)

    with col_exp:
            st.write("**Exportálás**")
            # Összeállítjuk a TELJES mentendő csomagot
            export_data = {
                "portfolio": st.session_state.portfolio,
                "favorites": list(st.session_state.favorites),
                "price_alerts": st.session_state.price_alerts, # A konkrét USD értékek
                "subscribed_news": list(st.session_state.subscribed_news), # Hír kapcsolók
                "subscribed_alerts": list(st.session_state.subscribed_alerts), # Ár riasztás kapcsolók
                "seen_news": list(st.session_state.seen_news),
                "settings": {
                    "email": st.session_state.get('user_email', ''),
                    "groq_key": st.session_state.get('groq_api_key', '')
                }
            }
            json_string = json.dumps(export_data, indent=4)
            
            st.download_button(
                label="📥 Teljes mentés letöltése (JSON)",
                data=json_string,
                file_name="stockwatcher_full_backup.json",
                mime="application/json",
                help="Menti a portfóliót, a kedvenceket, a limiteket és az összes beállítást."
            )

    with col_imp:
        st.write("**Importálás**")
        uploaded_file = st.file_uploader("Biztonsági mentés visszatöltése", type=["json"])
        
        if uploaded_file is not None:
            try:
                import_data = json.load(uploaded_file)
                
                if st.button("🔄 Minden adat felülírása és betöltése"):
                    # 1. ADATOK BETÖLTÉSE A MEMÓRIÁBA (Session State)
                    st.session_state.portfolio = import_data.get("portfolio", [])
                    st.session_state.favorites = set(import_data.get("favorites", []))
                    st.session_state.price_alerts = import_data.get("price_alerts", {})
                    st.session_state.subscribed_news = set(import_data.get("subscribed_news", []))
                    st.session_state.subscribed_alerts = set(import_data.get("subscribed_alerts", []))
                    
                    settings = import_data.get("settings", {})
                    st.session_state.user_email = settings.get("email", "")
                    st.session_state.groq_api_key = settings.get("groq_key", "")

                    # 2. KRITIKUS LÉPÉS: Megjelöljük, hogy az adatok már be vannak töltve!
                    # Ez akadályozza meg, hogy a kódod eleje felülírja őket a régivel.
                    st.session_state.loaded_port = True
                    st.session_state.loaded_fav = True
                    st.session_state.loaded_news = True
                    st.session_state.loaded_email = True
                    st.session_state.loaded_alerts = True
                    st.session_state.loaded_alert_subs = True

                    # 3. KULCS ÜTKÖZÉS JAVÍTÁSA: 
                    # Nem hívunk meg sok setItem-et egyszerre. 
                    # Ehelyett csak egy sikeres üzenetet küldünk, és a rerun után 
                    # az adatok már a memóriában lesznek. A böngészőbe mentés pedig
                    # majd az első manuális változtatáskor (pl. kedvenc gomb) megtörténik.
                    
                    st.success("✅ Adatok betöltve a memóriába! Kérlek, frissíts egyet a mentés véglegesítéséhez.")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Hiba a fájl feldolgozása közben: {e}")

    

elif menu == "ℹ️ A programról":
    # ==========================================
    # A PROGRAMRÓL OLDAL
    # ==========================================
    st.title("ℹ️ A programról")
    st.write("Üdvözlünk a Tőzsde Figyelő alkalmazásban! Ez a felület azért jött létre, hogy egyszerűbbé, átláthatóbbá és okosabbá tegye a befektetéseid kezelését.")
    
    st.divider()

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 A program célja")
        st.write("""
        Ez a szoftver egy modern részvénykövető és portfóliómenedzser alkalmazás. Legfőbb funkciói:
        * **Valós idejű árfolyamok:** Kövesd nyomon a világpiaci részvények aktuális helyzetét.
        * **Portfólió kezelés:** Vezesd a saját befektetéseidet, és lásd azonnal a nyereséget vagy veszteséget.
        * **Okos értesítések:** Kapj azonnali jelzést, ha a piac mozgásba lendül.
        * **AI alapú piacelemzés:** Használd a mesterséges intelligenciát a hírek és a portfóliód gyors értékelésére.
        """)

        st.subheader("🤖 Mesterséges Intelligencia")
        st.write("""
        A program a villámgyors **Groq AI** technológiát használja az elemzésekhez és a chat asszisztenshez. 
        Ennek használatához egy saját, ingyenes API kulcsra van szükséged, amelyet mindössze 2 perc alatt igényelhetsz a [Groq Console](https://console.groq.com/) weboldalán.
        """)

    with col2:
        st.subheader("🔒 Adatvédelem és Adatkezelés")
        st.info("""
        **Semmilyen adatot nem tárolunk rólad szervereken!**
        
        Minden megadott adatod (a portfóliód, az e-mail címed, az API kulcsod és az értesítési limitjeid) kizárólag a **te saját böngésződ memóriájában** (LocalStorage) tárolódik.
        
        *💡 Fontos: Ha egy másik számítógépről, másik böngészőből nyitod meg az oldalt, vagy törlöd a böngészési adatokat, a beállításaidat újra meg kell adnod!*
        """)

        st.subheader("🔔 Értesítési rendszer")
        st.write("""
        Minden egyes részvényhez egyedi szabályokat állíthatsz be. A program e-mailen keresztül képes értesíteni téged, ha:
        * Új, piacmozgató hír jelenik meg a kiválasztott cégről.
        * Az árfolyam eléri az általad beállított **célárat** (Felső limit).
        * Az árfolyam beesik a **kockázati szinted** alá (Alsó limit / Stop-Loss).
        """)

    st.divider()

     # Jogi nyilatkozat kiemelve a lap alján
    st.warning("""
    **⚠️ JOGI NYILATKOZAT / DISCLAIMER**
    
    A beépített Mesterséges Intelligencia (AI) által készített elemzések, összefoglalók és a Portfólió Asszisztens válaszai **kizárólag tájékoztató és edukációs jellegűek**. 
    
    Az AI **nem helyettesíti a képesített pénzügyi szakembereket**, és az általa generált tartalom **semmilyen formában nem minősül befektetési, pénzügyi vagy adóügyi tanácsadásnak**. A tőzsdei befektetések kockázattal járnak, a döntéseket minden esetben saját felelősségedre, alapos tájékozódás után hozd meg!
    """)

    # --- ÚJ: HASZNÁLATI ÚTMUTATÓ SZEKCIÓ ---
    st.header(translations[st.session_state.language]['about_usage_title'])
    st.info(translations[st.session_state.language]['about_usage_text'])



elif menu == "📚 Befektetési kisokos":
        st.title("📚 Befektetési Kisokos")
        st.write("Ezen az oldalon összegyűjtöttük a legfontosabb fogalmakat, hogy magabiztosabban mozoghass a tőzsdén.")

        # --- ALAPFOGALMAK ---
        st.header("🔍 Alapfogalmak")
        
        with st.expander("🏢 Mi az a részvény?", expanded=True):
            st.write("""
            A részvény egy vállalat tulajdonjogának egy darabkája. Ha részvényt veszel, tulajdonos leszel a cégben.
            * **Előnye:** Ha a cég jól megy, nő az árfolyam és osztalékot is kaphatsz.
            * **Veszélye:** Ha a cég csődbe megy, a befektetésed értéke nullára is eshet.
            """)

        with st.expander("📦 Mi az az ETF?"):
            st.write("""
            **Exchange Traded Fund (Tőzsdén Kereskedett Alap).** Képzelj el egy kosarat, amiben több száz cég részvénye van benne.
            * **Előnye:** Diverzifikáció (megosztod a kockázatot). Nem egy cégtől függsz, hanem egy egész piactól (pl. S&P 500).
            * **Veszélye:** Piaci visszaesés esetén az egész kosár értéke csökken.
            """)

        with st.expander("📊 Mi az a P/E ráta?"):
            st.write("""
            **Price-to-Earnings (Árfolyam/Nyereség).** Azt mutatja meg, hogy a cég aktuális ára hányszorosa az egy év alatt megtermelt profitjának.
            * **Alacsony (pl. 10-15):** A részvény olcsónak tűnhet (vagy bajban van a cég).
            * **Magas (pl. 50+):** A befektetők nagy növekedést várnak (vagy túlárazott a papír).
            """)

        with st.expander("🪙 Mi az a Kriptovaluta?"):
            st.write("""
            Digitális fizetőeszközök (pl. Bitcoin, Ethereum), amik mögött nem áll bank vagy állam.
            * **Előnye:** Hatalmas emelkedési potenciál, 24/7 kereskedés.
            * **Veszélye:** **Extrém volatilitás** (akár egy nap alatt 20-30%-ot eshet), nincs rájuk garancia.
            """)

        st.divider()

        # --- PORTFÓLIÓ PÉLDÁK ---
        st.header("🥧 Mintaportfóliók")
        st.write("A kockázattűrő képességed alapján különböző módon oszthatod meg a pénzed.")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("🛡️ Konzervatív")
            st.caption("Biztonságra törekvő")
            data = {'Kategória': ['Állampapír/Készpénz', 'S&P 500 ETF', 'Osztalékos részvény'], 'Arány': [60, 30, 10]}
            fig = px.pie(data, values='Arány', names='Kategória', hole=0.3, color_discrete_sequence=['#2ecc71', '#27ae60', '#16a085'])
            st.plotly_chart(fig, use_container_width=True, key="p_cons")
            st.write("Alacsony kockázat, mérsékelt hozam.")

        with col2:
            st.subheader("⚖️ Kiegyensúlyozott")
            st.caption("Növekedés + Biztonság")
            data = {'Kategória': ['S&P 500 ETF', 'Egyedi részvények', 'Készpénz', 'Nasdaq 100'], 'Arány': [40, 30, 15, 15]}
            fig = px.pie(data, values='Arány', names='Kategória', hole=0.3, color_discrete_sequence=['#3498db', '#2980b9', '#34495e', '#5dade2'])
            st.plotly_chart(fig, use_container_width=True, key="p_bal")
            st.write("Hosszú távú vagyonépítésre.")

        with col3:
            st.subheader("🚀 Kockázatos")
            st.caption("Maximális hozamra várva")
            data = {'Kategória': ['Kripto', 'Növekedési részvények', 'Opciók/Egyéb'], 'Arány': [40, 50, 10]}
            fig = px.pie(data, values='Arány', names='Kategória', hole=0.3, color_discrete_sequence=['#e74c3c', '#c0392b', '#922b21'])
            st.plotly_chart(fig, use_container_width=True, key="p_aggr")
            st.write("Nagy hozam reménye, de nagy veszteség lehetősége.")

        st.info("💡 **Tipp:** A legtöbb szakértő szerint a kezdőknek érdemes a portfóliójuk legalább 70-80%-át alacsony költségű ETF-ekben (pl. S&P 500 vagy World ETF) tartani.")

else:
    # ==========================================
    # TŐZSDE FIGYELŐ OLDAL (DASHBOARD)
    # ==========================================
    # --- BAL OLDALI SÁV (Kereső és listák) ---
    st.sidebar.subheader("🔍 Keresés")
    search_query = st.sidebar.text_input("Írd be a nevet vagy kódot:", key="search_bar")
    if search_query:
        results = search_stock(search_query)
        for res in results:
            if st.sidebar.button(f"{res['symbol']} ({res['description']})", key=f"search_{res['symbol']}", use_container_width=True):
                st.session_state.selected_stock = res['symbol']
                st.rerun()

    st.sidebar.divider()

    if st.session_state.favorites:
        st.sidebar.subheader("⭐ Kedvencek")
        draw_stock_buttons(list(st.session_state.favorites), "fav")
        st.sidebar.divider()

    trending_list = get_stocks_from_screener("trending")
    popular_list = get_stocks_from_screener("most_active")

    st.sidebar.subheader("🔥 Trending")
    draw_stock_buttons(trending_list, "trend")

    st.sidebar.divider()
    st.sidebar.subheader("🌟 Népszerű")
    draw_stock_buttons(popular_list, "pop")

    # --- FŐOLDAL ---
    selected = st.session_state.selected_stock
    info = get_stock_details(selected)
    company_name = info.get('longName', selected)

    currency = info.get('currency', 'USD')

    # 1. Callback a kedvencekhez (marad a régi)
    def toggle_favorite():
        if st.session_state[f"check_{selected}"]:
            st.session_state.favorites.add(selected)
        else:
            st.session_state.favorites.discard(selected)
        if 'localS' in globals():
            localS.setItem("stored_favorites", list(st.session_state.favorites))

    # 2. ÚJ: SZŰKEBB OSZLOP ARÁNYOK [Részvény, Kedvenc, Hangulat]
    # Itt a 0.15 és 0.15 miatt szinte egymás mellett lesznek
    col_title, col_fav, col_sentiment = st.columns([0.2, 0.3, 0.5])

    with col_title:
        st.title(f"📊 {selected}")
        st.caption(company_name)

    with col_fav:
        # Egy kis trükk: lejjebb toljuk a checkboxot, hogy pont a cím közepénél legyen
        st.markdown('<div style="padding-top: 35px;"></div>', unsafe_allow_html=True)
        is_fav = selected in st.session_state.favorites
        st.checkbox(
            "⭐", # Kivettük a "Kedvenc" szöveget, mert a csillag magáért beszél és közelebb hozza a gombot
            value=is_fav, 
            key=f"check_{selected}", 
            on_change=toggle_favorite,
            help="Hozzáadás a kedvencekhez"
        )

    with col_sentiment:
        sentiment_val = get_market_sentiment()
        
        
        # Emoji és szöveg meghatározása (marad a régi logika)
        if sentiment_val < 30: emoji, label = "😨", "Extreme Fear"
        elif sentiment_val < 45: emoji, label = "😟", "Fear"
        elif sentiment_val < 55: emoji, label = "😐", "Neutral"
        elif sentiment_val < 70: emoji, label = "🙂", "Greed"
        else: emoji, label = "🤑", "Extreme Greed"

        # EGYETLEN HTML blokkban a szöveg és a csúszka
        st.markdown(f"""
            <div style="padding-top: 5px;">
                <div style="font-size: 14px; font-weight: bold; margin-bottom: 10px; color: #fafafa;">
                    Piaci Hangulat: <span style="color: #00ffcc;">{label}</span>
                </div>
                <div style="width: 100%; background-color: #333; border-radius: 10px; height: 8px; position: relative; margin-top: 15px;">
                    <div style="position: absolute; left: {sentiment_val}%; top: -14px; font-size: 20px; transform: translateX(-50%); transition: all 0.5s; z-index: 10;">
                        {emoji}
                    </div>
                    <div style="width: 100%; height: 100%; border-radius: 10px; background: linear-gradient(to right, #ff4b4b, #ffa421, #f0f2f6, #90ee90, #2ecc71);"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)


    st.divider()

    # --- IDŐTÁV ÉS GRAFIKON ---
    live_data = get_live_price(selected)
    current_price = live_data.get('c', 'N/A')
    st.subheader(f"Aktuális ár: {current_price} {currency}")

    # 1. Definiáljuk az opciókat
    period_options = {"5 Nap": "5d", "1 Hónap": "1mo", "1 Év": "1y", "5 Év": "5y", "Maximum": "max"}
    period_labels = list(period_options.keys())

    # 2. Inicializáljuk a mentett indexet a memóriában, ha még nem létezik (alapértelmezett: 1 év, azaz index 2)
    if 'current_period_idx' not in st.session_state:
        st.session_state.current_period_idx = 2

    # 3. Callback függvény: amikor kézzel átkattintasz, elmentjük az új indexet
    def on_period_change():
        new_label = st.session_state.period_selector_key
        st.session_state.current_period_idx = period_labels.index(new_label)

    # 4. A rádiógomb, ami a mentett indexet használja
    sel_label = st.radio(
        "Időtáv:", 
        period_labels, 
        horizontal=True, 
        index=st.session_state.current_period_idx,
        key="period_selector_key",
        on_change=on_period_change
    )

    # 5. Adatok lekérése a TÉNYLEGESEN kiválasztott gomb alapján
    hist_data = get_historical_data(selected, period_options[sel_label])
    
    if not hist_data.empty:
        # JAVÍTVA: A grafikon függőleges tengelye is a megfelelő devizát mutatja
        fig = px.line(hist_data, y='Close', labels={'Close': f'Árfolyam ({currency})', 'index': 'Dátum'})
        fig.update_layout(xaxis={'fixedrange': True}, yaxis={'fixedrange': True}, dragmode=False, hovermode="x unified")
        st.plotly_chart(
            fig, 
            use_container_width=True, 
            config={'scrollZoom': False, 'displayModeBar': False},
            key=f"chart_{selected}"
        )

    st.divider()

    col1, col2, col3 = st.columns(3)
    col1.metric("Market Cap", f"{info.get('marketCap', 0) / 1e9:.2f} Mrd {currency}")
    col2.metric("P/E Ráta", info.get('trailingPE', 'N/A'))
    col3.metric("52 Heti Max", f"{info.get('fiftyTwoWeekHigh', 'N/A')} {currency}")

    st.divider()

    # --- ÉRTESÍTÉSEK ---
    st.subheader("🔔 Értesítések beállítása")

    
    
    # Biztosítjuk, hogy az aktuális részvénynek legyen helye a szótárban
    if selected not in st.session_state.price_alerts:
        st.session_state.price_alerts[selected] = {"low": 0.0, "high": 0.0}

    is_subscribed = selected in st.session_state.subscribed_news



    with st.container(border=True):
        col_info, col_low, col_high = st.columns(3)
        
        # 1. OSZLOP: Hírek és E-mail
        # 1. OSZLOP: Hírek, Árfolyam-riasztások és E-mail
        with col_info:
            st.write("**Értesítések állapota**")
            
            # --- 1. HÍREK KAPCSOLÓ ---
            def toggle_news():
                if st.session_state[f"news_toggle_{selected}"]:
                    st.session_state.subscribed_news.add(selected)
                else:
                    st.session_state.subscribed_news.discard(selected)
                localS.setItem("stored_news_subs", list(st.session_state.subscribed_news))
            
            is_subscribed_news = selected in st.session_state.subscribed_news
            st.toggle(
                "Hírek kérése", 
                value=is_subscribed_news, 
                key=f"news_toggle_{selected}",
                on_change=toggle_news
            )

            # --- 2. ÁRFOLYAM RIASZTÁS KAPCSOLÓ ---
            def toggle_price_sub():
                if st.session_state[f"alert_sub_{selected}"]:
                    st.session_state.subscribed_alerts.add(selected)
                else:
                    st.session_state.subscribed_alerts.discard(selected)
                localS.setItem("stored_alert_subs", list(st.session_state.subscribed_alerts))

            is_subscribed_alerts = selected in st.session_state.subscribed_alerts
            st.toggle(
                "Árfolyam riasztások", 
                value=is_subscribed_alerts, 
                key=f"alert_sub_{selected}",
                on_change=toggle_price_sub,
                help="Kapcsold be, ha e-mailt kérsz a lenti limitek elérésekor."
            )
            
            st.write("---") # Halvány elválasztó vonal
            
            # E-mail mező
            email_input = st.text_input("E-mail a riasztásokhoz:", value=st.session_state.user_email, placeholder="pelda@email.hu")
            if email_input != st.session_state.user_email:
                if is_valid_email(email_input) or email_input == "":
                    st.session_state.user_email = email_input
                    localS.setItem("stored_email", email_input) 
                    if email_input: st.success("✅ Mentve!")
                else:
                    st.error("❌ Érvénytelen formátum!")

        # 2. OSZLOP: Alsó limit
        with col_low:
            st.write(f"**Alsó limit (Stop-Loss)**")
            
            def update_low_limit():
                st.session_state.price_alerts[selected]["low"] = st.session_state[f"low_{selected}"]
                localS.setItem("stored_alerts", st.session_state.price_alerts)

            saved_low = st.session_state.price_alerts[selected]["low"]
            
            # JAVÍTVA: A felirat dinamikusan mutatja a devizát
            low_price = st.number_input(
                f"Szólj, ha ez alá esik ({currency}):", 
                value=float(saved_low), 
                step=1.0, 
                key=f"low_{selected}",
                on_change=update_low_limit
            )
            
            # VIZUÁLIS CSÚSZKA
            if low_price > 0 and current_price != 'N/A':
                dist_low = ((current_price - low_price) / current_price) * 100
                dist_low = max(0, min(100, dist_low))
                color = "#ff4b4b" if dist_low < 5 else "#ffa421"
                
                st.markdown(f"""
                    <div style="font-size: 11px; margin-bottom: 5px; text-align: right;">Távolság: {dist_low:.1f}%</div>
                    <div style="width: 100%; background-color: #333; border-radius: 10px; height: 6px;">
                        <div style="width: {dist_low}%; height: 100%; border-radius: 10px; background-color: {color}; transition: width 0.5s;"></div>
                    </div>
                """, unsafe_allow_html=True)

        # 3. OSZLOP: Felső limit
        with col_high:
            st.write(f"**Felső limit (Célár)**")
            
            def update_high_limit():
                st.session_state.price_alerts[selected]["high"] = st.session_state[f"high_{selected}"]
                localS.setItem("stored_alerts", st.session_state.price_alerts)

            saved_high = st.session_state.price_alerts[selected]["high"]
            
            # JAVÍTVA: A felirat itt is dinamikus
            high_price = st.number_input(
                f"Szólj, ha e fölé megy ({currency}):", 
                value=float(saved_high), 
                step=1.0, 
                key=f"high_{selected}",
                on_change=update_high_limit
            )

            # VIZUÁLIS CSÚSZKA
            if high_price > 0 and current_price != 'N/A':
                progress_high = (current_price / high_price) * 100
                progress_high = max(0, min(100, progress_high))
                color = "#2ecc71" if progress_high > 95 else "#3498db"
                
                st.markdown(f"""
                    <div style="font-size: 11px; margin-bottom: 5px; text-align: right;">Célár elérése: {progress_high:.1f}%</div>
                    <div style="width: 100%; background-color: #333; border-radius: 10px; height: 6px;">
                        <div style="width: {progress_high}%; height: 100%; border-radius: 10px; background-color: {color}; transition: width 0.5s;"></div>
                    </div>
                """, unsafe_allow_html=True)

    # Vizuális visszajelzés (toast)
    if low_price > 0 and current_price != 'N/A' and current_price < low_price:
        st.toast(f"⚠️ {selected} beesett {low_price} USD alá!", icon="🛑")
    if high_price > 0 and current_price != 'N/A' and current_price > high_price:
        st.toast(f"🚀 {selected} elérte a {high_price} USD-t!", icon="💰")


        # --- RIASZTÁSI LOGIKA INDÍTÁSA ---
    # Ez a rész már a konténeren kívül van, de a változókat ismeri!
    
    today_str = datetime.date.today().isoformat()

    # Csak akkor fut le, ha van megadott email és be van kapcsolva a riasztás erre a részvényre
    if st.session_state.user_email and selected in st.session_state.subscribed_alerts:
        
        # ALSÓ LIMIT (Stop-Loss)
        alert_key_low = f"{selected}_low"
        if low_price > 0 and current_price != 'N/A' and current_price < low_price:
            if st.session_state.sent_alerts.get(alert_key_low) != today_str:
                subject = f"⚠️ STOP-LOSS: {selected} beesett!"
                body = f"Szia!\n\nA(z) {selected} árfolyama {current_price} USD, ami a {low_price} USD limited alatt van."
                if send_email_alert(st.session_state.user_email, subject, body):
                    st.session_state.sent_alerts[alert_key_low] = today_str
                    st.toast("📧 Riasztási e-mail elküldve!", icon="📩")

        # FELSŐ LIMIT (Célár)
        alert_key_high = f"{selected}_high"
        if high_price > 0 and current_price != 'N/A' and current_price > high_price:
            if st.session_state.sent_alerts.get(alert_key_high) != today_str:
                subject = f"🚀 CÉLÁR: {selected} elérve!"
                body = f"Szia!\n\nA(z) {selected} árfolyama {current_price} USD, elérte a {high_price} USD céláradat."
                if send_email_alert(st.session_state.user_email, subject, body):
                    st.session_state.sent_alerts[alert_key_high] = today_str
                    st.toast("📧 Célár értesítés elküldve!", icon="📩")
    
    # --- HÍR RIASZTÁS AI ELEMZÉSSEL ---
    if st.session_state.user_email and selected in st.session_state.subscribed_news:
        news_items = get_stock_news(selected)
        
        # Csak a legfrissebb 2 hírt nézzük meg, hogy ne küldjön egyszerre túl sokat
        for item in news_items[:2]:
            news_data = item.get('content', item)
            news_uuid = item.get('uuid') or news_data.get('url')
            
            # Ha ezt a hírt még nem küldtük el:
            if news_uuid not in st.session_state.seen_news:
                title = news_data.get('title', 'Új hír érkezett')
                link = news_data.get('url') or news_data.get('link', '#')
                summary_text = news_data.get('summary', '')

                # 1. AI Elemzés generálása (ha van API kulcs)
                ai_analysis = ""
                if user_api_key:
                    with st.spinner(f"AI elemzés készítése a hírről..."):
                        ai_analysis = analyze_news_with_groq(title, summary_text, selected, user_api_key)
                
                # 2. Email összeállítása
                subject = f"📰 ÚJ HÍR + AI ELEMZÉS: {selected}"
                
                # HTML formátum a szép megjelenéshez (vagy sima szöveg)
                body = f"""
                Szia! 

                Új hírt találtam a(z) {selected} részvényhez:
                Cím: {title}
                Link: {link}

                --- 🤖 AI GYORSELEMZÉS ---
                {ai_analysis if ai_analysis else "Az AI elemzés nem érhető el."}

                Üdv, a Tőzsde Figyelőd
                                """
                                
                # 3. Küldés
                if send_email_alert(st.session_state.user_email, subject, body):
                    # Elmentjük, hogy többször ne küldje el
                    st.session_state.seen_news.add(news_uuid)
                    localS.setItem("stored_seen_news", list(st.session_state.seen_news))
                    st.toast(f"📰 Új hír elküldve AI elemzéssel!", icon="📧")
    
    st.divider()

    # --- AI CHAT ASSZISZTENS ---
    st.subheader(f"💬 AI Pénzügyi Asszisztens ({selected})")
    
    # Külön chat memória minden részvényhez!
    chat_key = f"messages_{selected}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = [{"role": "assistant", "content": f"Szia! Én vagyok az AI asszisztensed. Miben segíthetek a(z) {selected} részvénnyel kapcsolatban?"}]

    chat_container = st.container(height=400, border=True)
    with chat_container:
        for message in st.session_state[chat_key]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input(f"Kérj véleményt a(z) {selected} részvényről..."):
        # 1. Felhasználó üzenetének mentése és kirajzolása
        st.session_state[chat_key].append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        # 2. AI Válasz generálása és kirajzolása
        with chat_container:
            with st.chat_message("assistant"):
                if not user_api_key:
                    st.error("❌ Kérlek, add meg a Groq API kulcsodat a bal oldali sávban a chateléshez!")
                else:
                    with st.spinner("Elemzés folyamatban..."):
                        try:
                            # Groq kliens inicializálása
                            client = OpenAI(api_key=user_api_key, base_url="https://api.groq.com/openai/v1")
                            
                            # Rendszer utasítás: Itt adjuk át titokban az aktuális árat az AI-nak!
                            system_prompt = {
                                "role": "system", 
                                "content": f"Te egy profi magyar pénzügyi asszisztens vagy. A felhasználó a(z) {selected} részvényt elemzi. A részvény jelenlegi ára: {current_price} USD. Válaszolj szakszerűen, objektíven. Ne adj konkrét befektetési tanácsot."
                            }
                            
                            # Összefűzzük a titkos utasítást az eddigi látható beszélgetéssel
                            api_messages = [system_prompt] + st.session_state[chat_key]
                            
                            # Hívjuk a modellt
                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=api_messages,
                                max_tokens=1024
                            )
                            
                            # Eredmény kinyerése
                            ai_response = response.choices[0].message.content
                            
                            # Kirajzolás és mentés a memóriába
                            st.markdown(ai_response)
                            st.session_state[chat_key].append({"role": "assistant", "content": ai_response})
                            
                        except Exception as e:
                            st.error(f"⚠️ Hálózati vagy API hiba: {str(e)}")

    st.caption("⚠️ **Jogi nyilatkozat / Disclaimer:** *Az AI asszisztens által adott válaszok kizárólag edukációs és tájékoztató jellegűek, nem minősülnek pénzügyi, befektetési vagy adóügyi tanácsadásnak.*")

    st.divider()

    # --- HÍREK SZEKCIÓ ---
    st.subheader(f"📰 Legfrissebb hírek ({selected})")
    
    # --- ÚJ: Lapozó memória (Session State) beállítása ---
    if 'news_limit' not in st.session_state:
        st.session_state.news_limit = 5
    if 'news_stock' not in st.session_state:
        st.session_state.news_stock = selected

    # Ha a felhasználó átkattint egy MÁSIK részvényre, a lapozót visszaállítjuk 5-re!
    if st.session_state.news_stock != selected:
        st.session_state.news_limit = 5
        st.session_state.news_stock = selected

    news_items = get_stock_news(selected)

    if news_items:
        # 1. Bekerült az 'enumerate', ami ad egy 'i' sorszámot minden hírnek (0, 1, 2, 3...)
        for i, item in enumerate(news_items[:st.session_state.news_limit]):
            data = item.get('content', item)
            
            title = data.get('title', 'Nincs elérhető cím')
            
            raw_link = data.get('url') or data.get('clickThroughUrl') or data.get('link')
            if isinstance(raw_link, dict):
                link = raw_link.get('url', '#')
            elif isinstance(raw_link, str):
                link = raw_link
            else:
                link = '#'
                
            # --- TÖBBI KÓD (képek, dátumok beállítása) MARAD UGYANAZ ---
            
            # 2. Létrehozunk egy garantáltan egyedi azonosítót a sorszám segítségével
            unique_id = f"{link}_{i}"
            
            img_url = ""
            thumbnail = data.get('thumbnail')
            if thumbnail and isinstance(thumbnail, dict):
                resolutions = thumbnail.get('resolutions')
                if resolutions and isinstance(resolutions, list) and len(resolutions) > 0:
                    img_url = resolutions[0].get('url', '')
            
            publisher = data.get('publisher')
            if not publisher and isinstance(data.get('provider'), dict):
                publisher = data.get('provider').get('displayName', 'Ismeretlen forrás')
            elif not publisher:
                publisher = 'Ismeretlen forrás'
            
            timestamp = data.get('providerPublishTime')
            pub_date_str = data.get('pubDate')
            
            if timestamp:
                try:
                    pub_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y. %m. %d. %H:%M')
                except Exception:
                    pub_date = "Ismeretlen időpont"
            elif isinstance(pub_date_str, str):
                pub_date = pub_date_str[:10].replace("-", ". ") + ". " + pub_date_str[11:16]
            else:
                pub_date = "Friss hír"
            
            with st.container(border=True):
                st.markdown(f"##### [{title}]({link})")
                col_img, col_meta, col_ai = st.columns([0.2, 0.35, 0.45]) 
                
                with col_img:
                    if img_url:
                        st.markdown(
                            f'<a href="{link}" target="_blank">'
                            f'<img src="{img_url}" width="100%" style="border-radius: 8px; object-fit: cover;">'
                            f'</a>', 
                            unsafe_allow_html=True
                        )
                    else:
                        st.write("*(Nincs kép)*")
                        
                with col_meta:
                    st.write("") 
                    st.caption(f"🏢 **{publisher}**")
                    st.caption(f"🕒 {pub_date}")
                    
                # A hír-megjelenítő ciklusban:
                with col_ai:
                    if unique_id in st.session_state.ai_analyses:
                        st.info(st.session_state.ai_analyses[unique_id])
                    else:
                        # CSAK AKKOR engedjük a gombot, ha van kulcs, különben csak egy figyelmeztetést kap
                        if not user_api_key:
                            st.caption("🔑 Adj meg kulcsot az elemzéshez")
                        else:
                            if st.button("🤖 AI Elemzés", key=f"btn_{unique_id}", use_container_width=True):
                                with st.spinner("Elemzés..."):
                                    summary_text = data.get('summary', '')
                                    analysis = analyze_news_with_groq(title, summary_text, selected, user_api_key)
                                    st.session_state.ai_analyses[unique_id] = analysis
                                    st.rerun()

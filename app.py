import streamlit as st
import requests
import time
import yfinance as yf
import plotly.express as px
import datetime
import pandas as pd
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


localS = LocalStorage()


# Page title
st.set_page_config(page_title="StockWatcher", page_icon="📈", layout="wide")



# Styles

st.markdown("""
    <style>
        /*On mobile there is no huge margin*/
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        /*On wider devices the margin is biggger*/
        @media (min-width: 800px) {
            .block-container {
                padding-left: 5rem !important;
                padding-right: 5rem !important;
                padding-top: 3rem !important;
            }
        }

        [data-testid="stAppViewBlockContainer"] {
            padding-top: 1rem !important;
        }

        /* Sidebar header */
        [data-testid="stSidebarHeader"] {
            padding-top: 0.5rem !important;
            min-height: 2rem !important; 
        }
        
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }
            
        .element-container:has(iframe[height="0"]),
        .element-container:has(iframe[width="0"]) {
            display: none !important;
            margin: 0 !important;
            padding: 0 !important;
            height: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)


# Session states

if 'language' not in st.session_state:
    st.session_state.language = 'hu'

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

# Datas from the browser's localstorage
saved_portfolio = localS.getItem("stored_portfolio")
saved_favorites = localS.getItem("stored_favorites")
saved_email = localS.getItem("stored_email")
saved_alerts = localS.getItem("stored_alerts")
saved_news_subs = localS.getItem("stored_news_subs")
saved_groq_key = localS.getItem("stored_groq_key")



# Load to memory

if 'subscribed_alerts' not in st.session_state:
    st.session_state.subscribed_alerts = set()

if saved_groq_key and 'groq_api_key' not in st.session_state:
    st.session_state.groq_api_key = saved_groq_key
    
if 'seen_news' not in st.session_state:
    saved_seen_news = localS.getItem("stored_seen_news")
    st.session_state.seen_news = set(saved_seen_news) if saved_seen_news else set()

if 'sent_alerts' not in st.session_state:
    st.session_state.sent_alerts = {}

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

if 'ai_analyses' not in st.session_state:
    st.session_state.ai_analyses = {}

if saved_news_subs is not None and 'loaded_news' not in st.session_state:
    st.session_state.subscribed_news = set(saved_news_subs)
    st.session_state.loaded_news = True

if saved_email and 'loaded_email' not in st.session_state:
    st.session_state.user_email = saved_email
    st.session_state.loaded_email = True

if saved_alerts is not None and 'loaded_alerts' not in st.session_state:
    st.session_state.price_alerts = saved_alerts
    st.session_state.loaded_alerts = True



# Methods
@st.cache_data(ttl=3600)
def search_stock(query):
    if not query: return []
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        results = data.get('quotes', [])
        
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
    
@st.cache_data(ttl=3600)
def get_exchange_rate(currency, target="USD"):
    if currency == target:
        return 1.0
        
    try:
        ticker_symbol = f"{currency}{target}=X"
        rate_data = yf.Ticker(ticker_symbol).history(period="1d")
        
        if not rate_data.empty:
            return float(rate_data['Close'].iloc[-1])
    except Exception:
        pass
        
    return 1.0

def send_email_alert(target_email, subject, body):
    if "EMAIL_USER" not in st.secrets or "EMAIL_PASSWORD" not in st.secrets:
        st.error("❌ Error while sending the email: Missing API secrets!")
        return False
        
    sender_email = st.secrets["EMAIL_USER"]
    sender_password = st.secrets["EMAIL_PASSWORD"]
    
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
        print(f"Error while sending the email: {e}")
        return False


def get_market_sentiment():
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
        return 50


def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None


@st.cache_data(ttl=86400)
def analyze_news_with_groq(title, summary, stock_symbol, api_key):
    if not api_key:
        return "❌ Please, insert you API key into the corresponding box!"
    
    context = f"Title: {title}\nSummary: {summary}" if summary else f"Title: {title}"
    
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional stock market analyst."},
                {"role": "user", "content": f"Analyze the news regarding {stock_symbol}.\n\n{context}\n\nPlease provide a short summary in english of the expected effects with emojis."}
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
        return ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "GOOGL", "BTC-USD", "ETH-USD", "AMD", "NFLX", "PLNTR", "SMCI", "INTC"]

@st.cache_data(ttl=60)
def get_live_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        
        hist = ticker.history(period="2d")
        
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            
            if len(hist) > 1:
                prev_price = hist['Close'].iloc[-2]
                change = current_price - prev_price
            else:
                change = 0
                
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
        info = ticker.info
        if not info or len(info) < 5: 
            raise Exception("Missing data")
        return info
    except Exception as e:
        return {
            'longName': symbol,
            'currency': 'USD',
            'sector': 'Unknown',
            'marketCap': 0,
            'trailingPE': 'N/A',
            'fiftyTwoWeekHigh': 'N/A'
        }


@st.cache_data(ttl=3600)
def get_cached_ticker_data(symbol):
    t = yf.Ticker(symbol)
    try:
        info = t.info
        hist = t.history(period="1d")
        if not info or len(info) < 5: raise ValueError("Limit")
        return info, hist
    except:
        try:
            hist = t.history(period="2d")
            last_p = hist['Close'].iloc[-1]
            prev_p = hist['Close'].iloc[-2]
            fallback_info = {
                'symbol': symbol, 'longName': symbol, 'currency': 'USD',
                'currentPrice': last_p, 'regularMarketPreviousClose': prev_p,
                'sector': 'Adat nem elérhető (Rate Limit)', 'dividendYield': 0
            }
            return fallback_info, hist
        except:
            return {'symbol': symbol, 'longName': symbol, 'currency': 'USD'}, pd.DataFrame()

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

@st.cache_data(ttl=300) 
def get_stock_news(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.news

def draw_stock_buttons(stock_list, key_prefix):
    fetched_data = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Elküldjük a kéréseket egyszerre a háttérben
        future_to_sym = {executor.submit(get_live_price, sym): sym for sym in stock_list}
        
        for future in concurrent.futures.as_completed(future_to_sym):
            sym = future_to_sym[future]
            fetched_data[sym] = future.result()

    for symbol in stock_list:
        data = fetched_data.get(symbol)
        
        if data == "RATE_LIMIT":
            st.sidebar.error(f"⚠️ {symbol} blocked (Too many requests!).")
            continue
        elif not data or not isinstance(data, dict) or not data.get('c'):
            continue
            
        price = data['c']
        change = data.get('d', 0)
        arrow = "🟩 ⬆" if change > 0 else "🟥 ⬇" if change < 0 else "⬜ ➖"
        
        if st.sidebar.button(f"{symbol} | {price} USD {arrow}", key=f"{key_prefix}_{symbol}", use_container_width=True):
            st.session_state.selected_stock = symbol
            st.rerun()




st.sidebar.header("📈 Stock Exchange Center")


st.sidebar.divider() 



def run_global_alerts():
    all_watched = st.session_state.subscribed_alerts.union(st.session_state.subscribed_news)
    today_str = datetime.date.today().isoformat()
    
    unsubscribe_footer = (
        "\n\n---\n"
        "If you would like to stop receiving such notifications, "
        "visit https://stockwatcher-nyb3fc4uhqcdapktbug5yl.streamlit.app."
    )
    global_api_key = st.session_state.get('groq_api_key', '')
    
    if not global_api_key:
        saved_key = localS.getItem("stored_groq_key")
        if saved_key:
            global_api_key = saved_key
            st.session_state.groq_api_key = saved_key

    for ticker_sym in all_watched:
        price_data = get_live_price(ticker_sym)
        if not price_data: continue
        
        curr_p = price_data['c']
        alert_limits = st.session_state.price_alerts.get(ticker_sym, {"low": 0.0, "high": 0.0})
        
        try:
            ticker_info = get_stock_details(ticker_sym)
            curr_symbol = ticker_info.get('currency', 'USD')
        except:
            curr_symbol = 'USD'

        if ticker_sym in st.session_state.subscribed_alerts and st.session_state.user_email:
            low_l = float(alert_limits["low"])
            high_l = float(alert_limits["high"])

            if low_l > 0 and curr_p < low_l:
                alert_key = f"{ticker_sym}_low"
                if st.session_state.sent_alerts.get(alert_key) != today_str:
                    subject = f"⚠️ STOP-LOSS: {ticker_sym} fell!"
                    body = (
                        f"Greetings!\n\n"
                        f"The price of {ticker_sym} is currently {curr_p} {curr_symbol}, "
                        f"which has fallen below the set limit {low_l} {curr_symbol}."
                        f"{unsubscribe_footer}"
                    )
                    if send_email_alert(st.session_state.user_email, subject, body):
                        st.session_state.sent_alerts[alert_key] = today_str
                        st.toast(f"📧 Stop-loss alert sent ({ticker_sym})!", icon="📩")

            if high_l > 0 and curr_p > high_l:
                alert_key = f"{ticker_sym}_high"
                if st.session_state.sent_alerts.get(alert_key) != today_str:
                    subject = f"🚀 TARGET PRICE: {ticker_sym} reached!"
                    body = (
                        f"Gretings!\n\n"
                        f"The price of {ticker_sym} has reached {curr_p} {curr_symbol}, "
                        f"thus the target flow of {high_l} {curr_symbol} has been met."
                        f"{unsubscribe_footer}"
                    )
                    if send_email_alert(st.session_state.user_email, subject, body):
                        st.session_state.sent_alerts[alert_key] = today_str
                        st.toast(f"📧 Target price alert sent ({ticker_sym})!", icon="📩")

        if ticker_sym in st.session_state.subscribed_news and st.session_state.user_email:
            news = get_stock_news(ticker_sym)
            if news:
                if 'news_initialized' not in st.session_state:
                    st.session_state.news_initialized = set()
                    
                is_first_check = ticker_sym not in st.session_state.news_initialized
                
                emails_sent_now = 0
                has_new_saved = False 
                
                for item in news[:5]:
                    if emails_sent_now >= 2 and not is_first_check:
                        break
                        
                    n_data = item.get('content', item)
                    
                    raw_link = n_data.get('url') or n_data.get('clickThroughUrl') or n_data.get('link')
                    if isinstance(raw_link, dict):
                        link = raw_link.get('url', '#')
                    elif isinstance(raw_link, str):
                        link = raw_link
                    else:
                        link = '#'
                        
                    title = n_data.get('title', 'New news')
                    n_uuid = n_data.get('uuid')
                    
                    if not n_uuid:
                        n_uuid = link if link != '#' else title
                    
                    if n_uuid and n_uuid not in st.session_state.seen_news:
                        
                        if is_first_check:
                            st.session_state.seen_news.add(n_uuid)
                            has_new_saved = True
                            
                        else:
                            summary = n_data.get('summary', '')

                            ai_analysis = ""
                            if global_api_key:
                                ai_result = analyze_news_with_groq(title, summary, ticker_sym, global_api_key)
                                if ai_result and "⚠️" not in ai_result and "❌" not in ai_result:
                                    ai_analysis = ai_result

                            subject = f"📰 News + AI analysis: {ticker_sym}"
                            body = f"Greetings!\n\n"
                            body += f"I found news for {ticker_sym} stock:\n"
                            body += f"Title: {title}\n"
                            body += f"Link: {link}\n\n"
                            
                            if ai_analysis:
                                body += f"--- 🤖 QUICK AI ANALYSIS ---\n{ai_analysis}\n"
                            else:
                                body += "*(There is currently no AI analysis for this news - check your API key!)*\n"
                            
                            body += unsubscribe_footer
                            
                            if send_email_alert(st.session_state.user_email, subject, body):
                                st.session_state.seen_news.add(n_uuid)
                                emails_sent_now += 1
                                has_new_saved = True
                                st.toast(f"📧 News sent with AI analysis ({ticker_sym})!", icon="📩")
                
                if is_first_check:
                    st.session_state.news_initialized.add(ticker_sym)
                
                if has_new_saved:
                    localS.setItem("stored_seen_news", list(st.session_state.seen_news), key=f"save_news_batch_{ticker_sym}")

run_global_alerts()







# Navigation

menu = st.sidebar.selectbox("Select item:", ["📈 StockWatcher", "💰 My Portfolio", "📚 Investment Smart", "ℹ️ About the program"])


#Auto refresh
st.sidebar.divider()
auto_refresh_enabled = st.sidebar.toggle(
    "Automatic update (1 minute)",
    value=False,
    help="If you turn it on, the page will automatically reload every minute. This is necessary so that the program can continuously monitor prices and news and send you an email if the limit is exceeded."
)

if auto_refresh_enabled:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60000, key="stock_watcher_refresh")

# REQUEST API KEY GLOBALLY
with st.sidebar.expander("🔑 AI Settings (Free)"):
        st.markdown("Request a free key in [Groq Console](https://console.groq.com/)!")
        
        saved_key = localS.getItem("stored_groq_key")
        if 'groq_api_key' not in st.session_state:
            st.session_state.groq_api_key = saved_key if saved_key else ""
            
        current_input = st.text_input(
            "Groq API Key:", 
            value=st.session_state.groq_api_key, 
            type="password", 
            help="Your browser will securely remember the key!"
        )
        
        if current_input != st.session_state.groq_api_key:
            st.session_state.groq_api_key = current_input
            localS.setItem("stored_groq_key", current_input)
            
        user_api_key = current_input

        if not user_api_key:
            st.warning("⚠️ Use a Groq key for AI analytics!")




#Portfolio page
if menu == "💰 My Portfolio":
    st.title("💰 My Portfolio")

    with st.expander("➕ Add new stock", expanded=True):
        
        st.write("Search for the company name or code, then enter your purchase details!")
        
        search_q = st.text_input(
            "🔍 Search (pl. Apple, Tesla, NVDA):", 
            key="port_search",
            help="Can't find the stock you're looking for? Make sure you've typed the ID correctly! If you're looking for a European stock, try adding '.DE' (German) or '.AS' (Dutch) to the end of the code. Check the exact code at finance.yahoo.com!"        
            )
                
        selected_ticker = None
        

        if search_q:
            results = search_stock(search_q)
            
            options = [f"{search_q.upper()} (Add directly)"]
            
            if results:
                options += [f"{r['symbol']} ({r['description']})" for r in results]
                
            chosen = st.selectbox("Select the exact stock:", options, key="port_select")
            
            selected_ticker = chosen.split(" ")[0]
        
        st.divider()
        
        # Purchase details
        st.write("### 💵 Purchase details")
        
        input_type = st.radio("How would you like to enter the price?", ["Total amount paid (Investment)", "Price of 1 share (Unit price)"], horizontal=True)

        col1, col2 = st.columns(2)
        new_qty = col2.number_input("Quantity purchased (pcs):", min_value=0.0001, step=0.01, format="%.4f")
        
        if input_type == "Total amount paid (Investment)":
            total_cost = col1.number_input("Total amount paid (USD):", min_value=0.0, step=1.0)
            actual_buy_price = (total_cost / new_qty) if new_qty > 0 else 0
            if total_cost > 0 and new_qty > 0:
                st.info(f"💡 **Unit price calculated by the system:** {actual_buy_price:.2f} USD / piece")
        else:
            actual_buy_price = col1.number_input("Price per piece when purchased (USD):", min_value=0.0, step=0.1)
            total_cost = actual_buy_price * new_qty
            if actual_buy_price > 0 and new_qty > 0:
                st.info(f"💡 **Total amount invested:** {total_cost:.2f} USD")

        if st.button("Add to portfolio", use_container_width=True):
            if selected_ticker and new_qty > 0 and actual_buy_price > 0:
                with st.spinner("Inspecting the market..."):
                    test_ticker = yf.Ticker(selected_ticker)
                    test_hist = test_ticker.history(period="1d")
                    if test_hist.empty:
                        st.error(f"❌ Invalid code: '{selected_ticker}'.")
                    else:
                        st.session_state.portfolio.append({
                            'symbol': selected_ticker, 
                            'buy_price': actual_buy_price,
                            'qty': new_qty
                        })
                        localS.setItem("stored_portfolio", st.session_state.portfolio)
                        st.success(f"✅ {selected_ticker} successfully added!")
                        time.sleep(1)
                        st.rerun()
            elif not selected_ticker:
                st.error("Please first search and choose a stock!")
            else:
                st.warning("Both quantity and price must be greater than 0!")

        # Stock buy/sell
    

    with st.expander("📦 Add other asset (Real estate, Wine, Jewelry etc.)"):
        st.write("Add alternative investments that are not tracked on the stock market.")
        custom_name = st.text_input("Name of the asset (e.g. Miami Apartment, Vintage Rolex):")
        custom_category = st.selectbox("Category:", ["Real Estate", "Wine", "Jewelry", "Art", "Vehicle", "Crypto (Offline)", "Other"])
        
        col_c1, col_c2 = st.columns(2)
        custom_qty = col_c1.number_input("Quantity:", min_value=0.0001, step=1.0, format="%.4f", key="custom_qty")
        custom_price = col_c2.number_input("Purchase Price (USD per unit):", min_value=0.0, step=100.0, key="custom_price")
        
        if st.button("Add alternative asset", use_container_width=True):
            if custom_name and custom_qty > 0 and custom_price > 0:
                st.session_state.portfolio.append({
                    'symbol': custom_name,
                    'buy_price': custom_price,
                    'qty': custom_qty,
                    'is_custom': True,  # <-- EZ A KULCS: Jelzi, hogy ez nem tőzsdei papír!
                    'custom_category': custom_category
                })
                localS.setItem("stored_portfolio", st.session_state.portfolio)
                st.success(f"✅ {custom_name} successfully added!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Please provide a name, and ensure quantity and price are greater than 0.")

    
    
    with st.expander("➖ Sale (Full or Partial)"):
        if not st.session_state.portfolio:
            st.write("You have no shares to sell.")
        else:
            stock_options = [f"{i}: {item['symbol']} ({item['qty']} pieces)" for i, item in enumerate(st.session_state.portfolio)]
            selected_to_sell = st.selectbox("Which stock are you looking to sell?", stock_options)
            
            idx = int(selected_to_sell.split(":")[0])
            current_item = st.session_state.portfolio[idx]
            
            col_s1, col_s2 = st.columns(2)
            sell_qty = col_s1.number_input(
                "Quantity to sell:", 
                min_value=0.01, 
                max_value=float(current_item['qty']), 
                step=1.0, 
                key="sell_asset_qty"  # <-- EZT ADD HOZZÁ
            )
            
            sell_price = col_s2.number_input(
                "Selling price (USD):", 
                min_value=0.0, 
                value=float(current_item['buy_price']), 
                key="sell_asset_price" # <-- EZT ADD HOZZÁ
            )

            if st.button("Complete purchase", use_container_width=True, type="primary"):
                profit = (sell_price - current_item['buy_price']) * sell_qty
                
                if sell_qty < current_item['qty']:
                    st.session_state.portfolio[idx]['qty'] -= sell_qty
                    st.toast(f"Sold {sell_qty} pieces of {current_item['symbol']}. Profit: {profit:.2f} USD", icon="💰")
                else:
                    st.session_state.portfolio.pop(idx)
                    localS.setItem("stored_portfolio", st.session_state.portfolio)
                    st.toast(f"The entire {current_item['symbol']} position has been closed. Profit: {profit:.2f} USD", icon="✅")
                
                time.sleep(1)
                st.rerun()

    if not st.session_state.portfolio:
        st.info("You don't have anything in your portfolio yet. Enter your first purchase above!")

    else:
        portfolio_data = []
        
        s_invested, s_current, s_div = 0, 0, 0
        
        total_invested, total_current = 0, 0

        allocation_data = []

        for item in st.session_state.portfolio:
            is_custom = item.get('is_custom', False)
            symbol = item['symbol']
            qty = item['qty']
            buy_p = item['buy_price']
            
            if is_custom:
                category = item.get('custom_category', 'Other')
                current_p = buy_p
                currency = "USD"
                sector = "Alternative Assets"
                exchange_rate = 1.0
                div_native = 0
            else:
                info, hist = get_cached_ticker_data(symbol)
                currency = info.get('currency', 'USD')
                current_p = hist['Close'].iloc[-1] if not hist.empty else buy_p
                sector = info.get('sector', 'Other')
                
                if "-USD" in symbol or "-EUR" in symbol:
                    category = "Crypto"
                elif "=X" in symbol:
                    category = "Currency"
                else:
                    category = "Stocks"
                
                div_yield = info.get('dividendYield', 0)
                if div_yield is None: div_yield = 0
                elif div_yield > 0.2: div_yield /= 100
                div_native = (current_p * qty) * div_yield
                
                exchange_rate = get_exchange_rate(currency, "USD")

            inv_usd = (buy_p * qty) * exchange_rate
            cur_usd = (current_p * qty) * exchange_rate
            div_usd = div_native * exchange_rate

            total_invested += inv_usd
            total_current += cur_usd

            if not is_custom and category == "Stocks":
                s_invested += inv_usd
                s_current += cur_usd
                s_div += div_usd

            portfolio_data.append({
                'Share': symbol,
                'Category': category,
                'Currency': currency,
                'Invested': buy_p * qty,
                'Current value': current_p * qty,
                'Profit/Loss': (current_p - buy_p) * qty,
                'Sector': sector,
                'Dividend (Annual)': div_native,
                'Current value (USD)': cur_usd, 
                'Invested (USD)': inv_usd
            })

        df_portfolio = pd.DataFrame(portfolio_data)

        st.subheader("📈 Stocks Only Performance")
        c1, c2, c3, c4 = st.columns(4)
        p_l_s = s_current - s_invested
        p_l_s_p = (p_l_s / s_invested * 100) if s_invested > 0 else 0
        c1.metric("Stock Investment", f"{s_invested:,.2f} $")
        c2.metric("Stock Value", f"{s_current:,.2f} $")
        c3.metric("Stock P/L", f"{p_l_s:,.2f} $", f"{p_l_s_p:.2f}%")
        c4.metric("Stock Dividend", f"{s_div:,.2f} $")

        st.subheader("🌍 Total Portfolio (All Assets)")
        t1, t2, t3, t4 = st.columns(4)
        p_l_t = total_current - total_invested
        p_l_t_p = (p_l_t / total_invested * 100) if total_invested > 0 else 0
        t1.metric("Total Investment", f"{total_invested:,.2f} $")
        t2.metric("Total Net Worth", f"{total_current:,.2f} $")
        t3.metric("Total P/L", f"{p_l_t:,.2f} $", f"{p_l_t_p:.2f}%")
        t4.metric("Assets Count", f"{len(df_portfolio)} items")

        st.divider()

        all_sectors = [
            "Information Technology", "Health Care", "Financials", "Consumer Discretionary", 
            "Communication Services", "Industrials", "Consumer Staples", "Energy", 
            "Utilities", "Real Estate", "Materials"
        ]

        sector_distribution = df_portfolio.groupby('Sector')['Current value (USD)'].sum() / total_current 

        for sector, weight in sector_distribution.items():
            if weight > 0.6:
                st.warning(f"⚠️ **The portfolio is not diversified enough!** Too much ({weight:.1%}) comes from the **{sector}** sector.")

        portfolio_sectors = df_portfolio['Sector'].unique()
        missing_sectors = [s for s in all_sectors if s not in portfolio_sectors]

        if len(missing_sectors) > 5:
                st.warning(f"⚠️ **Warning!** The portfolio is missing several key sectors (e.g. {', '.join(missing_sectors[:3])}).")


        col_pie1, col_pie2, col_pie3 = st.columns(3)
        
        with col_pie1:
            st.write("###🍰 Share Distribution")
            df_stocks = df_portfolio[df_portfolio['Category'].isin(['Stocks', 'Crypto', 'Currency'])]
            fig_stock = px.pie(df_stocks, values='Current value (USD)', names='Share', hole=0.4)
            fig_stock.update_layout(showlegend=False)
            fig_stock.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_stock, use_container_width=True)
            
        with col_pie2:
            st.write("###🏭 Sector Exposure")
            df_only_stocks = df_portfolio[df_portfolio['Category'] == 'Stocks']
            
            fig_sector = px.pie(df_only_stocks, values='Current value (USD)', names='Sector', hole=0.4)
            fig_sector.update_layout(showlegend=False)
            fig_sector.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_sector, use_container_width=True)

        with col_pie3:
            st.write("###⚖️ Asset Allocation")
            fig_alloc = px.pie(df_portfolio, values='Current value (USD)', names='Category', hole=0.4,
                               color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_alloc.update_layout(showlegend=False)
            fig_alloc.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_alloc, use_container_width=True)

        st.divider()

        

        st.write("### 📊 Portfolio Performance (Total and Per Share)")

        
        df_total = pd.DataFrame({
            'Share': ['All'],
            'Invested (USD)': [total_invested],
            'Current value (USD)': [total_current],
            'Sector': ['All']
        })

        df_plot = pd.concat([df_total, df_portfolio.sort_values('Current value (USD)', ascending=False)], ignore_index=True)

        df_melted = df_plot.melt(
            id_vars='Share', 
            value_vars=['Invested (USD)', 'Current value (USD)'], 
            var_name='Type', 
            value_name='Amount (USD)'
        )

        fig_bar = px.bar(
            df_melted, 
            x='Share', 
            y='Amount (USD)', 
            color='Type', 
            barmode='group',
            color_discrete_map={'Invested (USD)': '#6c757d', 'Current value (USD)': '#28a745'},
            text_auto='.2f' 
        )

        fig_bar.update_layout(
            yaxis_type="log",
            bargap=0.35,
            bargroupgap=0.1,
            xaxis={'fixedrange': True}, 
            yaxis={'fixedrange': True}, 
            dragmode=False,
            uniformtext_minsize=8, 
            uniformtext_mode='hide',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )


        st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})



        # Table
        with st.expander("📝 Detailed data table (In original currency)"):
            display_columns = ['Share', 'Currency', 'Invested', 'Current value', 'Profit/Loss', 'Sector']
            st.dataframe(df_portfolio[display_columns].style.format({
                'Invested': '{:.2f}', 
                'Current value': '{:.2f}', 
                'Profit/Loss': '{:.2f}'
            }), use_container_width=True)


        with st.expander("💰 Detailed Dividend Analysis"):
            st.write("The following amounts are estimated annual payments in their respective currencies:")
            

            df_div_display = df_portfolio[['Share', 'Currency', 'Dividend (Annual)', 'Sector']]
            
            st.dataframe(df_div_display.style.format({
                'Dividend (Annual)': '{:.2f}'
            }), use_container_width=True, hide_index=True)
            

            st.caption("Note: 'Accumulating' ETFs (like VUAA) show a value of 0.00 as they do not pay you directly.")

        if s_div > 0:
                st.write("### 🏆 Your largest dividend payers")
                fig_div = px.bar(
                    df_portfolio[df_portfolio['Dividend (Annual)'] > 0], 
                    x='Share', 
                    y='Dividend (Annual)',
                    color='Share',
                    text_auto='.2f',
                    title="Annual Dividend Per Share (In Original Currency)"
                )
                st.plotly_chart(fig_div, use_container_width=True, key="div_bar_chart")

        
        #Portfolio AI analysis
        st.divider()
        st.subheader("🤖 Portfolio Manager Assistant")
        st.info("Ask questions about your portfolio! For example: 'How risky is this composition?' or 'What other sectors do you recommend adding?'")

        port_chat_key = "messages_portfolio_main"
        if port_chat_key not in st.session_state:
            st.session_state[port_chat_key] = [{"role": "assistant", "content": "Hi! I'm your AI Portfolio Manager. I've reviewed your information above. How can I help you with your portfolio?"}]

        port_chat_container = st.container(height=400, border=True)
        with port_chat_container:
            for message in st.session_state[port_chat_key]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.text_input("Ask for feedback on your portfolio..."):
            st.session_state[port_chat_key].append({"role": "user", "content": prompt})
            
            with port_chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                    
            with port_chat_container:
                with st.chat_message("assistant"):
                    if not user_api_key:
                        st.error("❌ Please enter your Groq API key in the left sidebar to chat!")
                    else:
                        with st.spinner("Portfolio analysis in progress..."):
                            try:
                                portfolio_context = ""
                                for p_item in portfolio_data:
                                    portfolio_context += f"- {p_item['Share']}: {p_item['Current value (USD)']:.2f} USD value ({p_item['Sector']} sector)\n"
                                
                                system_prompt = {
                                    "role": "system", 
                                    "content": f"""You are a professional financial analyst and portfolio manager. 
                                    The user's current portfolio looks like this:
                                    Total value: {total_current:.2f} USD.
                                    Content:
                                    {portfolio_context}

                                    Please answer the user's questions about their portfolio. 
                                    Provide constructive criticism about diversification, sector concentration, and potential risks. 
                                    Be objective and point out if something is too risky. 
                                    Do not give direct investment advice, but you can suggest industries worth analyzing."""
                                }

                                client = OpenAI(api_key=user_api_key, base_url="https://api.groq.com/openai/v1")
                                
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
                                st.error(f"⚠️ Network or API error: {str(e)}")


        # EARNINGS CALENDAR
        st.divider()
        st.header("📅 Upcoming Quick Reports")
        st.write("The next quarterly reports of companies in your portfolio and favorites.")

        tracked_tickers = set([item['symbol'] for item in st.session_state.portfolio])
        if 'favorites' in st.session_state:
            tracked_tickers.update(st.session_state.favorites)

        earnings_data = []

        if tracked_tickers:
            with st.spinner('Updating calendar...'):
                for symbol in tracked_tickers:
                    try:
                        ticker = yf.Ticker(symbol)
                        calendar = ticker.calendar
                        
                        if calendar is not None and 'Earnings Date' in calendar:
                            next_report = calendar['Earnings Date'][0]
                            date_str = next_report.strftime('%Y-%m-%d')
                            
                            earnings_data.append({
                                "Share": symbol,
                                "Report Date": date_str,
                                "Type": "Portfolio" if any(item['symbol'] == symbol for item in st.session_state.portfolio) else "Favorite"
                            })
                    except:
                        continue

            if earnings_data:
                df_earnings = pd.DataFrame(earnings_data).sort_values(by="Report Date")
                
                st.dataframe(df_earnings, use_container_width=True, hide_index=True)
                
                st.info("💡**Why is this important?** On the day of the report, the exchange rate often moves significantly depending on expectations.")
            else:
                st.info("There is currently no report date available for the papers being tracked.")
        else:
            st.warning("There are no stocks in your portfolio or favorites yet.")
    

    st.divider()
    st.subheader("💾 Saving and loading data")
        
    col_exp, col_imp = st.columns(2)

    with col_exp:
            st.write("**Export**")
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
                label="📥 Download full backup (JSON)",
                data=json_string,
                file_name="stockwatcher_full_backup.json",
                mime="application/json",
                help="Saves portfolio, favorites, limits and all settings."
            )

    with col_imp:
        st.write("**Import**")
        uploaded_file = st.file_uploader("Restore backup", type=["json"])
        
        if uploaded_file is not None:
            try:
                import_data = json.load(uploaded_file)
                
                if st.button("🔄 Overwrite and load all data"):
                    st.session_state.portfolio = import_data.get("portfolio", [])
                    st.session_state.favorites = set(import_data.get("favorites", []))
                    st.session_state.price_alerts = import_data.get("price_alerts", {})
                    st.session_state.subscribed_news = set(import_data.get("subscribed_news", []))
                    st.session_state.subscribed_alerts = set(import_data.get("subscribed_alerts", []))
                    
                    st.session_state.loaded_port = True
                    st.session_state.loaded_fav = True
                    
                    storage_map = {
                        "stored_portfolio": st.session_state.portfolio,
                        "stored_favorites": list(st.session_state.favorites),
                        "stored_alerts": st.session_state.price_alerts,
                        "stored_news_subs": list(st.session_state.subscribed_news),
                        "stored_alert_subs": list(st.session_state.subscribed_alerts)
                    }
                    
                    for k, v in storage_map.items():
                        localS.setItem(k, v, key=f"save_{k}") 
                    
                    st.success("✅ Successful import and save! Updating...")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.warning(f"Yahoo error retrieving {symbol}: {e}")
                info = {'symbol': symbol, 'longName': symbol}
                hist = pd.DataFrame()
    
#About us page
elif menu == "ℹ️ About the program":
    
    st.title("ℹ️ About the program")
    st.write("Welcome to the Stock Market Watch app! This site was created to make managing your investments simpler, more transparent and smarter.")
    
    st.divider()

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 The purpose of the program")
        st.write("""
        This software is a modern stock tracker and portfolio manager application. Its main features:
        * **Real-time quotes:** Follow the current situation of global stocks.
        * **Portfolio management:** Manage your own investments and see your profits or losses instantly.
        * **Smart notifications:** Get instant alerts when the market moves.
        * **AI-based market analysis:** Use artificial intelligence to quickly evaluate news and your portfolio.
        """)

        st.subheader("🤖 Artificial Intelligence")
        st.write("""
        The program uses the lightning-fast **Groq AI** technology for analytics and chat assistant. 
        To use it, you need your own free API key, which you can request in just 2 minutes on the [Groq Console](https://console.groq.com/) website.
        """)

    with col2:
        st.subheader("🔒 Data Protection and Data Management")
        st.info("""
       **We do not store any data about you on our servers!**

        All your provided data (your portfolio, email address, API key and notification limits) is stored exclusively in **your own browser's memory** (LocalStorage).

        *💡 Important: If you open the site from another computer, another browser, or clear your browsing data, you will have to enter your settings again!*
        """)

        st.subheader("🔔 Notification system")
        st.write("""
        You can set individual rules for each stock. The program can notify you via email if:
        * New, market-moving news appears about the selected company.
        * The price reaches your **target price** (Upper limit).
        * The price falls below your **risk level** (Lower limit / Stop-Loss).
        """)

    st.divider()

    st.warning("""
    **⚠️ DISCLAIMER**

    The analyses, summaries and answers provided by the built-in Artificial Intelligence (AI) are **for informational and educational purposes only**. 

    The AI ​​**does not replace qualified financial professionals**, and the content it generates **does not constitute investment, financial or tax advice in any form**. Stock market investments involve risk, and you should always make decisions at your own risk and after thorough information!
    """)

    st.header("📖 User Guide")
    st.info("""
        ### 🤖 Activating AI Services
        For the full experience, request a free **Groq API key** on the [Groq Console](https://console.groq.com/) website, then paste it into the **AI Settings** field in the left sidebar. This will enable the portfolio analyzer and instant news analysis.

        ### 🔔 Notifications and Updates
        The application automatically checks **stock prices every minute**, and **news every 30 minutes**.
        
        > **⚠️ IMPORTANT WARNING:**
        > Since the application does not use a central server to store data, notifications **will only work** if:
        > 1. The page is **open** in your browser.
        > 2. Your computer is **turned on**.
        > 3. The **Auto-Refresh** feature is active.
        
        For the most reliable experience, it is recommended to leave the app open on a continuously running server or a dedicated, always-on computer.

        ### 🔒 Data Management and Backups
        All your data (e-mail, API key, portfolio) is stored securely in your browser's **LocalStorage**. This means that if you open the app on another computer or browser, the data will not be there. 
        **Tip:** Use the **Export** function at the bottom of the *My Portfolio* menu to create a backup or transfer your data to another device!
    """)

#Investment Smart
elif menu == "📚 Investment Smart":
        st.title("📚 Investment Smart")
        st.write("On this page, we have collected the most important concepts so that you can move more confidently on the stock market.")

        st.header("🔍 Basics")
        
        with st.expander("🏢 What is a stock?", expanded=True):
            st.write("""
            A stock is a piece of ownership in a company. When you buy a stock, you become an owner in the company.
            * **Advantage:** If the company does well, the price increases and you can receive dividends.
            * **Danger:** If the company goes bankrupt, the value of your investment can drop to zero.
            """)

        with st.expander("📦 What is an ETF?"):
            st.write("""
            **Exchange Traded Fund.** Imagine a basket of stocks from hundreds of companies.
            * **Advantage:** Diversification (you share the risk). You are not dependent on one company, but on an entire market (e.g. S&P 500).
            * **Danger:** In the event of a market downturn, the value of the entire basket decreases.
            """)

        with st.expander("📊 What is the P/E ratio?"):
            st.write("""
            **Price-to-Earnings.** Shows how many times the company's current price is divided by its annual earnings.
            * **Low (e.g. 10-15):** The stock may seem cheap (or the company is in trouble).
            * **High (e.g. 50+):** Investors expect high growth (or the stock is overpriced).
            """)

        with st.expander("What is Cryptocurrency?"):
            st.write("""
            Digital currencies (e.g. Bitcoin, Ethereum) that are not backed by a bank or state.
            * **Advantage:** Huge upside potential, 24/7 trading.
            * **Danger:** **Extreme volatility** (can fall 20-30% in a day), no guarantee.
            """)

        with st.expander("🐂 Bull Market vs. 🐻 Bear Market"):
            st.write("""
            These terms describe the general mood and trend of the stock market.
            * **Bull Market:** The market is in a continuous upward trend. Investors are optimistic, the economy is growing, and prices are rising.
            * **Bear Market:** The market falls by 20% or more from its recent peak. Investors are pessimistic, and prices are dropping.
            """)

        with st.expander("💸 What is a Dividend?"):
            st.write("""
            A dividend is a portion of a company's profit that is regularly paid out to its shareholders (usually quarterly).
            * **Advantage:** Generates predictable passive income. You get paid simply for holding the stock, regardless of daily price movements.
            * **Things to know:** Fast-growing tech companies rarely pay dividends because they reinvest their profits to grow faster. Mature, stable companies (like Coca-Cola) are the best dividend payers.
            """)

        with st.expander("⚖️ What is Market Capitalization (Market Cap)?"):
            st.write("""
            It shows the total total dollar market value of a company's outstanding shares *(Current Stock Price x Total Number of Shares)*.
            * **Large-cap (e.g. Apple, Microsoft):** Over $10 billion. Usually safer, stable companies with slower, steady growth.
            * **Small-cap:** Under $2 billion. Smaller, newer companies. They have higher growth potential but come with much higher risk and volatility.
            """)

        with st.expander("🛑 Stop-Loss & 🎯 Target Price"):
            st.write("""
            Essential risk management tools (which you can easily set up in the StockWatcher notification section!).
            * **Stop-Loss (Lower limit):** A pre-set risk level. If the stock falls to this price, you sell it (or get an alert) to prevent further massive losses.
            * **Target Price (Upper limit):** A pre-set goal where you are satisfied with the profit and plan to sell the stock before the market turns against you.
            """)

        st.divider()

        st.header("🥧 Sample portfolios")
        st.write("You can divide your money in different ways based on your risk tolerance.")

        col1, col2, col3 = st.columns(3)

        # Egy kis segédfüggvény a diagramok egységes formázásához
        def format_pie_chart(fig):
            fig.update_traces(textinfo='percent+label', textposition='inside')
            fig.update_layout(
                showlegend=False, # Kikapcsoljuk az oldalsó jelmagyarázatot, mert a cikkelyeken rajta lesz a név
                margin=dict(t=10, b=10, l=10, r=10), # Eltüntetjük a felesleges üres helyeket
                height=300 # Fix magasságot adunk nekik
            )
            return fig

        with col1:
            st.subheader("🛡️ Conservative")
            st.caption("Security-oriented")
            data = {'Category': ['Gov. Bonds/Cash', 'S&P 500 ETF', 'Dividend stock'], 'Ratio': [60, 30, 10]}
            fig1 = px.pie(data, values='Ratio', names='Category', hole=0.3, color_discrete_sequence=['#2ecc71', '#27ae60', '#16a085'])
            fig1 = format_pie_chart(fig1)
            st.plotly_chart(fig1, use_container_width=True, key="p_cons")
            st.write("Low risk, moderate return.")

        with col2:
            st.subheader("⚖️ Balanced")
            st.caption("Growth + Security")
            data = {'Category': ['S&P 500 ETF', 'Individual shares', 'Cash', 'Nasdaq 100'], 'Ratio': [40, 30, 15, 15]}
            fig2 = px.pie(data, values='Ratio', names='Category', hole=0.3, color_discrete_sequence=['#3498db', '#2980b9', '#34495e', '#5dade2'])
            fig2 = format_pie_chart(fig2)
            st.plotly_chart(fig2, use_container_width=True, key="p_bal")
            st.write("For long-term wealth building.")

        with col3:
            st.subheader("🚀 Risky")
            st.caption("Waiting for maximum yield")
            data = {'Category': ['Crypto', 'Growth stocks', 'Options/Other'], 'Ratio': [40, 50, 10]}
            fig3 = px.pie(data, values='Ratio', names='Category', hole=0.3, color_discrete_sequence=['#e74c3c', '#c0392b', '#922b21'])
            fig3 = format_pie_chart(fig3)
            st.plotly_chart(fig3, use_container_width=True, key="p_aggr")
            st.write("The hope of a big return, but the possibility of a big loss.")

        st.info("💡 **Tip:** Most experts recommend that beginners hold at least 70-80% of their portfolio in low-cost ETFs (e.g. S&P 500 or World ETF).")


        st.divider()

        # --- ÚJ RÉSZ: PIACI SZEKTOROK ---
        st.header("🏢 Market Sectors")
        st.write("The stock market is divided into 11 main sectors. Diversifying your investments across different sectors helps reduce risk. Here are the sectors with their top 3 market leaders:")

        sec_col1, sec_col2 = st.columns(2)

        with sec_col1:
            st.markdown("""
            * **💻 Information Technology:** Apple (AAPL), Microsoft (MSFT), Nvidia (NVDA)
            * **🏥 Health Care:** Eli Lilly (LLY), UnitedHealth (UNH), Johnson & Johnson (JNJ)
            * **🏦 Financials:** JPMorgan Chase (JPM), Visa (V), Mastercard (MA)
            * **🛍️ Consumer Discretionary:** Amazon (AMZN), Tesla (TSLA), Home Depot (HD)
            * **📱 Communication Services:** Alphabet (GOOGL), Meta (META), Netflix (NFLX)
            * **🏭 Industrials:** Caterpillar (CAT), Union Pacific (UNP), General Electric (GE)
            """)

        with sec_col2:
            st.markdown("""
            * **🛒 Consumer Staples:** Walmart (WMT), Procter & Gamble (PG), Coca-Cola (KO)
            * **🛢️ Energy:** ExxonMobil (XOM), Chevron (CVX), ConocoPhillips (COP)
            * **⚡ Utilities:** NextEra Energy (NEE), Southern Company (SO), Duke Energy (DUK)
            * **🏢 Real Estate:** Prologis (PLD), American Tower (AMT), Equinix (EQIX)
            * **🧱 Materials:** Linde (LIN), Sherwin-Williams (SHW), Freeport-McMoRan (FCX)
            """)

        st.divider()


else:
    st.sidebar.subheader("🔍 Search")
    search_query = st.sidebar.text_input("Enter the name or code:", key="search_bar")
    if search_query:
        results = search_stock(search_query)
        for res in results:
            if st.sidebar.button(f"{res['symbol']} ({res['description']})", key=f"search_{res['symbol']}", use_container_width=True):
                st.session_state.selected_stock = res['symbol']
                st.rerun()

    st.sidebar.divider()

    if st.session_state.favorites:
        st.sidebar.subheader("⭐ Favorites")
        draw_stock_buttons(list(st.session_state.favorites), "fav")
        st.sidebar.divider()

    trending_list = get_stocks_from_screener("trending")
    popular_list = get_stocks_from_screener("most_active")

    st.sidebar.subheader("🔥 Trending")
    draw_stock_buttons(trending_list, "trend")

    st.sidebar.divider()
    st.sidebar.subheader("🌟 Popular")
    draw_stock_buttons(popular_list, "pop")

    selected = st.session_state.selected_stock
    info = get_stock_details(selected)
    company_name = info.get('longName', selected)

    currency = info.get('currency', 'USD')

    def toggle_favorite():
        if st.session_state[f"check_{selected}"]:
            st.session_state.favorites.add(selected)
        else:
            st.session_state.favorites.discard(selected)
        if 'localS' in globals():
            localS.setItem("stored_favorites", list(st.session_state.favorites))


    col_title, col_fav, col_sentiment = st.columns([0.2, 0.3, 0.5])

    with col_title:
        st.title(f"📊 {selected}")
        st.caption(company_name)

    with col_fav:
        st.markdown('<div style="padding-top: 35px;"></div>', unsafe_allow_html=True)
        is_fav = selected in st.session_state.favorites
        st.checkbox(
            "⭐", 
            value=is_fav, 
            key=f"check_{selected}", 
            on_change=toggle_favorite,
        )

    with col_sentiment:
        sentiment_val = get_market_sentiment()
        
        
        if sentiment_val < 30: emoji, label = "😨", "Extreme Fear"
        elif sentiment_val < 45: emoji, label = "😟", "Fear"
        elif sentiment_val < 55: emoji, label = "😐", "Neutral"
        elif sentiment_val < 70: emoji, label = "🙂", "Greed"
        else: emoji, label = "🤑", "Extreme Greed"

        st.markdown(f"""
            <div style="padding-top: 5px;">
                <div style="font-size: 14px; font-weight: bold; margin-bottom: 10px; color: #fafafa;">
                    Market Mood: <span style="color: #00ffcc;">{label}</span>
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

    live_data = get_live_price(selected)
    current_price = live_data.get('c', 'N/A')
    st.subheader(f"Current price: {current_price} {currency}")

    period_options = {"5 days": "5d", "1 month": "1mo", "1 year": "1y", "5 years": "5y", "Max": "max"}
    period_labels = list(period_options.keys())

    if 'current_period_idx' not in st.session_state:
        st.session_state.current_period_idx = 2

    def on_period_change():
        new_label = st.session_state.period_selector_key
        st.session_state.current_period_idx = period_labels.index(new_label)

    sel_label = st.radio(
        "Time period:", 
        period_labels, 
        horizontal=True, 
        index=st.session_state.current_period_idx,
        key="period_selector_key",
        on_change=on_period_change
    )

    hist_data = get_historical_data(selected, period_options[sel_label])
    
    if not hist_data.empty:
        fig = px.line(hist_data, y='Close', labels={'Close': f'Price ({currency})', 'index': 'Date'})
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
    col2.metric("P/E Ratio", info.get('trailingPE', 'N/A'))
    col3.metric("52 Weekly Max", f"{info.get('fiftyTwoWeekHigh', 'N/A')} {currency}")

    st.divider()



    st.subheader("🔔 Notification settings")

    
    
    if selected not in st.session_state.price_alerts:
        st.session_state.price_alerts[selected] = {"low": 0.0, "high": 0.0}

    is_subscribed = selected in st.session_state.subscribed_news


    with st.container(border=True):
        col_info, col_low, col_high = st.columns(3)
        
        with col_info:
            st.write("**Notifications Status**")
            
            def toggle_news():
                if st.session_state[f"news_toggle_{selected}"]:
                    st.session_state.subscribed_news.add(selected)
                else:
                    st.session_state.subscribed_news.discard(selected)
                localS.setItem("stored_news_subs", list(st.session_state.subscribed_news), key=f"save_news_subs_{selected}")
            
            is_subscribed_news = selected in st.session_state.subscribed_news
            st.toggle(
                "Request news", 
                value=is_subscribed_news, 
                key=f"news_toggle_{selected}",
                on_change=toggle_news
            )

            def toggle_price_sub():
                if st.session_state[f"alert_sub_{selected}"]:
                    st.session_state.subscribed_alerts.add(selected)
                else:
                    st.session_state.subscribed_alerts.discard(selected)
                localS.setItem("stored_alert_subs", list(st.session_state.subscribed_alerts), key=f"save_alert_subs_{selected}")

            is_subscribed_alerts = selected in st.session_state.subscribed_alerts
            st.toggle(
                "Price alerts", 
                value=is_subscribed_alerts, 
                key=f"alert_sub_{selected}",
                on_change=toggle_price_sub,
                help="Turn it on if you want to receive an email when the limits below are reached."
            )
            
            st.write("---")
            
            email_input = st.text_input("Email for alerts:", value=st.session_state.user_email, placeholder="sample@email.com")
            if email_input != st.session_state.user_email:
                if is_valid_email(email_input) or email_input == "":
                    st.session_state.user_email = email_input
                    
                    localS.setItem("stored_email", email_input, key=f"save_email_{selected}") 
                    # ----------------------------------------
                    
                    if email_input: st.success("✅ Saved!")
                else:
                    st.error("❌ Invalid format!")

        # 2. OSZLOP: Alsó limit
        with col_low:
            st.write(f"**Lower limit (Stop-Loss)**")
            
            def update_low_limit():
                st.session_state.price_alerts[selected]["low"] = st.session_state[f"low_{selected}"]
                localS.setItem("stored_alerts", st.session_state.price_alerts)

            saved_low = st.session_state.price_alerts[selected]["low"]
            
            low_price = st.number_input(
                f"Alert if falls under ({currency}):", 
                value=float(saved_low), 
                step=1.0, 
                key=f"low_{selected}",
                on_change=update_low_limit
            )
            
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

        with col_high:
            st.write(f"**Upper limit (Target price)**")
            
            def update_high_limit():
                st.session_state.price_alerts[selected]["high"] = st.session_state[f"high_{selected}"]
                localS.setItem("stored_alerts", st.session_state.price_alerts)

            saved_high = st.session_state.price_alerts[selected]["high"]
            
            high_price = st.number_input(
                f"Alert if goes above ({currency}):", 
                value=float(saved_high), 
                step=1.0, 
                key=f"high_{selected}",
                on_change=update_high_limit
            )

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

    if low_price > 0 and current_price != 'N/A' and current_price < low_price:
        st.toast(f"⚠️ {selected} fell under {low_price} USD!", icon="🛑")
    if high_price > 0 and current_price != 'N/A' and current_price > high_price:
        st.toast(f"🚀 {selected} reached {high_price} USD!", icon="💰")


    today_str = datetime.date.today().isoformat()
    
    unsubscribe_footer = (
        "\n\n---\n"
        "If you would like to stop receiving such notifications, "
        "visit https://stockwatcher-nyb3fc4uhqcdapktbug5yl.streamlit.app."
    )

    global_api_key = st.session_state.get('groq_api_key', '')

    if st.session_state.user_email and selected in st.session_state.subscribed_alerts:
        
        alert_key_low = f"{selected}_low"
        if low_price > 0 and current_price != 'N/A' and current_price < low_price:
            if st.session_state.sent_alerts.get(alert_key_low) != today_str:
                subject = f"⚠️ STOP-LOSS {selected} fell!"
                body = (
                    f"Greetings!!\n\n"
                    f"The current exchange rate for {selected} is {current_price} {currency}", 
                    f"which fell below the set {low_price} {currency} limit."
                    f"{unsubscribe_footer}"
                )
                if send_email_alert(st.session_state.user_email, subject, body):
                    st.session_state.sent_alerts[alert_key_low] = today_str
                    st.toast(f"📧 Stop-loss alert sent!", icon="📩")

        alert_key_high = f"{selected}_high"
        if high_price > 0 and current_price != 'N/A' and current_price > high_price:
            if st.session_state.sent_alerts.get(alert_key_high) != today_str:
                subject = f"🚀 Target price: {selected} reached!"
                body = (
                    f"Greetings!\n\n"
                    f"The price of {selected} has reached {current_price} {currency}, "
                    f"your {high_price} {currency} target price was met."
                    f"{unsubscribe_footer}"
                )
                if send_email_alert(st.session_state.user_email, subject, body):
                    st.session_state.sent_alerts[alert_key_high] = today_str
                    st.toast(f"📧 Target price alert sent!", icon="📩")

    
    st.divider()








    st.subheader(f"💬 AI Financial Assistant ({selected})")
    
    chat_key = f"messages_{selected}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = [{"role": "assistant", "content": f"Hi! I'm your AI assistant. How can I help you with {selected} stock?"}]

    chat_container = st.container(height=400, border=True)
    with chat_container:
        for message in st.session_state[chat_key]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.text_input(f"Ask for an opinion on {selected} stock..."):
        st.session_state[chat_key].append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        with chat_container:
            with st.chat_message("assistant"):
                if not user_api_key:
                    st.error("❌ Please enter your Groq API key in the left sidebar to chat!")
                else:
                    with st.spinner("Analysis in progress..."):
                        try:
                            client = OpenAI(api_key=user_api_key, base_url="https://api.groq.com/openai/v1")
                            
                            system_prompt = {
                                "role": "system", 
                                "content": f"You are a professional financial assistant. The user is analyzing the {selected} stock. The current price of the stock is {current_price} USD. Please respond professionally and objectively. Do not give specific investment advice."}
                            
                            api_messages = [system_prompt] + st.session_state[chat_key]
                            
                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=api_messages,
                                max_tokens=1024
                            )
                            
                            ai_response = response.choices[0].message.content
                            
                            st.markdown(ai_response)
                            st.session_state[chat_key].append({"role": "assistant", "content": ai_response})
                            
                        except Exception as e:
                            st.error(f"⚠️ Network or API error: {str(e)}")

    st.caption("⚠️ **Legal statement / Disclaimer:** *The answers provided by the AI ​​assistant are for educational and informational purposes only and do not constitute financial, investment or tax advice.*")
    st.divider()

    # NEWS
    st.subheader(f"📰 Recent news ({selected})")
    
    if 'news_limit' not in st.session_state:
        st.session_state.news_limit = 5
    if 'news_stock' not in st.session_state:
        st.session_state.news_stock = selected

    if st.session_state.news_stock != selected:
        st.session_state.news_limit = 5
        st.session_state.news_stock = selected

    news_items = get_stock_news(selected)

    if news_items:
        for i, item in enumerate(news_items[:st.session_state.news_limit]):
            data = item.get('content', item)
            
            title = data.get('title', 'No title available')
            
            raw_link = data.get('url') or data.get('clickThroughUrl') or data.get('link')
            if isinstance(raw_link, dict):
                link = raw_link.get('url', '#')
            elif isinstance(raw_link, str):
                link = raw_link
            else:
                link = '#'
                
            
            unique_id = f"{link}_{i}"
            
            img_url = ""
            thumbnail = data.get('thumbnail')
            if thumbnail and isinstance(thumbnail, dict):
                resolutions = thumbnail.get('resolutions')
                if resolutions and isinstance(resolutions, list) and len(resolutions) > 0:
                    img_url = resolutions[0].get('url', '')
            
            publisher = data.get('publisher')
            if not publisher and isinstance(data.get('provider'), dict):
                publisher = data.get('provider').get('displayName', 'Unknown source')
            elif not publisher:
                publisher = 'Unknown source'
            
            timestamp = data.get('providerPublishTime')
            pub_date_str = data.get('pubDate')
            
            if timestamp:
                try:
                    pub_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y. %m. %d. %H:%M')
                except Exception:
                    pub_date = "Unknown date"
            elif isinstance(pub_date_str, str):
                pub_date = pub_date_str[:10].replace("-", ". ") + ". " + pub_date_str[11:16]
            else:
                pub_date = "Recent news"
            
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
                        st.write("*(No image available)*")
                        
                with col_meta:
                    st.write("") 
                    st.caption(f"🏢 **{publisher}**")
                    st.caption(f"🕒 {pub_date}")
                    
                with col_ai:
                    if unique_id in st.session_state.ai_analyses:
                        st.info(st.session_state.ai_analyses[unique_id])
                    else:
                        if not user_api_key:
                            st.caption("🔑 Enter a key for analysis")
                        else:
                            if st.button("🤖 AI Analysis", key=f"btn_{unique_id}", use_container_width=True):
                                with st.spinner("Analyzing..."):
                                    summary_text = data.get('summary', '')
                                    analysis = analyze_news_with_groq(title, summary_text, selected, user_api_key)
                                    st.session_state.ai_analyses[unique_id] = analysis
                                    st.rerun()

# 📈 StockWatcher

A modern, AI-powered stock tracking and portfolio management dashboard built with Python and Streamlit. Track real-time market data, manage your investments, set up smart email alerts, and leverage Artificial Intelligence (Groq API) for instant news and portfolio analysis.

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)

## 🌐 Live Demo
**Try it instantly in your browser (No installation required):** 👉 [Click here to open StockWatcher!](https://stockwatcher-nyb3fc4uhqcdapktbug5yl.streamlit.app)
---

## ✨ Key Features

* 📊 **Real-Time Dashboard:** Search and track global stocks, view historical data with interactive Plotly charts, and monitor market sentiment.
* 💰 **Advanced Portfolio Management:** Log your purchases/sales, track profit/loss, estimate annual dividends, and visualize your sector diversification with pie and bar charts.
* 🤖 **AI Assistant & News Analysis:** Powered by the blazing-fast Groq API (LLaMA 3). Chat with an AI Portfolio Manager to evaluate your holdings, and get instant, emoji-rich summaries of market-moving news.
* 🔔 **Smart Email Alerts:** Set custom Stop-Loss and Target Price limits. The app sends automatic email notifications when prices cross your limits or when new AI-analyzed news is published.
* 📅 **Earnings Calendar:** Automatically tracks and displays upcoming quarterly report dates for your portfolio and favorite stocks.
* 🔒 **Privacy-First (No Database):** 100% serverless data handling. All personal data, API keys, and portfolio entries are stored securely in your browser's `LocalStorage`. Includes full JSON export/import functionality for backups.

## 🛠️ Technology Stack

* **Frontend/Backend:** [Streamlit](https://streamlit.io/)
* **Financial Data:** `yfinance`
* **Data Visualization:** `plotly.express`, `pandas`
* **Artificial Intelligence:** `openai` (configured for Groq API)
* **Storage:** `streamlit-local-storage`
* **Notifications:** Built-in Python `smtplib`

---
## 🚀 Installation & Setup (For Local Run)
*If you want to run the application locally on your own machine for better privacy and to avoid Yahoo Finance rate limits:*

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/StockWatcher.git
cd StockWatcher
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up email notifications (Optional)
Email alerts require a Gmail account with an App Password. Without this, the app works fine but won't send email notifications.

**Step 1:** Enable 2-Step Verification on your Google account at [myaccount.google.com/security](https://myaccount.google.com/security)

**Step 2:** Generate an App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
- Select "Mail" as the app
- Copy the generated 16-character password

**Step 3:** Create the secrets file:
```bash
mkdir .streamlit
```
Create a file called `.streamlit/secrets.toml` with the following content:
```toml
EMAIL_USER = "your_gmail_address@gmail.com"
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"
```
> ⚠️ **Never commit this file to GitHub!** It is already listed in `.gitignore` for your protection.

### 4. Run the application
```bash
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`.

---

> 💡 **No secrets file?** The app will still work fully — only email notifications will be disabled. You can add the secrets file at any time to enable them.

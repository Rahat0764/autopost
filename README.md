<div align="center">

# 🤖 AutoPost Bot
**Fully Automated AI-Powered Facebook Page Manager**

[![Python](https://img.shields.io/badge/Python-v3.14.3-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Web_Framework-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![Gemini](https://img.shields.io/badge/AI-Google_Gemini-orange?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg?style=for-the-badge)](https://github.com/Rahat0764/autopost/graphs/commit-activity)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

An intelligent, autonomous bot that researches, writes, generates dynamic images, and publishes posts to your Facebook Page, completely controllable via Telegram.

[🔑 Token Generator](https://token-generator-five-tan.vercel.app) · [🐞 Report Bug](https://github.com/Rahat0764/autopost/issues) · [👔 LinkedIn](https://www.linkedin.com/in/RahatAhmedX)

</div>

---

## ✨ Key Features

* **🧠 Advanced AI Writing:** Utilizes Google Gemini (Flash & Lite) for human-like, engaging Bengali/English content.
* **🎨 Dynamic Image Synthesis:** Automatically creates customized, aesthetic images with `Pillow` matching the post's theme.
* **🔍 Real-Time Web Research:** Integrates Serper API to fetch live data, ensuring 100% factual accuracy.
* **📱 Telegram Command Center:** Full control from your phone (Force post, change languages, pause/resume, check stats).
* **☁️ Zero-Downtime Deployment:** Optimized for Render/Heroku with Flask + Gunicorn background threading.
* **🛡️ Smart Quality Checker:** Built-in AI hallucination and repetition checker before publishing.

## 🛠️ Tech Stack

* **Language:** Python 3.14.3
* **Libraries:** `Flask`, `Gunicorn`, `Requests`, `Pillow`
* **APIs:** Facebook Graph API, Telegram Bot API, Google Gemini, Serper Search
* **Database:** SQLite3 (Local caching, logs & history)

---

## 🚀 Getting Started

Follow these instructions to set up the bot locally or deploy it to the cloud.

### 1️⃣ Facebook Developer Setup (Crucial)
To post automatically, you need a Meta App and a Never-Expiring Page Token.
1. Go to [Meta for Developers](https://developers.facebook.com/) and click **Create App** (Select *Other* -> *Business*).
2. Note down your **App ID** and **App Secret** from `App Settings > Basic`.
3. Go to the [Graph API Explorer](https://developers.facebook.com/tools/explorer/).
4. Select your App, and generate a **User Token** with these permissions: 
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `pages_show_list`
5. **Generate Final Token:** Go to our custom [Token Generator Tool](https://token-generator-five-tan.vercel.app), paste your App details and User Token to instantly forge your **Never-Expiring Page Token**.

### 2️⃣ Telegram Bot Setup
1. Message [@BotFather](https://t.me/botfather) on Telegram and send `/newbot`.
2. Copy the **Bot Token**.
3. Message [@userinfobot](https://t.me/userinfobot) to get your personal **Telegram User ID**.

### 3️⃣ Local Installation

Clone the repository and install dependencies:
```bash
git clone [https://github.com/Rahat0764/autopost.git](https://github.com/Rahat0764/autopost.git)
cd autopost
pip install -r requirements.txt
```

Set your environment variables (or export them in the terminal):
```env
APP_ID=your_app_id
APP_SECRET=your_app_secret
PAGE_ID=your_page_id
PAGE_ACCESS_TOKEN=your_never_expiring_page_token
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_USER_IDS=your_telegram_user_id
GEMINI_API_KEY=your_gemini_api_key
SERPER_API_KEY=your_serper_api_key
LANGUAGE=bn
```

Run the bot:
```bash
python run.py
```

### 4️⃣ Cloud Deployment (Render.com)
Deploy the bot so it runs 24/7 for free:
1. Sign up on [Render.com](https://render.com) and create a **New Web Service**.
2. Connect your GitHub repository.
3. **Environment:** `Python 3`
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `gunicorn run:app`
6. **Environment Variables:** Add all variables from Step 3. **Crucially, add `PORT` with value `8080`.**
7. Click **Deploy**.

> **Pro Tip:** To prevent Render's free tier from sleeping, copy your Render URL and paste it into [UptimeRobot](https://uptimerobot.com) with a 5-minute ping interval.

---

## 🤖 Telegram Commands Reference

Control your bot easily from anywhere using these commands:

| Command | Description |
| :--- | :--- |
| `/status` | View live bot status, total posts, tokens used, and active model. |
| `/post` | Force generate and publish a post immediately. |
| `/post <topic>`| Publish a post on a specific custom topic. |
| `/lang bn` | Switch bot language to Bengali. |
| `/lang en` | Switch bot language to English. |
| `/model` | Open inline keyboard to change Gemini AI model. |
| `/pause` | Pause the automated schedule. |
| `/resume` | Resume the automated schedule. |
| `/logs` | View recent system errors and warnings. |
| `/topics` | View the queue of upcoming topics. |

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/Rahat0764/autopost/issues).

---

## 👨‍💻 Author

**Rahat Ahmed**
* LinkedIn: [@RahatAhmedX](https://www.linkedin.com/in/RahatAhmedX)
* GitHub: [@Rahat0764](https://github.com/Rahat0764)

<div align="center">
  <i>If you find this project useful, don't forget to leave a ⭐!</i>
</div>
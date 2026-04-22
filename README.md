<h1 align="center">🚀 AutoPost Bot</h1>

<p align="center">
  <b>An advanced, fully automated AI-powered Facebook Page posting bot.</b><br>
  <i>Generates content, creates dynamic images, researches facts, and publishes seamlessly with zero downtime.</i>
</p>

<p align="center">
  <a href="https://token-generator-five-tan.vercel.app"><b>🔑 Token Generator Tool</b></a> •
  <a href="https://github.com/Rahat0764/autopost/"><b>📂 Repository</b></a> •
  <a href="https://www.linkedin.com/in/RahatAhmedX"><b>💼 LinkedIn</b></a>
</p>

---

## ✨ Features

- **🤖 AI Content Generation:** Powered by Google Gemini (2.5 & 3.0 Flash/Lite) for high-quality, engaging posts.
- **🎨 Automated Image Synthesis:** Dynamically generates beautiful, customized images using `Pillow` based on the post's topic and theme.
- **🌐 Real-Time Web Research:** Integrates with the Serper API to fetch up-to-date facts and deep-scan websites for accurate context.
- **📱 Complete Telegram Control:** Fully controllable via a Telegram Bot. Check status, force posts, pause/resume, and view error logs directly from your phone.
- **☁️ Cloud & Production Ready:** Built with Flask and Gunicorn for 24/7 deployment on Render, Heroku, or any VPS.
- **🔐 Built-in Security:** Comes with a custom [One-Click Token Generator](https://token-generator-five-tan.vercel.app) to securely forge Never-Expiring Facebook Page Tokens.

---

## 🛠️ Architecture & Tech Stack

- **Language:** Python 3.10+
- **APIs Used:** Facebook Graph API, Telegram Bot API, Google Gemini API, Serper Web Search API.
- **Libraries:** `Flask`, `Gunicorn`, `Requests`, `Pillow`.
- **Database:** SQLite3 (Local caching, log tracking, and post history).

---

## 🚀 Step-by-Step Installation & Deployment

### Step 1: Facebook Developer Setup
To post automatically, you need a Meta App and a Page Access Token.

1. Go to [Meta for Developers](https://developers.facebook.com/) and create an account.
2. Click **Create App** ➔ Select **Other** ➔ Select **Business**.
3. Name your app and create it.
4. From the App Dashboard, go to **App Settings > Basic** and note down your `App ID` and `App Secret`.
5. Open the [Graph API Explorer](https://developers.facebook.com/tools/explorer/).
6. Select your App, and generate a **User Token** with the following permissions:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `pages_show_list`
7. **Crucial:** Go to the [AutoPost Token Generator Tool](https://token-generator-five-tan.vercel.app). Input your App ID, App Secret, Page ID, and the Short-Lived User Token you just got. Click "Generate" to receive your **Never-Expiring Page Token**.

### Step 2: Telegram Bot Setup
1. Go to Telegram and search for [@BotFather](https://t.me/botfather).
2. Send `/newbot` and follow the instructions to get your `TELEGRAM_BOT_TOKEN`.
3. Search for [@userinfobot](https://t.me/userinfobot) to get your personal `TELEGRAM_USER_IDS`.

### Step 3: Local Testing (Termux/PC)
1. Clone the repository:
   ```bash
   git clone https://github.com/Rahat0764/autopost.git
   cd autopost
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your environment variables (or export them in terminal):
   ```env
   APP_ID=your_app_id
   APP_SECRET=your_app_secret
   PAGE_ID=your_page_id
   PAGE_ACCESS_TOKEN=your_long_lived_page_token
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_USER_IDS=your_telegram_user_id
   GEMINI_API_KEY=your_gemini_api_key
   SERPER_API_KEY=your_serper_api_key
   LANGUAGE=bn
   ```
4. Run the bot:
   ```bash
   python run.py
   ```

### Step 4: Cloud Deployment (Render)
To keep the bot running 24/7 for free without keeping your device on:

1. Create an account on [Render.com](https://render.com).
2. Click **New** ➔ **Web Service** and connect this GitHub repository.
3. **Environment:** Select `Python 3`.
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `gunicorn run:app`  *(If `run.py` is in the root folder)*
6. **Environment Variables:** Add all the variables mentioned in Step 3. 
   - ⚠️ **Mandatory:** Add a new variable `PORT` with the value `8080`.
7. Click **Deploy**. Once it says "Live", your bot is officially running in the cloud!
8. *(Optional)* To prevent Render's free tier from sleeping, copy your Render URL and paste it into [UptimeRobot](https://uptimerobot.com) with a 5-minute ping interval.

---

## 📱 Telegram Commands Reference

Once the bot is running, send these commands to your Telegram bot:

- `/status` - View current bot status, total posts, and active schedule.
- `/post` - Force the bot to generate and publish a post immediately.
- `/post <topic>` - Force publish a specific topic (e.g., `/post Artificial Intelligence`).
- `/pause` / `/resume` - Temporarily halt or resume scheduled posting.
- `/lang bn` or `/lang en` - Switch the bot's language between Bengali and English.
- `/model` - Select the Gemini AI model (Flash / Lite) manually or set to Auto.
- `/logs` - View recent error logs directly in Telegram.
- `/help` - View the complete list of commands.

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/Rahat0764/autopost/issues).

---

## 👨‍💻 Author

**Rahat Ahmed**
- 💼 LinkedIn: [RahatAhmedX](https://www.linkedin.com/in/RahatAhmedX)
- 🐙 GitHub: [@Rahat0764](https://github.com/Rahat0764)

> *If you find this project helpful, please consider giving it a ⭐ on GitHub!*
# Admin Assistant Bot 🤖

A powerful Telegram assistant bot that forwards user messages to the admin, allows admin to reply, and provides tools for managing users (ban/unban, broadcast, statistics).  
Built with **Python, Pyrogram, Flask, and MongoDB**. Deployable on **Render** or any VPS.

---

## 🚀 Features
- 📩 **Message Forwarding** – User messages are automatically forwarded to the admin.
- 🔁 **Admin Reply System** – Admin can reply to forwarded messages, and replies are sent back to the original user.
- 📊 **Statistics Tracking** – Tracks total users, total messages, and banned users.
- 🚫 **Ban/Unban System** – Ban abusive users directly from forwarded messages or using commands.
- 📢 **Broadcast System** – Send messages, photos, videos, documents, or stickers to all users.
- ⏳ **Auto-Reply** – Sends an automatic reply to users while waiting for admin response.
- 🔨 **Inline Ban Button** – Admin receives forwarded messages with a ban button for quick action.
- 🌐 **Flask Health Check** – A `/` endpoint for uptime monitoring and Render deployment compatibility.
- ☁️ **Webhook Support** – Works with both polling (local) and webhook (Render/Heroku) modes.

---

## 📜 Commands

| Command        | Description |
|----------------|-------------|
| `/start`       | Register and welcome new users |
| `/stats`       | Show bot statistics (admin only) |
| `/ban <user_id>` | Ban a user by their Telegram ID (admin only) |
| `/unban <user_id>` | Unban a user (admin only) |
| `/broadcast`   | Broadcast a replied message to all users (admin only) |

> ⚠️ **Note:** `/ban`, `/unban`, `/stats`, and `/broadcast` are **admin-only commands**.

---

## ⚙️ Environment Variables

You need to set the following environment variables for the bot to work:

| Variable              | Description |
|-----------------------|-------------|
| `BOT_TOKEN`           | Telegram bot token from [BotFather](https://t.me/BotFather) |
| `ADMIN_ID`            | Your Telegram user ID (admin) |
| `MONGODB_URI`         | MongoDB connection string |
| `PORT`                | Port for Flask (default: `5000`) |
| `RENDER`              | Set to `true` when deploying on Render |
| `RENDER_EXTERNAL_URL` | Render app external URL (e.g., `https://your-app.onrender.com`) |

---

## 🛠️ Deployment

### Local (Polling)
1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set environment variables in `.env` or shell.
3. Run the bot:
   ```bash
   python main.py
   ```

### Render (Webhook)
1. Push your project to GitHub.
2. Create a new **Web Service** on Render.
3. Add environment variables in the **Render Dashboard**.
4. Deploy – The bot will run automatically with webhook mode.

---

## 🧾 License
This project is for personal use. Modify and use as per your needs.

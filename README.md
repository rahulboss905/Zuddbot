# Telegram Channel Verification Bot

This bot verifies if users are members of a Telegram channel before granting access to group links.

## Features
- Channel membership verification
- Group link distribution
- User statistics tracking
- Admin-only statistics command

## Setup

1. **Create a Telegram Bot**:
   - Use @BotFather to create a new bot and get your `TELEGRAM_BOT_TOKEN`

2. **Set up MongoDB**:
   - Create a free cluster at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
   - Get your connection string (`MONGODB_URI`)

3. **Configure Environment Variables**:
   - Copy `.env.example` to `.env`
   - Fill in all required values:
     - `TELEGRAM_BOT_TOKEN`: Your bot's API token
     - `TELEGRAM_CHANNEL_ID`: Your channel ID (@username or numeric ID)
     - `TELEGRAM_INVITE_LINK`: Your channel invite link
     - `TELEGRAM_GROUP_LINK`: Your group invite link
     - `MONGODB_URI`: MongoDB connection string
     - `ADMIN_USER_ID`: Your Telegram user ID (get from @userinfobot)

## Local Development

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
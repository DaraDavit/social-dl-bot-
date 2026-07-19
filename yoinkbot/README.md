# YoinkBot

Telegram bot — yoinks videos without watermarks from TikTok, YouTube, and Pinterest.

## Features

- **TikTok** — no-watermark MP4
- **YouTube** — MP4 (Video) or MP3 (Audio) via inline buttons
- **Pinterest** — video or image
- Files over 50MB handled gracefully (Telegram upload limit)

## Setup

```bash
git clone https://github.com/yourusername/yoinkbot.git
cd yoinkbot
python3 -m ensurepip
pip install -r requirements.txt
```

Create a `.env` file:

```
BOT_TOKEN=your_bot_token_here
```

Get a token from [@BotFather](https://t.me/BotFather).

### YouTube cookies (required for YouTube downloads)

YouTube requires signed-in cookies to bypass bot detection.

1. Install the **"Get cookies.txt LOCALLY"** browser extension
2. Log into YouTube in that browser
3. Export cookies → save as `youtube-cookies.txt` in the project root

## Run

```bash
python bot.py
```

## Keep alive (VPS)

Using `screen`:

```bash
screen -S yoinkbot
python bot.py
# Ctrl+A, D to detach
```

Or a systemd service:

```ini
[Unit]
Description=YoinkBot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/yoinkbot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Requirements

- Python 3.10+
- ffmpeg
- `yt-dlp`, `python-telegram-bot`, `python-dotenv`

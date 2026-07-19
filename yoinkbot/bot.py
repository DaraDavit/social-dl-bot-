import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in .env")

from downloader.core import download, detect_platform, cleanup

YOUTUBE_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Video", callback_data="yt:mp4"),
        InlineKeyboardButton("MP3", callback_data="yt:mp3"),
    ]
])


def extract_url(text: str) -> str | None:
    import re
    pat = r"https?://[^\s]+"
    m = re.search(pat, text)
    return m.group(0) if m else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("yoink. send a link.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    url = extract_url(text)
    if not url:
        await update.message.reply_text("no link. can't yoink nothing.")
        return

    platform = detect_platform(url)

    if platform == "youtube":
        context.user_data["pending_url"] = url
        await update.message.reply_text("youtube. video or mp3?", reply_markup=YOUTUBE_KEYBOARD)
        return

    await _download_and_send(update, context, url, "mp4")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("yt:"):
        fmt = data.split(":")[1]
        url = context.user_data.pop("pending_url", None)
        if not url:
            await query.edit_message_text("link expired. send again.")
            return
        await query.edit_message_text("yoink...")
        await _download_and_send_callback(query, context, url, fmt)
    else:
        await query.edit_message_text("nah.")


async def _download_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, fmt: str) -> None:
    status_msg = await update.message.reply_text("yoink...")

    result, error = await asyncio.to_thread(download, url, fmt)

    if error == "auth":
        await status_msg.edit_text("youtube wants me to prove i'm not a bot.\nsend a cookies.txt file. tuff.")
        return
    if not result:
        await status_msg.edit_text(f"can't yoink that.")
        return

    await status_msg.edit_text("yoink. sending...")

    try:
        file_size_mb = result.filesize / (1024 * 1024)
        ext = result.ext
        is_tiktok = detect_platform(url) == "tiktok"
        caption = None if is_tiktok else f"{result.title[:200]}"

        if caption and ext in ("mp3", "m4a", "ogg", "wav"):
            caption = f"🎵 {caption}"

        if caption and file_size_mb > 49:
            caption += f"\n\n{file_size_mb:.0f}MB"

        with open(result.path, "rb") as f:
            if ext in ("mp3", "m4a", "ogg", "wav"):
                await update.message.reply_audio(
                    audio=f,
                    title=result.title[:64] if not is_tiktok else None,
                    caption=caption,
                    read_timeout=120,
                    write_timeout=120,
                )
            elif ext in ("jpg", "jpeg", "png", "gif", "webp"):
                await update.message.reply_photo(
                    photo=f,
                    caption=caption,
                    read_timeout=120,
                    write_timeout=120,
                )
            else:
                await update.message.reply_video(
                    video=f,
                    caption=caption,
                    read_timeout=120,
                    write_timeout=120,
                    supports_streaming=True,
                )

        await status_msg.delete()
        cleanup(result.path)

    except Exception as e:
        err = str(e)
        if "too big" in err.lower() or "entity too large" in err.lower():
            await status_msg.edit_text(
                f"file too big ({file_size_mb:.0f}MB).\ntelegram caps at 50MB.\ntuff."
            )
        else:
            await status_msg.edit_text(f"failed. tuff.")
        cleanup(result.path)


async def _download_and_send_callback(query, context: ContextTypes.DEFAULT_TYPE, url: str, fmt: str) -> None:
    result, error = await asyncio.to_thread(download, url, fmt)

    if error == "auth":
        await query.edit_message_text("youtube wants me to prove i'm not a bot.\nsend a cookies.txt file. tuff.")
        return
    if not result:
        await query.edit_message_text(f"can't yoink that.")
        return

    try:
        file_size_mb = result.filesize / (1024 * 1024)
        ext = result.ext
        is_tiktok = detect_platform(url) == "tiktok"
        caption = None if is_tiktok else result.title[:200]

        if caption and ext in ("mp3", "m4a", "ogg", "wav"):
            caption = f"🎵 {caption}"
        if caption and file_size_mb > 49:
            caption += f"\n\n{file_size_mb:.0f}MB"

        with open(result.path, "rb") as f:
            if ext in ("mp3", "m4a", "ogg", "wav"):
                await query.message.reply_audio(
                    audio=f,
                    title=result.title[:64] if not is_tiktok else None,
                    caption=caption,
                    read_timeout=120,
                    write_timeout=120,
                )
            elif ext in ("jpg", "jpeg", "png", "gif", "webp"):
                await query.message.reply_photo(
                    photo=f,
                    caption=caption,
                    read_timeout=120,
                    write_timeout=120,
                )
            else:
                await query.message.reply_video(
                    video=f,
                    caption=caption,
                    read_timeout=120,
                    write_timeout=120,
                    supports_streaming=True,
                )

        await query.edit_message_text("yoinked.")
        cleanup(result.path)

    except Exception as e:
        err = str(e)
        if "too big" in err.lower() or "entity too large" in err.lower():
            await query.edit_message_text(
                f"file too big ({file_size_mb:.0f}MB). telegram caps at 50MB. tuff."
            )
        else:
            await query.edit_message_text(f"failed. tuff.")
        cleanup(result.path)


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("yoinkbot running...")
    app.run_polling()


if __name__ == "__main__":
    main()

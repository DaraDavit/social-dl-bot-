import os
import re
import tempfile
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Callable

import yt_dlp
from yt_dlp.utils import DownloadError

DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

COOKIES_FILE = Path(__file__).parent.parent / "youtube-cookies.txt"

TELEGRAM_MAX_SIZE = 50 * 1024 * 1024  # 50MB


@dataclass
class DownloadResult:
    path: str
    title: str
    duration: int
    filesize: int
    ext: str


def _sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def detect_platform(url: str) -> str:
    u = url.lower()
    if "tiktok.com" in u:
        return "tiktok"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "pinterest.com" in u or "pin.it" in u:
        return "pinterest"
    return "unknown"


def download(
    url: str,
    format_choice: str = "mp4",
    progress_callback: Callable[[dict], None] | None = None,
    progress_state: dict | None = None,
) -> tuple[DownloadResult | None, str | None]:
    platform = detect_platform(url)
    uid = str(int(time.time() * 1000))
    output_tmpl = str(DOWNLOADS_DIR / f"yoink_{uid}_%(title).80s.%(ext)s")

    def _hook(d):
        if progress_state is not None and d["status"] == "downloading":
            progress_state["percent"] = float(d.get("_percent_str", "0").replace("%", "").strip() or 0)
            progress_state["speed"] = d.get("_speed_str", "")
            progress_state["eta"] = d.get("_eta_str", "")
            progress_state["downloaded"] = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            if total:
                progress_state["total"] = total
        if progress_callback:
            progress_callback(d)

    hooks = [_hook]

    ydl_opts: dict = {
        "outtmpl": output_tmpl,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "progress_hooks": hooks,
        "socket_timeout": 30,
    }

    if platform == "tiktok":
        ydl_opts["format"] = "bestvideo+bestaudio/best"
    elif platform == "youtube":
        if COOKIES_FILE.exists():
            ydl_opts["cookiefile"] = str(COOKIES_FILE)
        if format_choice == "mp3":
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        else:
            ydl_opts["format"] = (
                "best[height<=720][filesize<50M]"
                "/best[height<=480][filesize<50M]"
                "/best[filesize<50M]"
                "/worst"
            )
    elif platform == "pinterest":
        ydl_opts["format"] = "best"
    else:
        ydl_opts["format"] = "best"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except DownloadError as e:
        msg = str(e).lower()
        if "sign in" in msg or "cookies" in msg or "bot" in msg:
            return None, "auth"
        return None, None
    except Exception:
        return None, None

    downloaded = None
    session_id = f"yoink_{uid}"
    for f in sorted(DOWNLOADS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.is_file() and f.name.startswith(session_id):
            downloaded = f
            break

    if not downloaded:
        for f in sorted(DOWNLOADS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file() and f"s_{info.get('id', '')}" not in f.name:
                continue
            downloaded = f
            break

    if not downloaded:
        return None, None

    if format_choice == "mp3" and platform == "youtube" and downloaded.suffix != ".mp3":
        for alt in downloaded.parent.glob(downloaded.stem + ".*"):
            if alt.suffix == ".mp3":
                downloaded = alt
                break

    return DownloadResult(
        path=str(downloaded),
        title=info.get("title", "video"),
        duration=info.get("duration", 0) or 0,
        filesize=downloaded.stat().st_size,
        ext=downloaded.suffix.lstrip("."),
    ), None


def cleanup(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass

"""
Telegram PC Controller - All in One
By Nothing-dot-exe (https://github.com/Nothing-dot-exe)

Contains both the GUI Manager and the Telegram Bot backend in a single file.
Configuration is stored in config.json (managed via GUI).

Setup:
1. pip install -r requirements.txt
2. python TelegramController.py
3. Enter Bot Token and Chat ID in the GUI, then click Start.
"""

import os
import sys
import io
import socket
import asyncio
import subprocess
import threading
import platform
import logging
import winreg
from datetime import datetime

import psutil
import pyautogui
import requests
import tkinter as tk
from tkinter import font as tkfont

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ╔══════════════════════════════════════════════════════════════╗
# ║                    CONFIGURATION                             ║
# ╚══════════════════════════════════════════════════════════════╝

import json
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {"BOT_TOKEN": "", "AUTHORIZED_USER_ID": ""}

def save_config(token, user_id):
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "_README": "Telegram PC Controller Configuration",
            "_BOT_TOKEN_help": "Get this from @BotFather on Telegram (/newbot)",
            "BOT_TOKEN": token,
            "_AUTHORIZED_USER_ID_help": "Your Telegram User ID (get it from @RawDataBot or /myid command)",
            "AUTHORIZED_USER_ID": user_id,
            "_author": "Nothing-dot-exe (https://github.com/Nothing-dot-exe)"
        }, f, indent=4)

cfg = load_config()
BOT_TOKEN = cfg.get("BOT_TOKEN", "").strip()
AUTHORIZED_USER_ID = cfg.get("AUTHORIZED_USER_ID", "")
try: AUTHORIZED_USER_ID = int(AUTHORIZED_USER_ID)
except: AUTHORIZED_USER_ID = 0

# ══════════════════════════════════════════════════════════════
THIS_SCRIPT = os.path.abspath(__file__)
APP_NAME = "TelegramPCController"
# Force python.exe instead of pythonw.exe for subprocess stability
PYTHON_EXE = sys.executable.replace("pythonw.exe", "python.exe")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

pending_actions = {}


# =====================================================================
#                        BOT BACKEND LOGIC
# =====================================================================

def authorized(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != AUTHORIZED_USER_ID:
            await update.message.reply_text("⛔ Unauthorized. Access denied.")
            logger.warning(f"Unauthorized access attempt by {user_id}")
            return
        return await func(update, context)
    return wrapper

async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👤 *Your Telegram Info*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *User ID:* `{user.id}`\n"
        f"📛 *Name:* {user.first_name}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Copy the User ID above and set it as\n"
        f"`AUTHORIZED_USER_ID` in the bot script.",
        parse_mode="Markdown",
    )

@authorized
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🖥️ *Telegram PC Controller*
━━━━━━━━━━━━━━━━━━━━━━

🔧 *System Control*
/screenshot — Capture screen
/webcam — Capture webcam photo
/lock — Lock the PC
/shutdown — Shutdown (30s cancel)
/restart — Restart (30s cancel)
/sleep — Put PC to sleep
/logoff — Log off current user
/cancel — Cancel shutdown/restart

📊 *Monitoring*
/status — CPU, RAM, Disk, Battery
/processes — Top processes by CPU
/ip — Local & public IP
/drives — List all drives
/uptime — System uptime
/wifi — Current WiFi info

📁 *Apps & Files*
/tasklist — Running apps
/kill `<name>` — Kill a process
/open `<path>` — Open file/app
/cmd `<command>` — Run shell command
/download `<url>` — Download file to PC
/sendfile `<path>` — Send file to Telegram
/browse `<url>` — Open URL in browser

🔊 *Media & Display*
/volume `<0-100>` — Set volume
/mute — Toggle mute
/brightness `<0-100>` — Set brightness
/media `<play/pause/next/prev>` — Media keys
/say `<text>` — Text-to-speech on PC

💬 *Utilities*
/alert `<msg>` — Popup on PC
/clipboard — Get clipboard
/setclip `<text>` — Set clipboard
/note `<text>` — Save note to Desktop
/myid — Show your Telegram ID

💻 *Author*
Made by Nothing-dot-exe
GitHub: [Nothing-dot-exe](https://github.com/Nothing-dot-exe)

━━━━━━━━━━━━━━━━━━━━━━
🟢 Bot is online and ready!
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

@authorized
async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Capturing screen...")
    try:
        screenshot = pyautogui.screenshot()
        buf = io.BytesIO()
        screenshot.save(buf, format="PNG")
        buf.seek(0)
        await update.message.reply_photo(photo=buf, caption=f"🖥️ Screenshot — {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        await update.message.reply_text(f"❌ Screenshot failed: {e}")

@authorized
async def cmd_webcam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📷 Capturing webcam...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            await update.message.reply_text("❌ No webcam found.")
            return
        ret, frame = cap.read()
        cap.release()
        if not ret:
            await update.message.reply_text("❌ Failed to capture webcam.")
            return
        _, buf_arr = cv2.imencode(".jpg", frame)
        buf = io.BytesIO(buf_arr.tobytes())
        buf.seek(0)
        await update.message.reply_photo(photo=buf, caption=f"📷 Webcam — {datetime.now().strftime('%H:%M:%S')}")
    except ImportError:
        await update.message.reply_text("❌ opencv-python not installed.\nRun: `pip install opencv-python`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Webcam error: {e}")

@authorized
async def cmd_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔒 Locking PC...")
    try:
        subprocess.Popen("rundll32.exe user32.dll,LockWorkStation")
        await update.message.reply_text("✅ PC locked.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to lock: {e}")

@authorized
async def cmd_shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("❌ Cancel Shutdown", callback_data="cancel_shutdown")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = await update.message.reply_text(
        "⚠️ *PC will shutdown in 30 seconds!*\nPress the button below to cancel.",
        parse_mode="Markdown", reply_markup=reply_markup
    )
    job = context.application.job_queue.run_once(execute_shutdown, 30, data=msg.message_id, name="shutdown_job")
    pending_actions["shutdown"] = job

async def execute_shutdown(context: ContextTypes.DEFAULT_TYPE):
    pending_actions.pop("shutdown", None)
    subprocess.Popen("shutdown /s /t 0", shell=True)

@authorized
async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("❌ Cancel Restart", callback_data="cancel_restart")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = await update.message.reply_text(
        "⚠️ *PC will restart in 30 seconds!*\nPress the button below to cancel.",
        parse_mode="Markdown", reply_markup=reply_markup
    )
    job = context.application.job_queue.run_once(execute_restart, 30, data=msg.message_id, name="restart_job")
    pending_actions["restart"] = job

async def execute_restart(context: ContextTypes.DEFAULT_TYPE):
    pending_actions.pop("restart", None)
    subprocess.Popen("shutdown /r /t 0", shell=True)

@authorized
async def cmd_logoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚪 Logging off...")
    try:
        subprocess.Popen("shutdown /l", shell=True)
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != AUTHORIZED_USER_ID:
        await query.answer("⛔ Unauthorized.")
        return
    await query.answer()
    if query.data == "cancel_shutdown" and "shutdown" in pending_actions:
        pending_actions["shutdown"].schedule_removal()
        pending_actions.pop("shutdown")
        await query.edit_message_text("✅ Shutdown cancelled.")
    elif query.data == "cancel_restart" and "restart" in pending_actions:
        pending_actions["restart"].schedule_removal()
        pending_actions.pop("restart")
        await query.edit_message_text("✅ Restart cancelled.")
    else:
        await query.edit_message_text("ℹ️ No pending action to cancel.")

@authorized
async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cancelled = []
    for key in list(pending_actions.keys()):
        pending_actions[key].schedule_removal()
        pending_actions.pop(key)
        cancelled.append(key)
    if cancelled:
        await update.message.reply_text(f"✅ Cancelled: {', '.join(cancelled)}")
    else:
        await update.message.reply_text("ℹ️ No pending actions to cancel.")

@authorized
async def cmd_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😴 Putting PC to sleep...")
    try:
        subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

@authorized
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        b_time = datetime.fromtimestamp(psutil.boot_time())
        up = datetime.now() - b_time
        bat = psutil.sensors_battery()
        bat_info = "🔌 No battery (Desktop)"
        if bat:
            plug = "🔌 Plugged in" if bat.power_plugged else "🔋 On battery"
            bat_info = f"{plug} — {bat.percent}%"
        h, rem = divmod(int(up.total_seconds()), 3600)
        m, _ = divmod(rem, 60)
        text = f"📊 *System Status*\n━━━━━━━━━━━━━━━━━━━━━━\n🖥️ *PC:* {platform.node()}\n💻 *OS:* {platform.system()} {platform.release()}\n⚡ *CPU:* {cpu}%\n🧠 *RAM:* {mem.percent}% ({mem.used // (1024**3)}/{mem.total // (1024**3)} GB)\n💾 *Disk:* {disk.percent}% ({disk.used // (1024**3)}/{disk.total // (1024**3)} GB)\n{bat_info}\n⏱️ *Uptime:* {h}h {m}m\n━━━━━━━━━━━━━━━━━━━━━━"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_processes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                if p.info: procs.append(p.info)
            except: pass
        procs.sort(key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)
        lines = ["📊 *Top Processes (by CPU)*", "━━━━━━━━━━━━━━━━━━━━━━"]
        for p in procs[:15]:
            n = (p["name"] or "Unknown")[:20]
            c = p.get("cpu_percent", 0) or 0
            m = p.get("memory_percent", 0) or 0
            lines.append(f"`{n:<20}` CPU: {c:.1f}% | RAM: {m:.1f}%")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lip = s.getsockname()[0]
        s.close()
        try: pip = requests.get("https://api.ipify.org", timeout=5).text
        except: pip = "Could not determine"
        text = f"🌐 *Network Info*\n━━━━━━━━━━━━━━━━━━━━━━\n🏠 *Local IP:* `{lip}`\n🌍 *Public IP:* `{pip}`\n💻 *Hostname:* `{socket.gethostname()}`\n━━━━━━━━━━━━━━━━━━━━━━"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_drives(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        lines = ["💾 *Drives*", "━━━━━━━━━━━━━━━━━━━━━━"]
        for p in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(p.mountpoint)
                lines.append(f"📀 `{p.device}` ({p.fstype})\n   Used: {u.used//(1024**3)}GB / {u.total//(1024**3)}GB ({u.percent}%) | Free: {u.free//(1024**3)}GB")
            except:
                lines.append(f"📀 `{p.device}` — Access denied")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bt = datetime.fromtimestamp(psutil.boot_time())
        up = datetime.now() - bt
        d = up.days
        h, r = divmod(up.seconds, 3600)
        m, s = divmod(r, 60)
        text = f"⏱️ *System Uptime*\n━━━━━━━━━━━━━━━━━━━━━━\n🕐 *Up for:* {d}d {h}h {m}m {s}s\n🖥️ *Boot time:* `{bt.strftime('%Y-%m-%d %H:%M:%S')}`\n━━━━━━━━━━━━━━━━━━━━━━"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_wifi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=10)
        out = r.stdout.strip()
        if not out or "not running" in out.lower():
            await update.message.reply_text("📶 WiFi adapter not found or disabled.")
            return
        lines = ["📶 *WiFi Info*", "━━━━━━━━━━━━━━━━━━━━━━"]
        for l in out.split("\n"):
            l = l.strip()
            for k in ["SSID", "Signal", "State", "Radio type", "Authentication", "Channel"]:
                if l.startswith(k) and "BSSID" not in l:
                    lines.append(f"• `{l}`")
                    break
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_tasklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        t = list(set([p.info["name"] for p in psutil.process_iter(["name"]) if p.info["name"] and not p.info["name"].startswith("svchost")]))
        t.sort()
        tl = "\n".join([f"• `{x}`" for x in t[:50]])
        text = f"📋 *Running Apps ({len(t)})*\n━━━━━━━━━━━━━━━━━━━━━━\n{tl}"
        if len(t) > 50: text += f"\n\n_...and {len(t) - 50} more_"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/kill <name>`", parse_mode="Markdown")
    t, k = " ".join(context.args).lower(), 0
    try:
        for p in psutil.process_iter(["name"]):
            try:
                if p.info["name"] and t in p.info["name"].lower():
                    p.kill()
                    k += 1
            except: pass
        await update.message.reply_text(f"💀 Killed {k} process(es) matching `{context.args[0]}`" if k else f"⚠️ No process matching `{context.args[0]}` found", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/open <path>`", parse_mode="Markdown")
    t = " ".join(context.args)
    try:
        os.startfile(t)
        await update.message.reply_text(f"✅ Opened: `{t}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to open: {e}")

@authorized
async def cmd_shell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/cmd <command>`", parse_mode="Markdown")
    c = " ".join(context.args)
    await update.message.reply_text(f"⚙️ Running: `{c}`", parse_mode="Markdown")
    try:
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=30)
        o = r.stdout or r.stderr or "(No output)"
        if len(o) > 3900: o = o[:3900] + "\n\n... (truncated)"
        await update.message.reply_text(f"```\n{o}\n```", parse_mode="Markdown")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏰ Command timed out (30s).")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/download <url>`", parse_mode="Markdown")
    url = context.args[0]
    await update.message.reply_text(f"⬇️ Downloading...")
    try:
        res = requests.get(url, stream=True, timeout=60)
        fn = url.split("/")[-1].split("?")[0] or "download"
        fp = os.path.join(os.path.expanduser("~"), "Desktop", fn)
        with open(fp, "wb") as f:
            for c in res.iter_content(chunk_size=8192): f.write(c)
        await update.message.reply_text(f"✅ Downloaded!\n📁 *File:* `{fn}`\n📂 *Saved to:* Desktop", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Download failed: {e}")

@authorized
async def cmd_sendfile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/sendfile <path>`", parse_mode="Markdown")
    fp = " ".join(context.args)
    try:
        if not os.path.exists(fp): return await update.message.reply_text(f"❌ File not found: `{fp}`", parse_mode="Markdown")
        smb = os.path.getsize(fp) / (1024 * 1024)
        if smb > 50: return await update.message.reply_text(f"❌ File too large ({smb:.1f}MB). Telegram limit is 50MB.")
        await update.message.reply_text(f"📤 Sending `{os.path.basename(fp)}` ({smb:.2f}MB)...", parse_mode="Markdown")
        with open(fp, "rb") as f: await update.message.reply_document(document=f, filename=os.path.basename(fp))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/browse <url>`", parse_mode="Markdown")
    import webbrowser
    u = context.args[0]
    if not u.startswith("http"): u = "https://" + u
    webbrowser.open(u)
    await update.message.reply_text(f"🌐 Opened: `{u}`", parse_mode="Markdown")

@authorized
async def cmd_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/volume <0-100>`", parse_mode="Markdown")
    try:
        l = int(context.args[0])
        if not 0 <= l <= 100: return await update.message.reply_text("⚠️ Volume must be between 0 and 100.")
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devs = AudioUtilities.GetSpeakers()
        face = devs.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(face, POINTER(IAudioEndpointVolume))
        vol.SetMasterVolumeLevelScalar(l / 100.0, None)
        b = "█" * (l // 10) + "░" * (10 - l // 10)
        await update.message.reply_text(f"🔊 Volume: {l}%\n[{b}]")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devs = AudioUtilities.GetSpeakers()
        face = devs.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(face, POINTER(IAudioEndpointVolume))
        m = vol.GetMute()
        vol.SetMute(not m, None)
        await update.message.reply_text("🔊 Unmuted!" if m else "🔇 Muted!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_brightness(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/brightness <0-100>`", parse_mode="Markdown")
    try:
        l = int(context.args[0])
        r = subprocess.run(["powershell", "-Command", f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{l})"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0: await update.message.reply_text(f"🔆 Brightness: {l}%\n[" + "☀" * (l // 10) + "░" * (10 - l // 10) + "]")
        else: await update.message.reply_text(f"❌ Failed:\n`{r.stderr.strip()}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/media <play/pause/next/prev/stop>`", parse_mode="Markdown")
    a = context.args[0].lower()
    vk = {"play": "0xB3", "pause": "0xB3", "next": "0xB0", "prev": "0xB1", "stop": "0xB2"}
    if a not in vk: return await update.message.reply_text("❌ Unknown action", parse_mode="Markdown")
    try:
        subprocess.run(["powershell", "-Command", f'Add-Type -TypeDefinition "using System; using System.Runtime.InteropServices; public class MediaKey {{ [DllImport(\\"user32.dll\\")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo); }}"; [MediaKey]::keybd_event({vk[a]}, 0, 0, [UIntPtr]::Zero); [MediaKey]::keybd_event({vk[a]}, 0, 2, [UIntPtr]::Zero)'], timeout=5)
        await update.message.reply_text(f"🎵 Media: {a}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_say(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/say <text>`", parse_mode="Markdown")
    t = " ".join(context.args).replace("'", "''")
    try:
        subprocess.Popen(["powershell", "-Command", f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{t}')"])
        await update.message.reply_text(f"🗣️ Speaking: \"{' '.join(context.args)}\"")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/alert <msg>`", parse_mode="Markdown")
    m = " ".join(context.args).replace("'", "''")
    try:
        subprocess.Popen(f'''powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('{m}', 'Telegram Alert', 'OK', 'Information')"''', shell=True)
        await update.message.reply_text(f"✅ Alert shown on PC: `{m}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_clipboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = subprocess.run(["powershell", "-Command", "Get-Clipboard"], capture_output=True, text=True, timeout=5)
        c = r.stdout.strip() or "(Clipboard is empty)"
        if len(c) > 3900: c = c[:3900] + "\n\n... (truncated)"
        await update.message.reply_text(f"📋 *Clipboard:*\n```\n{c}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_setclip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/setclip <text>`", parse_mode="Markdown")
    t = " ".join(context.args)
    try:
        subprocess.run(["powershell", "-Command", f"Set-Clipboard -Value '{t}'"], timeout=5)
        await update.message.reply_text(f"✅ Clipboard set to: `{t}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

@authorized
async def cmd_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: `/note <text>`", parse_mode="Markdown")
    t = " ".join(context.args)
    try:
        d = os.path.join(os.path.expanduser("~"), "Desktop")
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fp = os.path.join(d, f"TelegramNote_{ts}.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(f"📝 Telegram Note\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*40}\n\n{t}")
        await update.message.reply_text(f"📝 Note saved!\n📂 `{os.path.basename(fp)}`\n📁 Location: Desktop", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


def run_bot():
    # Reload config from file so subprocess gets latest GUI values
    fresh_cfg = load_config()
    global BOT_TOKEN, AUTHORIZED_USER_ID
    BOT_TOKEN = fresh_cfg.get("BOT_TOKEN", "").strip()
    AUTHORIZED_USER_ID = fresh_cfg.get("AUTHORIZED_USER_ID", "")
    try: AUTHORIZED_USER_ID = int(AUTHORIZED_USER_ID)
    except: AUTHORIZED_USER_ID = 0

    if not BOT_TOKEN or not AUTHORIZED_USER_ID:
        print("Error: Missing Configuration. Please set Bot Token and Chat ID in the GUI.")
        sys.exit(1)
    
    # Check if another instance is running via lock file
    import tempfile
    lock_file = os.path.join(tempfile.gettempdir(), 'telegram_pc_controller.lock')
    try:
        if os.path.exists(lock_file):
            pidstr = open(lock_file, "r").read().strip()
            if pidstr:
                try:
                    pid_int = int(pidstr)
                    if psutil.pid_exists(pid_int):
                        proc = psutil.Process(pid_int)
                        if '--run-bot' in ' '.join(proc.cmdline()):
                            print(f"Error: Another instance is already running (PID {pidstr})")
                            sys.exit(1)
                except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                    pass  # Stale lock, overwrite it
        open(lock_file, "w").write(str(os.getpid()))
    except Exception:
        pass

    print("=" * 60)
    print("  [PC] Telegram PC Controller Bot")
    print("=" * 60)
    print(f"  Bot Token:  ...{BOT_TOKEN[-8:]}")
    print(f"  Auth User:  {AUTHORIZED_USER_ID}")
    print(f"  Started:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("  [OK] Bot is running! Send /start on Telegram.")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    cmds = [
        ("start", cmd_start), ("help", cmd_start), ("myid", cmd_myid), ("screenshot", cmd_screenshot),
        ("webcam", cmd_webcam), ("lock", cmd_lock), ("shutdown", cmd_shutdown), ("restart", cmd_restart),
        ("logoff", cmd_logoff), ("cancel", cmd_cancel), ("sleep", cmd_sleep), ("status", cmd_status),
        ("processes", cmd_processes), ("ip", cmd_ip), ("drives", cmd_drives), ("uptime", cmd_uptime),
        ("wifi", cmd_wifi), ("tasklist", cmd_tasklist), ("kill", cmd_kill), ("open", cmd_open),
        ("cmd", cmd_shell), ("download", cmd_download), ("sendfile", cmd_sendfile), ("browse", cmd_browse),
        ("volume", cmd_volume), ("mute", cmd_mute), ("brightness", cmd_brightness), ("media", cmd_media),
        ("say", cmd_say), ("alert", cmd_alert), ("clipboard", cmd_clipboard), ("setclip", cmd_setclip),
        ("note", cmd_note)
    ]
    for c, f in cmds:
        app.add_handler(CommandHandler(c, f))
    app.add_handler(CallbackQueryHandler(cancel_callback))
    
    # We remove the lock file on exit (if possible safely)
    try:
        app.run_polling(drop_pending_updates=True)
    finally:
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except Exception:
            pass


# =====================================================================
#                        GUI MANAGER LOGIC
# =====================================================================

class Theme:
    BG = "#0d0d12"
    SURFACE = "#161620"
    SURFACE_2 = "#1c1c2a"
    BORDER = "#2a2a3d"
    GREEN = "#22c55e"
    GREEN_DIM = "#166534"
    RED = "#ef4444"
    BLUE = "#3b82f6"
    CYAN = "#06b6d4"
    AMBER = "#f59e0b"
    TEXT = "#f0f0f5"
    TEXT_2 = "#a0a0b8"
    TEXT_3 = "#606078"
    TEXT_DIM = "#3d3d55"

class BotManagerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Telegram PC Controller")
        
        # Load custom icon
        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
        if getattr(sys, 'frozen', False):
            ico_path = os.path.join(sys._MEIPASS, "app_icon.ico")
        try: self.root.iconbitmap(ico_path)
        except: pass

        self.root.geometry("480x860")
        self.root.resizable(False, False)
        self.root.configure(bg=Theme.BG)
        self.root.attributes('-alpha', 0.98)

        self.bot_process = None
        self.is_running = False
        self.minimize_on_close = False
        self.cmd_count = 0
        self.start_time = None

        self.fn = {
            "title": tkfont.Font(family="Segoe UI", size=16, weight="bold"),
            "subtitle": tkfont.Font(family="Segoe UI", size=9),
            "label": tkfont.Font(family="Segoe UI", size=10, weight="bold"),
            "small": tkfont.Font(family="Segoe UI", size=8),
            "tiny": tkfont.Font(family="Segoe UI", size=7),
            "status": tkfont.Font(family="Segoe UI", size=20, weight="bold"),
            "status_sub": tkfont.Font(family="Segoe UI", size=9),
            "log": tkfont.Font(family="Cascadia Code", size=8),
            "stat_num": tkfont.Font(family="Segoe UI", size=14, weight="bold"),
            "stat_lbl": tkfont.Font(family="Segoe UI", size=7),
        }

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        main = tk.Frame(self.root, bg=Theme.BG)
        main.pack(fill="both", expand=True, padx=20, pady=(14, 10))

        # Title Row
        title_row = tk.Frame(main, bg=Theme.BG)
        title_row.pack(fill="x")
        tk.Label(title_row, text="⚡", font=("Segoe UI", 16), bg=Theme.BG, fg=Theme.CYAN).pack(side="left", padx=(0, 6))
        title_col = tk.Frame(title_row, bg=Theme.BG)
        title_col.pack(side="left")
        tk.Label(title_col, text="PC Controller", font=self.fn["title"], fg=Theme.TEXT, bg=Theme.BG).pack(anchor="w")
        tk.Label(title_col, text="Telegram Remote Access", font=self.fn["tiny"], fg=Theme.TEXT_3, bg=Theme.BG).pack(anchor="w")

        # Power Section
        power_section = tk.Frame(main, bg=Theme.BG)
        power_section.pack(fill="x", pady=(10, 0))
        self.power_canvas = tk.Canvas(power_section, width=110, height=110, bg=Theme.BG, highlightthickness=0)
        self.power_canvas.pack()
        self._draw_power_off()
        self.power_canvas.bind("<Button-1>", self._toggle_bot)
        self.power_canvas.configure(cursor="hand2")

        self.status_text = tk.Label(power_section, text="OFFLINE", font=self.fn["status"], fg=Theme.RED, bg=Theme.BG)
        self.status_text.pack(pady=(4, 0))
        self.status_sub = tk.Label(power_section, text="Tap the button to start", font=self.fn["tiny"], fg=Theme.TEXT_3, bg=Theme.BG)
        self.status_sub.pack()

        # Stats Row
        stats_frame = tk.Frame(main, bg=Theme.SURFACE, highlightbackground=Theme.BORDER, highlightthickness=1)
        stats_frame.pack(fill="x", pady=(8, 0))

        for i, (icon, label, val_attr) in enumerate([("📡", "STATUS", "_stat_status"), ("⏱️", "UPTIME", "_stat_uptime"), ("📨", "CMDS", "_stat_cmds"), ("🤖", "SERVERS", "_stat_zombies")]):
            cell = tk.Frame(stats_frame, bg=Theme.SURFACE)
            cell.pack(side="left", fill="both", expand=True, padx=1)
            inner = tk.Frame(cell, bg=Theme.SURFACE)
            inner.pack(pady=8)
            tk.Label(inner, text=icon, font=("Segoe UI", 10), bg=Theme.SURFACE, fg=Theme.TEXT).pack()
            val_label = tk.Label(inner, text="--", font=self.fn["label"], fg=Theme.TEXT, bg=Theme.SURFACE)
            val_label.pack()
            setattr(self, val_attr, val_label)
            tk.Label(inner, text=label, font=self.fn["stat_lbl"], fg=Theme.TEXT_3, bg=Theme.SURFACE).pack()
            if i < 3:
                div = tk.Canvas(stats_frame, width=1, height=45, bg=Theme.SURFACE, highlightthickness=0)
                div.pack(side="left", fill="y", pady=8)
                div.create_line(0, 0, 0, 45, fill=Theme.BORDER)

        self._stat_status.configure(text="OFF", fg=Theme.RED)
        self._stat_uptime.configure(text="0m", fg=Theme.TEXT_2)
        self._stat_cmds.configure(text="0", fg=Theme.TEXT_2)
        self._stat_zombies.configure(text="0", fg=Theme.TEXT_2)

        self._update_zombies()

        # Configuration
        config_label = tk.Label(main, text="CONFIGURATION", font=self.fn["tiny"], fg=Theme.TEXT_3, bg=Theme.BG)
        config_label.pack(anchor="w", pady=(10, 3))

        cfg_frame = tk.Frame(main, bg=Theme.SURFACE, highlightbackground=Theme.BORDER, highlightthickness=1)
        cfg_frame.pack(fill="x")
        cfg_inner = tk.Frame(cfg_frame, bg=Theme.SURFACE)
        cfg_inner.pack(fill="x", padx=12, pady=8)

        tk.Label(cfg_inner, text="🔑 Bot Token:", font=self.fn["small"], fg=Theme.TEXT_2, bg=Theme.SURFACE).grid(row=0, column=0, sticky="w", pady=2)
        self.entry_token = tk.Entry(cfg_inner, font=self.fn["small"], bg=Theme.BG, fg=Theme.TEXT, insertbackground=Theme.TEXT, relief="flat", width=26, show="*")
        self.entry_token.grid(row=0, column=1, padx=4, pady=2, sticky="ew")
        self.entry_token.insert(0, BOT_TOKEN)
        paste_tok = tk.Label(cfg_inner, text="📋", font=("Segoe UI", 9), bg=Theme.SURFACE, fg=Theme.TEXT_2, cursor="hand2")
        paste_tok.grid(row=0, column=2, padx=2)
        paste_tok.bind("<Button-1>", lambda e: self._paste_to(self.entry_token))

        tk.Label(cfg_inner, text="👤 Chat ID:", font=self.fn["small"], fg=Theme.TEXT_2, bg=Theme.SURFACE).grid(row=1, column=0, sticky="w", pady=2)
        self.entry_id = tk.Entry(cfg_inner, font=self.fn["small"], bg=Theme.BG, fg=Theme.TEXT, insertbackground=Theme.TEXT, relief="flat", width=26)
        self.entry_id.grid(row=1, column=1, padx=4, pady=2, sticky="ew")
        self.entry_id.insert(0, str(AUTHORIZED_USER_ID) if AUTHORIZED_USER_ID else "")
        paste_id = tk.Label(cfg_inner, text="📋", font=("Segoe UI", 9), bg=Theme.SURFACE, fg=Theme.TEXT_2, cursor="hand2")
        paste_id.grid(row=1, column=2, padx=2)
        paste_id.bind("<Button-1>", lambda e: self._paste_to(self.entry_id))

        save_btn = tk.Label(cfg_inner, text=" SAVE ", font=self.fn["small"], bg=Theme.BLUE, fg="#ffffff", padx=8, pady=2, cursor="hand2")
        save_btn.grid(row=0, column=3, rowspan=2, padx=(4, 0))
        save_btn.bind("<Button-1>", lambda e: self._save_config())
        cfg_inner.columnconfigure(1, weight=1)

        # Settings
        settings_label = tk.Label(main, text="SETTINGS", font=self.fn["tiny"], fg=Theme.TEXT_3, bg=Theme.BG)
        settings_label.pack(anchor="w", pady=(10, 3))

        self._make_setting_row(main, "🚀", "Auto-Start with Windows", "Launch bot silently on login", self._check_autostart(), self._toggle_autostart)
        self._make_setting_row(main, "🔽", "Minimize on Close", "Keep bot running in background", False, self._toggle_minimize)
        self._make_action_row(main, "💀", "Kill All Servers", "Stop ANY running background bot", "KILL ALL", self._kill_all_zombies)

        # Log
        log_header = tk.Frame(main, bg=Theme.BG)
        log_header.pack(fill="x", pady=(10, 3))
        tk.Label(log_header, text="ACTIVITY LOG", font=self.fn["tiny"], fg=Theme.TEXT_3, bg=Theme.BG).pack(side="left")
        clear_lbl = tk.Label(log_header, text="Clear", font=self.fn["tiny"], fg=Theme.BLUE, bg=Theme.BG, cursor="hand2")
        clear_lbl.pack(side="right")
        clear_lbl.bind("<Button-1>", lambda e: self._clear_log())

        log_frame = tk.Frame(main, bg=Theme.SURFACE, highlightbackground=Theme.BORDER, highlightthickness=1)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, bg=Theme.SURFACE, fg=Theme.TEXT_2, font=self.fn["log"], relief="flat", padx=10, pady=6, wrap="word", state="disabled", height=4, borderwidth=0)
        self.log_text.pack(fill="both", expand=True)

        self.log_text.tag_configure("time", foreground=Theme.TEXT_DIM)
        self.log_text.tag_configure("info", foreground=Theme.BLUE)
        self.log_text.tag_configure("success", foreground=Theme.GREEN)
        self.log_text.tag_configure("error", foreground=Theme.RED)
        self.log_text.tag_configure("warn", foreground=Theme.AMBER)

        self._log("Ready. Enter config and tap power.", "info")

        # Author Footer
        footer = tk.Frame(main, bg=Theme.BG)
        footer.pack(fill="x", pady=(6, 0))
        author_lbl = tk.Label(footer, text="Made with \u2764\ufe0f by Nothing-dot-exe", font=self.fn["tiny"], fg=Theme.TEXT_3, bg=Theme.BG)
        author_lbl.pack(side="left")
        gh_btn = tk.Label(footer, text="  \U0001f310 GitHub", font=self.fn["tiny"], fg=Theme.CYAN, bg=Theme.BG, cursor="hand2")
        gh_btn.pack(side="right")
        gh_btn.bind("<Button-1>", lambda e: __import__('webbrowser').open("https://github.com/Nothing-dot-exe"))
        
    def _paste_to(self, entry):
        try:
            clip = self.root.clipboard_get()
            entry.delete(0, "end")
            entry.insert(0, clip.strip())
            self._log("Pasted from clipboard.", "info")
        except tk.TclError:
            self._log("Clipboard is empty.", "warn")

    def _save_config(self):
        tok = self.entry_token.get().strip()
        uid = self.entry_id.get().strip()
        try: uid = int(uid) if uid else 0
        except: uid = 0
        save_config(tok, uid)
        self._log("Config saved! Restart bot to apply changes.", "success")

    def _make_action_row(self, parent, icon, title, desc, btn_text, callback):
        row = tk.Frame(parent, bg=Theme.SURFACE, highlightbackground=Theme.BORDER, highlightthickness=1)
        row.pack(fill="x", pady=(0, 4))
        inner = tk.Frame(row, bg=Theme.SURFACE)
        inner.pack(fill="x", padx=14, pady=10)
        tk.Label(inner, text=icon, font=("Segoe UI", 13), bg=Theme.SURFACE, fg=Theme.TEXT).pack(side="left", padx=(0, 10))
        text_col = tk.Frame(inner, bg=Theme.SURFACE)
        text_col.pack(side="left", fill="x", expand=True)
        tk.Label(text_col, text=title, font=self.fn["label"], fg=Theme.TEXT, bg=Theme.SURFACE).pack(anchor="w")
        tk.Label(text_col, text=desc, font=self.fn["tiny"], fg=Theme.TEXT_3, bg=Theme.SURFACE).pack(anchor="w")
        btn = tk.Label(inner, text=btn_text, font=self.fn["small"], bg=Theme.RED, fg="#ffffff", padx=8, pady=4, cursor="hand2")
        btn.pack(side="right")
        btn.bind("<Button-1>", lambda e: callback())

    def _update_zombies(self):
        try:
            count = sum(1 for p in psutil.process_iter(['cmdline']) if p.info.get('cmdline') and '--run-bot' in p.info['cmdline'])
            self._stat_zombies.configure(text=str(count), fg=Theme.RED if count > 0 else Theme.TEXT_2)
        except: pass
        self.root.after(2000, self._update_zombies)

    def _kill_all_zombies(self):
        self._log("Killing all background bot servers...", "warn")
        killed = 0
        for p in psutil.process_iter(['cmdline']):
            try:
                cmd = p.info.get('cmdline')
                if cmd and '--run-bot' in cmd:
                    p.kill()
                    killed += 1
            except: pass
        import tempfile
        lock_file = os.path.join(tempfile.gettempdir(), 'telegram_pc_controller.lock')
        if os.path.exists(lock_file):
            try: os.remove(lock_file)
            except: pass
        self.is_running = False
        self.bot_process = None
        self._update_ui_stopped()
        self._log(f"Killed {killed} background server(s).", "success")
        self._update_zombies()

    def _make_setting_row(self, parent, icon, title, desc, initial, callback):
        row = tk.Frame(parent, bg=Theme.SURFACE, highlightbackground=Theme.BORDER, highlightthickness=1)
        row.pack(fill="x", pady=(0, 4))
        inner = tk.Frame(row, bg=Theme.SURFACE)
        inner.pack(fill="x", padx=14, pady=10)
        tk.Label(inner, text=icon, font=("Segoe UI", 13), bg=Theme.SURFACE, fg=Theme.TEXT).pack(side="left", padx=(0, 10))
        text_col = tk.Frame(inner, bg=Theme.SURFACE)
        text_col.pack(side="left", fill="x", expand=True)
        tk.Label(text_col, text=title, font=self.fn["label"], fg=Theme.TEXT, bg=Theme.SURFACE).pack(anchor="w")
        tk.Label(text_col, text=desc, font=self.fn["tiny"], fg=Theme.TEXT_3, bg=Theme.SURFACE).pack(anchor="w")
        
        toggle = tk.Canvas(inner, width=44, height=24, bg=Theme.SURFACE, highlightthickness=0, cursor="hand2")
        toggle.pack(side="right")
        toggle._is_on = initial
        toggle._callback = callback
        self._draw_toggle(toggle, initial)
        toggle.bind("<Button-1>", lambda e, t=toggle: self._click_toggle(t))

    def _draw_toggle(self, canvas, is_on):
        canvas.delete("all")
        w, h, r = 44, 24, 12
        if is_on: track_color, knob_x = Theme.GREEN, w - r
        else: track_color, knob_x = Theme.TEXT_DIM, r
        canvas.create_oval(1, 1, h-1, h-1, fill=track_color, outline="")
        canvas.create_oval(w-h+1, 1, w-1, h-1, fill=track_color, outline="")
        canvas.create_rectangle(r, 1, w-r, h-1, fill=track_color, outline="")
        knob_r = r - 3
        canvas.create_oval(knob_x - knob_r, r - knob_r, knob_x + knob_r, r + knob_r, fill="#ffffff", outline="")

    def _click_toggle(self, toggle):
        toggle._is_on = not toggle._is_on
        self._draw_toggle(toggle, toggle._is_on)
        if toggle._callback: toggle._callback(toggle._is_on)

    def _draw_power_off(self):
        c = self.power_canvas
        c.delete("all")
        cx, cy = 55, 55
        c.create_oval(8, 8, 102, 102, fill=Theme.SURFACE, outline=Theme.BORDER, width=2)
        c.create_oval(14, 14, 96, 96, fill=Theme.SURFACE_2, outline="")
        icon_r = 18
        c.create_arc(cx-icon_r, cy-icon_r+4, cx+icon_r, cy+icon_r+4, start=50, extent=260, style="arc", outline=Theme.RED, width=3)
        c.create_line(cx, cy-icon_r-1, cx, cy+2, fill=Theme.RED, width=3)

    def _draw_power_on(self):
        c = self.power_canvas
        c.delete("all")
        cx, cy = 55, 55
        for i in range(2):
            offset = (i + 1) * 3
            c.create_oval(8-offset, 8-offset, 102+offset, 102+offset, fill="", outline=Theme.GREEN_DIM, width=1)
        c.create_oval(8, 8, 102, 102, fill=Theme.SURFACE, outline=Theme.GREEN, width=2)
        c.create_oval(14, 14, 96, 96, fill="#0d1a0d", outline="")
        icon_r = 18
        c.create_arc(cx-icon_r, cy-icon_r+4, cx+icon_r, cy+icon_r+4, start=50, extent=260, style="arc", outline=Theme.GREEN, width=3)
        c.create_line(cx, cy-icon_r-1, cx, cy+2, fill=Theme.GREEN, width=3)

    def _toggle_bot(self, event=None):
        if self.is_running: self._stop_bot()
        else: self._start_bot()

    def _start_bot(self):
        # Auto-save config from GUI fields before launching
        tok = self.entry_token.get().strip()
        uid = self.entry_id.get().strip()
        if not tok or not uid:
            self._log("Missing Bot Token or Chat ID! Fill in Configuration first.", "error")
            return
        try:
            uid_int = int(uid)
        except ValueError:
            self._log("Chat ID must be a number!", "error")
            return
        save_config(tok, uid_int)

        self._log("Starting bot...", "info")
        try:
            # RUN ITSELF WITH THE `--run-bot` FLAG
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--run-bot"]
            else:
                cmd = [PYTHON_EXE, THIS_SCRIPT, "--run-bot"]

            self.bot_process = subprocess.Popen(
                cmd,
                cwd=SCRIPT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
                env=dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
            )
            self.is_running = True
            self.start_time = datetime.now()
            self.cmd_count = 0
            self._update_ui_running()
            self._log("Bot is online!", "success")
            
            t = threading.Thread(target=self._read_output, daemon=True)
            t.start()
            self._update_uptime()
        except Exception as e:
            self._log(f"Start failed: {e}", "error")

    def _stop_bot(self):
        if self.bot_process:
            self._log("Stopping bot...", "warn")
            try:
                self.bot_process.terminate()
                try: self.bot_process.wait(timeout=5)
                except subprocess.TimeoutExpired: self.bot_process.kill()
                self.bot_process = None
            except Exception as e:
                self._log(f"Stop error: {e}", "error")
                
            # Also clean up python-telegram-bot leftover processes
            import tempfile
            lock_file = os.path.join(tempfile.gettempdir(), 'telegram_pc_controller.lock')
            try:
                if os.path.exists(lock_file):
                    pidstr = open(lock_file, "r").read().strip()
                    if pidstr and psutil.pid_exists(int(pidstr)):
                        psutil.Process(int(pidstr)).kill()
                    os.remove(lock_file)
            except Exception:
                pass


        self.is_running = False
        self.start_time = None
        self._update_ui_stopped()
        self._log("Bot stopped.", "error")

    def _read_output(self):
        try:
            while self.bot_process and self.bot_process.poll() is None:
                line = self.bot_process.stdout.readline()
                if line:
                    text = line.decode("utf-8", errors="replace").strip()
                    if text and "httpx" not in text and "HTTP Request" not in text:
                        if "INCOMING" in text or "sendMessage" in text or "Capturing" in text:
                            self.cmd_count += 1
                            self.root.after(0, self._stat_cmds.configure, {"text": str(self.cmd_count)})
                        
                        if text.startswith("Error:") or text.startswith("Traceback") or "Exception:" in text:
                            self.root.after(0, self._log, text, "error")
                            if text.startswith("Error: Another"):
                                self.is_running = False
                                self.root.after(0, self._stop_bot)
                        else:
                            self.root.after(0, self._log, text, "info")
        except Exception:
            pass

        if self.is_running:
            self.is_running = False
            self.start_time = None
            self.root.after(0, self._update_ui_stopped)
            self.root.after(0, self._log, "Bot process exited.", "error")

    def _update_uptime(self):
        if self.is_running and self.start_time:
            total_sec = int((datetime.now() - self.start_time).total_seconds())
            if total_sec < 60: text = f"{total_sec}s"
            elif total_sec < 3600: text = f"{total_sec // 60}m"
            else: text = f"{total_sec // 3600}h{(total_sec % 3600) // 60}m"
            self._stat_uptime.configure(text=text, fg=Theme.GREEN)
            self.root.after(1000, self._update_uptime)

    def _update_ui_running(self):
        self._draw_power_on()
        self.status_text.configure(text="ONLINE", fg=Theme.GREEN)
        self.status_sub.configure(text="Bot is running and listening")
        self._stat_status.configure(text="ON", fg=Theme.GREEN)

    def _update_ui_stopped(self):
        self._draw_power_off()
        self.status_text.configure(text="OFFLINE", fg=Theme.RED)
        self.status_sub.configure(text="Tap the button to start")
        self._stat_status.configure(text="OFF", fg=Theme.RED)
        self._stat_uptime.configure(text="0m", fg=Theme.TEXT_2)

    def _log(self, message, tag="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{ts}] ", "time")
        self.log_text.insert("end", f"{message}\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _get_startup_key(self):
        return winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)

    def _check_autostart(self):
        try:
            key = self._get_startup_key()
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except: return False

    def _toggle_autostart(self, is_on):
        try:
            key = self._get_startup_key()
            if is_on:
                vbs_path = os.path.join(SCRIPT_DIR, "TelegramAutoStart.vbs")
                # Always regenerate in case paths changed
                with open(vbs_path, "w") as f:
                    f.write(f'Set WshShell = CreateObject("WScript.Shell")\n')
                    if getattr(sys, 'frozen', False):
                        f.write(f'WshShell.Run """{sys.executable}"" --run-bot", 0, False\n')
                    else:
                        f.write(f'WshShell.Run """{PYTHON_EXE}"" ""{THIS_SCRIPT}"" --run-bot", 0, False\n')
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'wscript.exe "{vbs_path}"')
                self._log("Auto-start enabled", "success")
            else:
                try: winreg.DeleteValue(key, APP_NAME)
                except: pass
                self._log("Auto-start disabled", "warn")
            winreg.CloseKey(key)
        except Exception as e:
            self._log(f"Registry error: {e}", "error")

    def _toggle_minimize(self, is_on):
        self.minimize_on_close = is_on
        self._log("Minimize on close enabled" if is_on else "Minimize on close disabled", "info")

    def _on_close(self):
        if self.minimize_on_close and self.is_running:
            self.root.withdraw()
            return
        if self.is_running: self._stop_bot()
        self.root.destroy()

    def run(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"+{x}+{y}")
        self.root.mainloop()

# =====================================================================
#                          BOOTSTRAPPING
# =====================================================================

if __name__ == "__main__":
    if "--run-bot" in sys.argv:
        # Running as the invisible background bot
        run_bot()
    else:
        # Running as the visible GUI manager
        app = BotManagerGUI()
        app.run()

# monitor.py
import psutil
import asyncio

def get_vps_usage():
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent()
    used = round(ram.used / (1024**3), 2)
    total = round(ram.total / (1024**3), 2)
    return f"🧠 RAM: {used} GB / {total} GB ({ram.percent}%)\n💻 CPU: {cpu}%"

async def live_status_updater(msg, filename: str, stage: str, stop_event: asyncio.Event):
    while not stop_event.is_set():
        usage = get_vps_usage()
        try:
            await msg.edit_text(f"""<blockquote>‣ <b>Anime Name :</b> <b><i>{filename}</i></b></blockquote>
            <b><blockquote>‣ <b>Status:</b> <i>{stage}</i></b></blockquote>""")
        except:
            pass
        await asyncio.sleep(5)

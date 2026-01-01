import asyncio
import os
import re
from asyncio import Event
from os import path as ospath
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove
from traceback import format_exc
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

# ── CONFIG & CORE ─────────────────────────────────────────────────────────────
from config import Var
from bot.core.bot_instance import bot, bot_loop, ani_cache, ffQueue, ffLock, ff_queued
from .tordownload import TorDownloader
from .database import db  # ← MongoDB helpers
from .func_utils import getfeed, encode, editMessage, sendMessage, convertBytes
from .text_utils import TextEditor
from .ffencoder import FFEncoder
from .tguploader import TgUploader
from .reporter import rep
from status import live_status_updater

# ── BUTTON FORMATTER ───────────────────────────────────────────────────────────
btn_formatter = {
    'HDRip': 'HDRip',
    '1080': '1080P',
    '720': '720P',
    '480': '480P',
    '360': '360P'
}

async def log_unmapped_anime(anime_name: str):
    anime_name = anime_name.strip()
    try:
        if not ospath.exists("unmapped.log"):
            async with aiopen("unmapped.log", "w") as f:
                await f.write(anime_name + "\n")
            return
        async with aiopen("unmapped.log", "r+") as f:
            lines = await f.readlines()
            if anime_name + "\n" in lines:
                return
            lines.append(anime_name + "\n")
            if len(lines) > 50:
                lines = lines[-50:]
            await f.seek(0)
            await f.truncate()
            await f.writelines(lines)
    except Exception as e:
        await rep.report(f"Unmapped log error: {e}", "error", log=True)

# ---------------------- Admin poster commands (unchanged) ---------------------
@bot.on_message(filters.command("getposter") & filters.user(Var.ADMINS))
async def get_anime_poster_handler(client, message):
    try:
        args = message.text.split(None, 1)
        if len(args) < 2:
            poster_list = await db.list_all_anime_posters()
            if not poster_list:
                return await message.reply_text("🤷‍♂️ No anime have a custom poster set.")
            text = "🖼️ ᴀɴɪᴍᴇ ᴡɪᴛʜ ᴄᴜꜱᴛᴏᴍ ᴘᴏꜱᴛᴇʀꜱ :\n\n"
            for anime in poster_list:
                text += f"<b>• {anime}\n"
            text += "\nᴛᴏ ꜱᴇᴇ ᴀ ꜱᴘᴇᴄɪꜰɪᴄ ᴘᴏꜱᴛᴇʀ ᴜꜱᴇ /getposter <anime name></b>"
            return await message.reply_text(text)
        anime_name = args[1].strip()
        poster_file_id = await db.get_anime_poster(anime_name)
        if poster_file_id:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=poster_file_id,
                caption=f"<b>🖼️ ᴛʜɪꜱ ɪꜱ ᴛʜᴇ ᴄᴜꜱᴛᴏᴍ ᴘᴏꜱᴛᴇʀ ꜰᴏʀ • {anime_name} •</b>"
            )
        else:
            await message.reply_text(
                f"<b>💀 ɴᴏ ᴄᴜꜱᴛᴏᴍ ᴘᴏꜱᴛᴇʀ ꜰᴏᴜɴᴅ ꜰᴏʀ • {anime_name} •</b>"
            )
    except Exception as e:
        await message.reply_text(f"❌ An error occurred: {e}")

@bot.on_message(filters.command("setposter") & filters.user(Var.ADMINS))
async def set_anime_poster_handler(client, message):
    try:
        if not message.reply_to_message or not message.reply_to_message.photo:
            return await message.reply_text("❌ ᴜꜱᴀɢᴇ:\nʀᴇᴘʟʏ ᴛᴏ ᴀ ᴘʜᴏᴛᴏ ᴡɪᴛʜ :\n/setposter <anime name>")
        args = message.text.split(None, 1)
        if len(args) < 2:
            return await message.reply_text("❌ ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴀɴɪᴍᴇ ɴᴀᴍᴇ : /setposter <anime name>")
        anime_name = args[1].strip()
        poster_file_id = message.reply_to_message.photo.file_id
        await db.set_anime_poster(anime_name, poster_file_id)
        await message.reply_text(f"<b>✅ ᴄᴜꜱᴛᴏᴍ ᴘᴏꜱᴛᴇʀ ꜱᴇᴛ ꜰᴏʀ • {anime_name} •</b>")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@bot.on_message(filters.command("delposter") & filters.user(Var.ADMINS))
async def delete_anime_poster_handler(client, message):
    try:
        args = message.text.split(None, 1)
        if len(args) < 2:
            return await message.reply_text("❌ Usage:\n/delposter <anime name>")
        anime_name = args[1].strip()
        await db.delete_anime_poster(anime_name)
        await message.reply_text(f"<b>✅ ʀᴇᴍᴏᴠᴇᴅ ᴄᴜꜱᴛᴏᴍ ᴘᴏꜱᴛᴇʀ ꜰᴏʀ • {anime_name} •</b>")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# ---------------------- RSS & Core Processing -------------------------------
@bot.on_message(filters.command("add_rss") & filters.user(Var.ADMINS))
async def add_custom_rss(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage:\n`/add_rss https://example.com/rss`")
        await rep.report("Invalid /add_rss command: Missing URL", "error", log=True)
        return
    url = message.command[1]
    if not url.startswith("http"):
        await message.reply_text("Invalid URL format.")
        await rep.report(f"Invalid RSS URL: {url}", "error", log=True)
        return
    ani_cache.setdefault("custom_rss", set()).add(url)
    await message.reply_text(f"RSS feed added:\n`{url}`")
    await rep.report(f"RSS feed added: {url}", "info", log=True)

@bot.on_message(filters.command("list_rss") & filters.user(Var.ADMINS))
async def list_rss(client, message: Message):
    feeds = list(ani_cache.get("custom_rss", []))
    if not feeds:
        await message.reply_text("No custom RSS links added yet.")
    else:
        await message.reply_text("Custom RSS Feeds:\n" + "\n".join([f"• {f}" for f in feeds]))
    await rep.report("Listed custom RSS feeds.", "info", log=True)

@bot.on_message(filters.command("remove_rss") & filters.user(Var.ADMINS))
async def remove_rss(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage:\n`/remove_rss https://example.com/rss`")
        return
    url = message.command[1]
    if url in ani_cache.get("custom_rss", set()):
        ani_cache.get("custom_rss", set()).remove(url)
        await message.reply_text(f"Removed:\n`{url}`")
        await rep.report(f"RSS feed removed: {url}", "info", log=True)
    else:
        await message.reply_text("RSS link not found.")
        await rep.report(f"RSS link not found: {url}", "warning", log=True)

# ---------------------- setchannel -------------------------------------------
@bot.on_message(filters.command("setchannel") & filters.user(Var.ADMINS))
async def set_channel(client, message: Message):
    try:
        if len(message.command) < 3:
            await message.reply_text(
                "<u>Usage</u>:\n"
                "<blockquote expandable>/setchannel &lt;anime_name&gt; &lt;channel_id&gt;\n"
            )
            return
        anime_name = " ".join(message.command[1:-1])
        try:
            channel_id = int(message.command[-1])
        except ValueError:
            await message.reply_text("Invalid channel ID – must be numeric.")
            return

        ani_info = TextEditor(anime_name)
        await ani_info.load_anilist()
        ani_id = ani_info.adata.get('id')
        if not ani_id:
            await message.reply_text(f"Anime not found: `{anime_name}`\nTry exact title from Anilist.")
            await rep.report(f"Anime not found: {anime_name}", "error", log=True)
            return

        await db.set_anime_channel(ani_id, channel_id)

        await message.reply_text(
            f"<b>Mapping Saved</b>\n\n"
            f"<b>Anime</b>: <i>{anime_name}</i>\n"
            f"<b>ID</b>: <code>{ani_id}</code>\n"
            f"<b>Channel</b>: <code>{channel_id}</code>"
        )
        await rep.report(
            f"Mapped {anime_name} ({ani_id}) → {channel_id}",
            "info", log=True
        )
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")
        await rep.report(f"/setchannel error: {format_exc()}", "error", log=True)

# ---------------------- setsticker -----------------------------------------
@bot.on_message(filters.command("setsticker") & filters.user(Var.ADMINS))
async def set_sticker(client, message: Message):
    sticker_id = None
    if message.reply_to_message and message.reply_to_message.sticker:
        sticker_id = message.reply_to_message.sticker.file_id
    elif len(message.command) >= 2:
        sticker_id = message.command[1]
    if not sticker_id:
        await message.reply_text("Reply to a sticker or give its file_id.")
        return
    try:
        await bot.send_sticker(message.chat.id, sticker=sticker_id)
    except Exception as e:
        await message.reply_text(f"Invalid sticker: {e}")
        return
    await db.set_sticker(sticker_id)
    await message.reply_text(f"Sticker set: `{sticker_id}`")
    await rep.report(f"Sticker set: {sticker_id}", "info", log=True)

# ---------------------- listchannels ---------------------------------------
@bot.on_message(filters.command("listchannels") & filters.user(Var.ADMINS))
async def list_channels(client, message: Message):
    mappings = await db.get_all_anime_channels()
    if not mappings:
        await message.reply_text("No anime channels mapped yet.")
        return
    txt = "<b>Anime → Channel Mapping</b>\n\n"
    for m in mappings:
        ani_id = m["ani_id"]
        channel_id = m["channel_id"]
        try:
            info = TextEditor(f"id:{ani_id}")
            await info.load_anilist()
            name = info.adata.get('title', {}).get('romaji', f"ID:{ani_id}")
        except Exception:
            name = f"ID:{ani_id}"
        txt += f"• <b>{name}</b> → <code>{channel_id}</code>\n"
    await message.reply_text(txt)
    await rep.report(f"Listed {len(mappings)} mappings", "info", log=True)

# ---------------------- RSS FETCHER ----------------------------------------
async def fetch_animes():
    await rep.report("RSS fetch loop started", "info", log=True)
    while True:
        try:
            await asyncio.sleep(60)
            if not ani_cache.get('fetch_animes', True):
                continue
            all_rss = Var.RSS_ITEMS + list(ani_cache.get("custom_rss", []))
            for link in all_rss:
                info = await getfeed(link, 0)
                if info:
                    asyncio.create_task(get_animes(info.title, info.link))
                else:
                    await rep.report(f"No info from link: {link}", "warning", log=True)
        except Exception as e:
            await rep.report(f"Error in fetch_animes loop: {e}", "error", log=True)

# ---------------------- CORE PROCESSING (fixed) -----------------------------
async def get_animes(name, torrent, force=False):
    try:
        aniInfo = TextEditor(name)
        await aniInfo.load_anilist()

        # STOP if AniList search fails
        if not aniInfo.adata:
            await rep.report(f"❌ AniList search failed for: `{name}`. Skipping this torrent.", "warning", log=True)
            return

        ani_id = aniInfo.adata.get('id')
        ep_no = aniInfo.pdata.get('episode_number')

        # 🔥 PATCH: Fallback extract episode number from torrent name when AniList misses it
        if not ep_no:
            # Common patterns: - 12 (1080p), Episode 12, ep12, 12v2, S01E12 etc.
            m = re.search(r"(?:episode|ep|e)\s*(\d{1,3})", name, flags=re.I)
            if not m:
                m = re.search(r"\b(\d{1,3})\b(?=[^\d]*(?:p|1080|720|480)?)", name)
            if m:
                try:
                    ep_no = int(m.group(1))
                except Exception:
                    ep_no = None

        if not ep_no:
            await rep.report(f"❌ Episode number missing → Skipping: {name}", "warning", log=True)
            return

        titles = aniInfo.adata.get("title", {})
        anime_title = (titles.get("english") or titles.get("romaji") or titles.get("native") or name).lower().strip()

        channel_id = await db.get_anime_channel(ani_id)
        if not channel_id:
            channel_id = Var.MAIN_CHANNEL
            ani_cache.setdefault("unmapped", set())
            if anime_title not in ani_cache["unmapped"]:
                asyncio.create_task(log_unmapped_anime(anime_title))
                ani_cache["unmapped"].add(anime_title)

        # Use cache key per anime+episode to avoid freezing across episodes
        cache_key = f"{ani_id}_{ep_no}"
        ani_cache.setdefault('ongoing', set())
        ani_cache.setdefault('completed', set())

        if cache_key not in ani_cache['ongoing']:
            ani_cache['ongoing'].add(cache_key)
        elif not force:
            return

        if not force and cache_key in ani_cache['completed']:
            return

        ani_data = await db.get_anime(ani_id)
        qual_data = ani_data.get(ep_no) if ani_data else None
        if force or not ani_data or not qual_data or not all(qual for qual in qual_data.values()):
            if "[BATCH] batch Batch" in name:
                await rep.report(f"Torrent Skipped!\n\n{name}", "warning", log=True)
                return

            ani_cache.setdefault("reported_ids", set())
            if ani_id not in ani_cache["reported_ids"]:
                await rep.report(f"New Anime Torrent Found!\n\n{name}", "info", log=True)
                ani_cache["reported_ids"].add(ani_id)

            stat_msg = await sendMessage(Var.LOG_CHANNEL, f"<b><blockquote>‣ Anime Name : <i><b>{name}</b></i></blockquote>\n<blockquote><i>Downloading...</i></blockquote></b>")

            # Progress callback for TorDownloader
            last_edit_time = 0
            async def progress_callback(data):
                nonlocal last_edit_time
                now = asyncio.get_event_loop().time()
                if now - last_edit_time < 5:  # Limit updates to every 5 seconds
                    return
                last_edit_time = now

                progress = data.get('progress', 0)
                dl_speed = data.get('download_rate', 0)
                ul_speed = data.get('upload_rate', 0)
                peers = data.get('peers', 0)
                total_done = data.get('total_done', 0)
                total_wanted = data.get('total_wanted', 1) # avoid div by zero

                # Calculate Percentage
                percent = progress * 100

                # Format Progress Bar
                bar_length = 12
                filled_length = int(bar_length * progress)
                bar = "█" * filled_length + "▒" * (bar_length - filled_length)

                # Format Sizes and Speed
                done_str = convertBytes(total_done)
                total_str = convertBytes(total_wanted)
                speed_str = f"{convertBytes(dl_speed)}/s"

                text = (
                    f"<b><blockquote>‣ Anime Name : <i><b>{name}</b></i></blockquote></b>\n"
                    f"<b><blockquote>‣ Status : <i>📥 Downloading</i>\n"
                    f"    <code>[{bar}]</code> {percent:.2f}%\n"
                    f"    ‣ <b>Speed :</b> {speed_str}\n"
                    f"    ‣ <b>Size :</b> {done_str} / {total_str}\n"
                    f"    ‣ <b>Peers :</b> {peers}</blockquote></b>"
                )
                await editMessage(stat_msg, text)

            dl = None
            try:
                # Pass callback to download
                dl = await TorDownloader("./downloads").download(torrent, name, progress_callback)
            except Exception as e:
                await rep.report(f"Downloader error: {e}", "error", log=True)
                dl = None

            if not dl or not ospath.exists(dl):
                await rep.report("File Download Incomplete, Try Again", "error", log=True)
                await stat_msg.delete()
                ani_cache['ongoing'].discard(cache_key)
                return

            post_id = None
            ffEvent = Event()
            ff_queued[torrent] = ffEvent
            try:
                if ffLock.locked():
                    await editMessage(stat_msg, f"<b><blockquote><b>‣ Anime Name :</b> <i><b>{name}</i></b></blockquote>\n<blockquote><i>Queued to Encode...</i></b></blockquote>")
                    await rep.report("Added Task to Queue...", "info", log=True)

                await ffQueue.put(torrent)
                await ffEvent.wait()
                await ffLock.acquire()

                btns = []
                quality_data = {}

                photo_url = await aniInfo.get_poster()
                main_caption = await aniInfo.get_caption()

                specific_post_msg = None
                main_post_msg = None

                for qual in Var.QUALS:
                    filename = await aniInfo.get_upname(qual)
                    await editMessage(stat_msg, f"<b><blockquote>‣ <b>Anime Name :</b> <i><b>{name}</i></b></blockquote\n<blockquote><i>Ready to Encode...</i></b></blockquote>")
                    await asyncio.sleep(1.5)
                    await rep.report("Starting Encode...", "info", log=True)
                    try:
                        encoder = FFEncoder(stat_msg, dl, filename, qual)
                        out_path = await encoder.start_encode()
                    except Exception as e:
                        await rep.report(f"Encoding Error: {e}", "error", log=True)
                        await stat_msg.delete()
                        return

                    await rep.report("Successfully Compressed. Now Uploading...", "info", log=True)
                    await editMessage(stat_msg, f"<b><blockquote>‣ <b>Anime Name :</b> <i><b>{filename}</i></b></blockquote\n\n<blockquote><i>Ready to Upload...</i></b></blockquote>")
                    await asyncio.sleep(1.5)

                    try:
                        msg = await TgUploader(stat_msg).upload(out_path, qual)
                    except Exception as e:
                        await rep.report(f"Upload Error: {e}", "error", log=True)
                        await stat_msg.delete()
                        return

                    await rep.report("Successfully Uploaded to Telegram.", "info", log=True)
                    msg_id = msg.id
                    bot_me = await bot.get_me()
                    link = f"https://telegram.me/{bot_me.username}?start={await encode('get-'+str(msg_id * abs(Var.FILE_STORE)))}"
                    quality_data[qual] = link

                    # Build buttons grouped by threes
                    current_btns = []
                    for q in Var.QUALS:
                        if q in quality_data:
                            btn = InlineKeyboardButton(f"{btn_formatter[q]}", url=quality_data[q])
                            if current_btns and len(current_btns[-1]) < 3:
                                current_btns[-1].append(btn)
                            else:
                                current_btns.append([btn])

                    # Determine photo to use
                    photo_to_use = photo_url or "https://envs.sh/YsH.jpg"

                    # If photo_to_use looks like a local path, ensure exists, otherwise send as file_id/url
                    try:
                        if isinstance(photo_to_use, str) and not photo_to_use.startswith('http') and ospath.exists(photo_to_use):
                            send_photo_arg = photo_to_use
                        else:
                            send_photo_arg = photo_to_use
                    except Exception:
                        send_photo_arg = photo_to_use

                    # Posting logic
                    try:
                        if channel_id != Var.MAIN_CHANNEL:
                            if specific_post_msg is None:
                                try:
                                    specific_post_msg = await bot.send_photo(
                                        channel_id,
                                        photo=send_photo_arg,
                                        caption=main_caption,
                                        reply_markup=InlineKeyboardMarkup(current_btns)
                                    )
                                except Exception as e:
                                    await rep.report(f"Failed to post to specific channel {channel_id}: {e}", "error", log=True)
                                    specific_post_msg = None

                            else:
                                await editMessage(specific_post_msg, main_caption, InlineKeyboardMarkup(current_btns))

                            if specific_post_msg:
                                post_id = specific_post_msg.id
                                if ep_no is not None:
                                    await db.save_anime(ani_id, ep_no, qual, post_id)

                                if main_post_msg is None:
                                    try:
                                        chat = await bot.get_chat(channel_id)
                                        if chat.username:
                                            join_url = f"https://t.me/{chat.username}"
                                        else:
                                            invite = await bot.create_chat_invite_link(chat_id=channel_id)
                                            join_url = invite.invite_link
                                        watch_url = f"https://t.me/c/{str(channel_id)[4:]}/{post_id}"
                                        main_markup = InlineKeyboardMarkup([
                                            [
                                                InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=join_url),
                                            ]
                                        ])
                                        main_post_msg = await bot.send_photo(
                                            Var.MAIN_CHANNEL,
                                            photo=send_photo_arg,
                                            caption=main_caption,
                                            reply_markup=main_markup
                                        )
                                    except Exception as e:
                                        await rep.report(f"Failed to post to main channel: {e}", "error", log=True)
                        else:
                            if main_post_msg is None:
                                main_post_msg = await bot.send_photo(
                                    Var.MAIN_CHANNEL,
                                    photo=send_photo_arg,
                                    caption=main_caption,
                                    reply_markup=InlineKeyboardMarkup(current_btns)
                                )
                            else:
                                await editMessage(main_post_msg, main_caption, InlineKeyboardMarkup(current_btns))

                            post_id = main_post_msg.id
                            if ep_no is not None:
                                await db.save_anime(ani_id, ep_no, qual, post_id)

                    except Exception as e:
                        await rep.report(f"Post/update error: {e}", "error", log=True)

                    # Fire-and-forget backup copy
                    asyncio.create_task(extra_utils(msg_id, out_path))

            finally:
                if ffLock.locked():
                    try:
                        ffLock.release()
                    except Exception:
                        pass

                # mark completed & cleanup
                ani_cache['ongoing'].discard(cache_key)
                ani_cache['completed'].add(cache_key)
                try:
                    await stat_msg.delete()
                except Exception:
                    pass

                try:
                    if dl and ospath.exists(dl):
                        await aioremove(dl)
                except Exception:
                    pass

    except Exception:
        await rep.report(format_exc(), "error", log=True)
        # ensure lock release
        try:
            if ffLock.locked():
                ffLock.release()
        except Exception:
            pass

# ---------------------- EXTRA UTILS (backup copy) ---------------------------
async def extra_utils(msg_id, out_path):
    try:
        msg = await bot.get_messages(Var.FILE_STORE, message_ids=msg_id)
        if Var.BACKUP_CHANNEL:
            for chat in str(Var.BACKUP_CHANNEL).split():
                try:
                    await msg.copy(int(chat))
                except Exception:
                    pass
    except Exception:
        pass

# ---------------------- START THE RSS LOOP ----------------------------------
bot_loop.create_task(fetch_animes())

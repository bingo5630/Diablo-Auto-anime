import asyncio
import os
from asyncio import gather, create_task, sleep as asleep, Event
from os import path as ospath
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath
from traceback import format_exc
from base64 import urlsafe_b64encode
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

# ── CONFIG & CORE ─────────────────────────────────────────────────────────────
from config import Var
from bot.core.bot_instance import bot, bot_loop, ani_cache, ffQueue, ffLock, ff_queued
from .tordownload import TorDownloader
from .database import db                # ← MongoDB helpers (see previous answer)
from .func_utils import getfeed, encode, editMessage, sendMessage, convertBytes
from .text_utils import TextEditor
from .ffencoder import FFEncoder
from .tguploader import TgUploader
from .reporter import rep

# ── BUTTON FORMATTER ───────────────────────────────────────────────────────────
btn_formatter = {
    'HDRip': 'HDRip',
    '1080': '1080P',
    '720': '720P',
    '480': '480P',
    '360': '360P'
}

# ── ENSURE POSTER FOLDER ───────────────────────────────────────────────────────
os.makedirs("./downloads/posters", exist_ok=True)


@bot.on_message(filters.command("getposter") & filters.user(Var.ADMINS))
async def get_anime_poster_handler(client, message):
    try:
        args = message.text.split(None, 1)
        # If no anime name is provided, list all anime with custom posters
        if len(args) < 2:
            poster_list = await db.list_all_anime_posters()
            if not poster_list:
                return await message.reply_text("🤷‍♂️ No anime have a custom poster set.")
            
            text = "🖼️ ᴀɴɪᴍᴇ ᴡɪᴛʜ ᴄᴜꜱᴛᴏᴍ ᴘᴏꜱᴛᴇʀꜱ :\n\n"
            for anime in poster_list:
                text += f"<b>• {anime}\n"
            text += "\nᴛᴏ ꜱᴇᴇ ᴀ ꜱᴘᴇᴄɪꜰɪᴄ ᴘᴏꜱᴛᴇʀ ᴜꜱᴇ /getposter <anime name></b>"
            return await message.reply_text(text)

        # If an anime name is provided, fetch and show that specific poster
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

# ── ADMIN COMMANDS ─────────────────────────────────────────────────────────────
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
    ani_cache["custom_rss"].add(url)
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
        ani_cache["custom_rss"].remove(url)
        await message.reply_text(f"Removed:\n`{url}`")
        await rep.report(f"RSS feed removed: {url}", "info", log=True)
    else:
        await message.reply_text("RSS link not found.")
        await rep.report(f"RSS link not found: {url}", "warning", log=True)


# ── /setchannel  (with optional custom poster) ─────────────────────────────────
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

        # Ensure poster directory
        poster_dir = "./downloads/posters"
        os.makedirs(poster_dir, exist_ok=True)

        custom_poster_path = None
        if message.reply_to_message and message.reply_to_message.photo:
            photo = message.reply_to_message.photo

            # Handle both list and single PhotoSize
            if isinstance(photo, list):
                photo = photo[-1]  # highest resolution
            # Now photo is a single PhotoSize object

            custom_poster_path = f"{poster_dir}/{photo.file_unique_id}.jpg"

            # Skip if already exists
            if ospath.exists(custom_poster_path):
                await rep.report(f"Poster already exists: {custom_poster_path}", "info", log=True)
            else:
                dl_msg = await message.reply_text("Downloading poster...")
                try:
                    await asyncio.wait_for(
                        bot.download_media(
                            message.reply_to_message,
                            file_name=custom_poster_path
                        ),
                        timeout=60
                    )
                    await dl_msg.edit_text("Poster downloaded!")
                    await rep.report(f"Poster saved: {custom_poster_path}", "info", log=True)
                except asyncio.TimeoutError:
                    await dl_msg.edit_text("Download timed out!")
                    await rep.report("Poster download timeout", "error", log=True)
                    return
                except Exception as e:
                    await dl_msg.edit_text(f"Download failed: {e}")
                    await rep.report(f"Poster download error: {e}", "error", log=True)
                    return
                finally:
                    await asleep(1)
                    await dl_msg.delete()

        # ---- Anilist lookup ----
        ani_info = TextEditor(anime_name)
        await ani_info.load_anilist()
        ani_id = ani_info.adata.get('id')
        if not ani_id:
            await message.reply_text(f"Anime not found: `{anime_name}`\nTry exact title from Anilist.")
            await rep.report(f"Anime not found: {anime_name}", "error", log=True)
            return

        # ---- Save mapping ----
        await db.set_anime_channel(ani_id, channel_id, custom_poster_path)

        poster_status = f"Set: `{custom_poster_path}`" if custom_poster_path else "Not set"
        await message.reply_text(
            f"<b>Mapping Saved</b>\n\n"
            f"<b>Anime</b>: <i>{anime_name}</i>\n"
            f"<b>ID</b>: <code>{ani_id}</code>\n"
            f"<b>Channel</b>: <code>{channel_id}</code>\n"
            f"<b>Custom Poster</b>: <i>{poster_status}</i>"
        )
        await rep.report(
            f"Mapped {anime_name} ({ani_id}) → {channel_id} | Poster: {custom_poster_path}",
            "info", log=True
        )

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")
        await rep.report(f"/setchannel error: {format_exc()}", "error", log=True)
        

# ── /removeposter ─────────────────────────────────────────────────────────────
@bot.on_message(filters.command("removeposter") & filters.user(Var.ADMINS))
async def remove_poster(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/removeposter <anime_name>`")
        return
    anime_name = " ".join(message.command[1:])
    ani_info = TextEditor(anime_name)
    await ani_info.load_anilist()
    ani_id = ani_info.adata.get('id')
    if not ani_id:
        await message.reply_text("Anime not found.")
        return

    old = await db.get_custom_poster(ani_id)
    channel = await db.get_anime_channel(ani_id)
    await db.set_anime_channel(ani_id, channel, None)   # remove poster field
    if old and ospath.exists(old):
        await aioremove(old)

    await message.reply_text(f"Custom poster removed for **{anime_name}**")
    await rep.report(f"Poster removed for ani_id {ani_id}", "info", log=True)


# ── /setsticker ───────────────────────────────────────────────────────────────
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


# ── /listchannels ─────────────────────────────────────────────────────────────
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
        poster = m.get("custom_poster")
        mark = " (Custom Poster)" if poster else ""
        try:
            info = TextEditor(f"id:{ani_id}")
            await info.load_anilist()
            name = info.adata.get('title', {}).get('romaji', f"ID:{ani_id}")
        except:
            name = f"ID:{ani_id}"
        txt += f"• <b>{name}</b>{mark} → <code>{channel_id}</code>\n"

    await message.reply_text(txt)
    await rep.report(f"Listed {len(mappings)} mappings", "info", log=True)


# ── RSS FETCHER ───────────────────────────────────────────────────────────────
async def fetch_animes():
    await rep.report("RSS fetch loop started", "info", log=True)
    processed = set()

    async def fetch_feed(link):
        info = await getfeed(link, 0)
        if info and info.link not in processed:
            processed.add(info.link)
            return info
        return None

    while True:
        await asleep(30)
        if not ani_cache.get('fetch_animes', True):
            continue

        all_rss = Var.RSS_ITEMS + list(ani_cache.get("custom_rss", []))

        # Fetch all feeds concurrently
        feed_tasks = [fetch_feed(link) for link in all_rss]
        new_items = await gather(*feed_tasks, return_exceptions=True)

        # Filter out None and exceptions, then create anime processing tasks
        anime_tasks = [
            bot_loop.create_task(get_animes(info.title, info.link))
            for info in new_items
            if info and not isinstance(info, Exception)
        ]

        if anime_tasks:
            await gather(*anime_tasks, return_exceptions=True)


# ── CORE PROCESSING (with custom poster priority) ─────────────────────────────
async def get_animes(name, torrent, force=False):
    try:
        ani_info = TextEditor(name)
        await ani_info.load_anilist()
        ani_id, ep_no = ani_info.adata.get('id'), ani_info.pdata.get("episode_number")
        if not ani_id or not ep_no:
            await rep.report(f"Invalid anime data for {name}: ID or episode number missing", "error", log=True)
            return
        if ani_id not in ani_cache['ongoing']:
            ani_cache['ongoing'].add(ani_id)
        elif not force:
            return
        ani_data = await db.get_anime(ani_id)
        qual_data = ani_data.get(ep_no) if ani_data else None
        if force or not ani_data or not qual_data or not all(qual_data.get(qual) for qual in Var.QUALS):
            if "[Batch]" in name:
                await rep.report(f"Torrent Skipped!\n\n{name}", "warning", log=True)
                return
            await rep.report(f"New Anime Torrent Found!\n\n{name}", "info", log=True)
            anime_name = name
            
            await asleep(1.5)
            stat_msg = await sendMessage(Var.LOG_CHANNEL, f"<blockquote>‣ <b>Aɴɪᴍᴇ Nᴀᴍᴇ :</b> <b><i>{name}</i></b></blockquote>\n\n<blockquote><i>Dᴏᴡɴʟᴏᴀᴅɪɴɢ....</i></blockquote>")
            dl = await TorDownloader("./downloads").download(torrent, name)
            if not dl or not ospath.exists(dl):
                await rep.report(f"File Download Incomplete, Try Again", "error", log=True)
                await stat_msg.delete()
                return
            
            task_id = torrent
            ffEvent = Event()
            ff_queued[task_id] = ffEvent

            if ffLock.locked():
                await editMessage(stat_msg, f"<blockquote>‣ <b>Aɴɪᴍᴇ Nᴀᴍᴇ :</b> <b><i>{name}</i></b></blockquote>\n\n<blockquote><i>Qᴜᴇᴜᴇᴅ ᴛᴏ Eɴᴄᴏᴅᴇ...</i></blockquote>")
                await rep.report("Aᴅᴅᴇᴅ Tᴀsᴋ ᴛᴏ Qᴜᴇᴜᴇ...", "info", log=True)
            await ffQueue.put(task_id)
            await ffEvent.wait()
            await ffLock.acquire()
            
            main_post_msg = None
            specific_post_msg = None
            main_btns = []
            specific_btns = []
            post_id = 0
            
            # === ENCODING & UPLOAD LOOP WITH 3 BUTTONS PER ROW ===
            for qual in Var.QUALS:
                filename = await ani_info.get_upname(qual)
                await editMessage(stat_msg, f"<blockquote>‣ <b>Aɴɪᴍᴇ Nᴀᴍᴇ :</b> <b><i>{name}</i></b></blockquote>\n\n<blockquote><i>Rᴇᴀᴅʏ ᴛᴏ Eɴᴄᴏᴅᴇ...</i></blockquote>")
                await asleep(1.5)
                await rep.report("Sᴛᴀʀᴛɪɴɢ Eɴᴄᴏᴅᴇ...", "info", log=True)
                
                try:
                    out_path = await FFEncoder(stat_msg, dl, filename, qual).start_encode()
                except Exception as e:
                    await rep.report(f"Error: {e}, Cancelled, Retry Again !", "error", log=True)
                    await stat_msg.delete()
                    ffLock.release()
                    return
                
                await rep.report("Sᴜᴄᴄᴇsғᴜʟʟʏ Cᴏᴍᴘʀᴇssᴇᴅ Nᴏᴡ Gᴏɪɴɢ Tᴏ Uᴘʟᴏᴀᴅ...", "info", log=True)
                await editMessage(stat_msg, f"<blockquote>‣ <b>Aɴɪᴍᴇ Nᴀᴍᴇ :</b> <b><i>{filename}</i></b></blockquote>\n\n<blockquote><i>Rᴇᴀᴅʏ ᴛᴏ Uᴘʟᴏᴀᴅ...</i></blockquote>")
                await asleep(1.5)
                
                try:
                    msg = await TgUploader(stat_msg).upload(out_path, qual)
                except Exception as e:
                    await rep.report(f"Error: {e}, Cancelled, Retry Again !", "error", log=True)
                    await stat_msg.delete()
                    ffLock.release()
                    return
                
                if not main_post_msg:
                    photo_url = await ani_info.get_poster()
                    # Try to get the custom poster first
                    anime_title_from_parser = ani_info.pdata.get("anime_title")
                    photo_url = await db.get_anime_poster(anime_title_from_parser)

                    # If no custom poster, fall back to the anilist poster
                    if not photo_url:
                        photo_url = await ani_info.get_poster()
                        
                    specific_channel_id = await db.get_anime_channel(ani_id)
                    main_caption = await ani_info.get_caption()

                    # Send to main channel
                    if photo_url and (await aiopath.isfile(photo_url) or isinstance(photo_url, str)):
                        try:
                            main_post_msg = await bot.send_photo(
                                Var.MAIN_CHANNEL,
                                photo=photo_url,
                                caption=main_caption
                            )
                        except Exception:
                             main_post_msg = await bot.send_photo(
                                Var.MAIN_CHANNEL,
                                photo="https://envs.sh/YsH.jpg",
                                caption=main_caption
                            )
                    else:
                        main_post_msg = await bot.send_photo(
                            Var.MAIN_CHANNEL,
                            photo="https://envs.sh/YsH.jpg",
                            caption=main_caption
                        )
                    post_id = main_post_msg.id

                    # Send to specific channel if mapped
                    if specific_channel_id:
                        try:
                            if photo_url and (await aiopath.isfile(photo_url) or isinstance(photo_url, str)):
                                try:
                                    specific_post_msg = await bot.send_photo(
                                        specific_channel_id,
                                        photo=photo_url,
                                        caption=main_caption
                                    )
                                except Exception:
                                    specific_post_msg = await bot.send_photo(
                                        specific_channel_id,
                                        photo="https://envs.sh/YsH.jpg",
                                        caption=main_caption
                                    )
                            else:
                                specific_post_msg = await bot.send_photo(
                                    specific_channel_id,
                                    photo="https://envs.sh/YsH.jpg",
                                    caption=main_caption
                                )
                        except Exception as e:
                            await rep.report(f"Failed to send to specific channel {specific_channel_id} for {name}: {str(e)}", "error", log=True)

                await rep.report("Sᴜᴄᴄᴇssғᴜʟʟʏ Uᴘʟᴏᴀᴅᴇᴅ Fɪʟᴇ ɪɴᴛᴏ Cʜᴀɴɴᴇʟ...", "info", log=True)
                msg_id = msg.id
                link = f"https://telegram.me/{(await bot.get_me()).username}?start={await encode('get-'+str(msg_id * abs(Var.FILE_STORE)))}"
                
                # === ADD BUTTON: 3 PER ROW ===
                qual_btn = InlineKeyboardButton(f"{btn_formatter[qual]}", url=link)

                if specific_channel_id:
                    # Add to specific channel buttons
                    if not specific_btns or len(specific_btns[-1]) == 3:
                        specific_btns.append([qual_btn])
                    else:
                        specific_btns[-1].append(qual_btn)
                    
                    # Update specific channel post
                    if specific_post_msg:
                        await editMessage(specific_post_msg, specific_post_msg.caption.html if specific_post_msg.caption else "", InlineKeyboardMarkup(specific_btns))
                        # Update main channel "Watch Anime" button
                        if not main_btns:
                            try:
                                channel_invite = await bot.export_chat_invite_link(specific_channel_id)
                                main_btns.append([
                                    InlineKeyboardButton("✨WATCH NOW✨", url=channel_invite),
                                    
                                ])
                            except Exception as e:
                                await rep.report(f"Failed to get invite link for channel {specific_channel_id}: {str(e)}", "warning", log=True)
                        await editMessage(main_post_msg, main_post_msg.caption.html if main_post_msg.caption else "", InlineKeyboardMarkup(main_btns))
                else:
                    # Add to main channel buttons
                    if not main_btns or len(main_btns[-1]) == 3:
                        main_btns.append([qual_btn])
                    else:
                        main_btns[-1].append(qual_btn)
                    
                    # Update main channel post
                    await editMessage(main_post_msg, main_post_msg.caption.html if main_post_msg.caption else "", InlineKeyboardMarkup(main_btns))
                
                await db.save_anime(ani_id, ep_no, qual, post_id)
            
            # === FINAL CLEANUP ===
            sticker_id = await db.get_sticker()
            if sticker_id:
                try:
                    await bot.send_sticker(Var.MAIN_CHANNEL, sticker=sticker_id)
                    await rep.report(f"Sticker {sticker_id} sent to main channel for {name}", "info", log=True)
                    if specific_channel_id and specific_post_msg:
                        await bot.send_sticker(specific_channel_id, sticker=sticker_id)
                        await rep.report(f"Sticker {sticker_id} sent to specific channel {specific_channel_id} for {name}", "info", log=True)
                except Exception as e:
                    await rep.report(f"Failed to send sticker {sticker_id}: {str(e)}", "error", log=True)
            
            ffLock.release()
            await stat_msg.delete()
            await aioremove(dl)
        else:
            await rep.report(f"Anime {name} already processed or completed", "info", log=True)
    except Exception as error:
        await rep.report(f"Error in get_animes for {name}: {format_exc()}", "error", log=True)
    finally:
        if ani_id:
            ani_cache['completed'].add(ani_id)
            


# ── EXTRA UTILS (backup copy) ─────────────────────────────────────────────────
async def extra_utils(msg_id, out_path):
    msg = await bot.get_messages(Var.FILE_STORE, message_ids=msg_id)
    if Var.BACKUP_CHANNEL != 0:
        for chat in str(Var.BACKUP_CHANNEL).split():
            await msg.copy(int(chat))


# ── START THE RSS LOOP (call it once when the bot starts) ─────────────────────
bot_loop.create_task(fetch_animes())

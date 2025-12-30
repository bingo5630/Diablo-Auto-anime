from pyrogram import Client, filters
from pyrogram.errors import ListenerTimeout
from bot.core.bot_instance import bot
from config import Var
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.core.database import *
from bot.Script import botmaker
from .shortner import shortner_panel, get_short
import requests
import random
import string
from config import SHORT_URL, SHORT_API, MESSAGES

shortened_urls_cache = {}
def generate_random_alphanumeric():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(8))

@bot.on_callback_query()
async def cb_handler(client: bot, query: CallbackQuery):
    data = query.data
    if data == "help":
        await query.message.edit_text(
            text=botmaker.HELP_TXT.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                 InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data='close')]
            ])
        )
        
    elif data == "about":
        await query.message.edit_text(
            text=botmaker.ABOUT_TXT.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                 InlineKeyboardButton('ᴄʟᴏꜱᴇ', callback_data='close')]
            ])
        )
        
    elif data == "start":
        await query.message.edit_text(
            text=botmaker.START_MSG.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ʜᴇʟᴘ", callback_data='help'),
                 InlineKeyboardButton("ᴀʙᴏᴜᴛ", callback_data='about')]
            ])
        )
        
    elif data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass
            
    elif data.startswith("rfs_ch_"):
        cid = int(data.split("_")[2])
        try:
            chat = await client.get_chat(cid)
            mode = await db.get_channel_mode(cid)
            status = "🟢 ᴏɴ" if mode == "on" else "🔴 ᴏғғ"
            new_mode = "ᴏғғ" if mode == "on" else "on"
            buttons = [
                [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
                [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
            ]
            await query.message.edit_text(
                f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            await query.answer("Failed to fetch channel info", show_alert=True)
            
    elif data.startswith("rfs_toggle_"):
        cid, action = data.split("_")[2:]
        cid = int(cid)
        mode = "on" if action == "on" else "off"
        await db.set_channel_mode(cid, mode)
        await query.answer(f"Force-Sub set to {'ON' if mode == 'on' else 'OFF'}")
        # Refresh the same channel's mode view
        chat = await client.get_chat(cid)
        status = "🟢 ON" if mode == "on" else "🔴 OFF"
        new_mode = "off" if mode == "on" else "on"
        buttons = [
            [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
            [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
        ]
        await query.message.edit_text(
            f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif data == "shortner":
        await query.answer()
        await shortner_panel(client, query)
        
    elif data == "toggle_shortner":
        # Toggle the shortner status
        current_status = await db.get_shortner_status()
        new_status = not current_status
      
        # Save to database
        await db.set_shortner_status(new_status)
      
        status_text = "ᴇɴᴀʙʟᴇᴅ" if new_status else "ᴅɪsᴀʙʟᴇᴅ"
        await query.answer(f"✓ ꜱʜᴏʀᴛɴᴇʀ {status_text}!")
      
        # Refresh the panel
        await shortner_panel(client, query)
        
    elif data == "add_shortner":
        await query.answer()
          
        settings = await db.get_shortner_settings()
        current_url = settings.get('short_url', SHORT_URL)
        current_api = settings.get('short_api', SHORT_API)
      
        msg = f"""<blockquote>**ꜱᴇᴛ ꜱʜᴏʀᴛɴᴇʀ ꜱᴇᴛᴛɪɴɢꜱ:**</blockquote>
**ᴄᴜʀʀᴇɴᴛ ꜱᴇᴛᴛɪɴɢꜱ:**
• **ᴜʀʟ:** `{current_url}`
• **ᴀᴘɪ:** `{current_api[:20]}...`
__<blockquote>**≡ ꜱᴇɴᴅ ɴᴇᴡ ꜱʜᴏʀᴛɴᴇʀ ᴜʀʟ ᴀɴᴅ ᴀᴘɪ ɪɴ ᴛʜɪꜱ ꜰᴏʀᴍᴀᴛ ɪɴ ᴛʜᴇ ɴᴇxᴛ 60 ꜱᴇᴄᴏɴᴅꜱ!**</blockquote>__
**ꜰᴏʀᴍᴀᴛ:** `ᴜʀʟ ᴀᴘɪ`
**ᴇxᴀᴍᴘʟᴇ:** `inshorturl.com 9435894656863495834957348`"""
      
        await query.message.edit_text(msg)
        try:
            res = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
            response_text = res.text.strip()
          
            # Parse the response: url api
            parts = response_text.split()
            if len(parts) >= 2:
                new_url = parts[0].replace('https://', '').replace('http://', '').replace('/', '')
                new_api = ' '.join(parts[1:]) # Join remaining parts as API key
              
                if new_url and '.' in new_url and new_api and len(new_api) > 10:
                    # Save to database
                    await db.update_shortner_setting('short_url', new_url)
                    await db.update_shortner_setting('short_api', new_api)
                  
                    await query.message.edit_text(f"**✓ ꜱʜᴏʀᴛɴᴇʀ ꜱᴇᴛᴛɪɴɢꜱ ᴜᴘᴅᴀᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**\n\n**ɴᴇᴡ ᴜʀʟ:** `{new_url}`\n**ɴᴇᴡ ᴀᴘɪ:** `{new_api[:20]}...`",
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'shortner')]]))
                else:
                    await query.message.edit_text("**✗ ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ! ᴘʟᴇᴀꜱᴇ ᴄʜᴇᴄᴋ ᴜʀʟ ᴀɴᴅ ᴀᴘɪ ᴋᴇʏ.**",
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'shortner')]]))
            else:
                await query.message.edit_text("**✗ ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ! ᴘʟᴇᴀꜱᴇ ᴜꜱᴇ: `ᴜʀʟ ᴀᴘɪ`**",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'shortner')]]))
        except ListenerTimeout:
            await query.message.edit_text("**⏰ ᴛɪᴍᴇᴏᴜᴛ! ᴛʀʏ ᴀɢᴀɪɴ.**",
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'shortner')]]))
            
    elif data == "set_tutorial_link":
        await query.answer()
          
        settings = await db.get_shortner_settings()
        current_tutorial = settings.get('tutorial_link', "https://t.me/How_to_Download_7x/26")
        msg = f"""<blockquote>**ꜱᴇᴛ ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ:**</blockquote>
**ᴄᴜʀʀᴇɴᴛ ᴛᴜᴛᴏʀɪᴀʟ:** `{current_tutorial}`
__ꜱᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ ɪɴ ᴛʜᴇ ɴᴇxᴛ 60 ꜱᴇᴄᴏɴᴅꜱ!__
**ᴇxᴀᴍᴘʟᴇ:** `https://t.me/How_to_Download_7x/26`"""
      
        await query.message.edit_text(msg)
        try:
            res = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
            new_tutorial = res.text.strip()
          
            if new_tutorial and (new_tutorial.startswith('https://') or new_tutorial.startswith('http://')):
                # Save to database
                await db.update_shortner_setting('tutorial_link', new_tutorial)
                await query.message.edit_text(f"**✓ ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ ᴜᴘᴅᴀᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'shortner')]]))
            else:
                await query.message.edit_text("**✗ ɪɴᴠᴀʟɪᴅ ʟɪɴᴋ ꜰᴏʀᴍᴀᴛ! ᴍᴜꜱᴛ ꜱᴛᴀʀᴛ ᴡɪᴛʜ https:// ᴏʀ http://**",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'shortner')]]))
        except ListenerTimeout:
            await query.message.edit_text("**⏰ ᴛɪᴍᴇᴏᴜᴛ! ᴛʀʏ ᴀɢᴀɪɴ.**",
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'shortner')]]))
            
    elif data == "set_validity":
        await query.answer()
        current_time = await db.get_verification_time()
        # Convert seconds to human readable
        hours = current_time // 3600
        msg = f"""<blockquote>**ꜱᴇᴛ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴠᴀʟɪᴅɪᴛʏ:**</blockquote>
**ᴄᴜʀʀᴇɴᴛ ᴠᴀʟɪᴅɪᴛʏ:** `{hours} Hours`
__ꜱᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ᴠᴀʟɪᴅɪᴛʏ ɪɴ **ʜᴏᴜʀꜱ** ɪɴ ᴛʜᴇ ɴᴇxᴛ 60 ꜱᴇᴄᴏɴᴅꜱ!__
**ᴇxᴀᴍᴘʟᴇ:** `24` ꜰᴏʀ 1 ᴅᴀʏ, `12` ꜰᴏʀ 12 ʜᴏᴜʀꜱ."""
        await query.message.edit_text(msg)
        try:
            res = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
            try:
                new_hours = int(res.text.strip())
                if new_hours > 0:
                    seconds = new_hours * 3600
                    await db.set_verification_time(seconds)
                    await query.message.edit_text(f"**✓ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴠᴀʟɪᴅɪᴛʏ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ {new_hours} ʜᴏᴜʀꜱ!**",
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'shortner')]]))
                else:
                     await query.message.edit_text("**✗ ɪɴᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ! ᴍᴜꜱᴛ ʙᴇ ɢʀᴇᴀᴛᴇʀ ᴛʜᴀɴ 0.**",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'shortner')]]))
            except ValueError:
                await query.message.edit_text("**✗ ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ! ᴘʟᴇᴀꜱᴇ ꜱᴇɴᴅ ᴀ ɴᴜᴍʙᴇʀ.**",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'shortner')]]))
        except ListenerTimeout:
            await query.message.edit_text("**⏰ ᴛɪᴍᴇᴏᴜᴛ! ᴛʀʏ ᴀɢᴀɪɴ.**",
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'shortner')]]))
            
    elif data == "test_shortner":
        await query.answer()
          
        await query.message.edit_text("**🔄 ᴛᴇꜱᴛɪɴɢ ꜱʜᴏʀᴛɴᴇʀ...**")
      
        settings = await db.get_shortner_settings()
        short_url = settings.get('short_url', SHORT_URL)
        short_api = settings.get('short_api', SHORT_API)
      
        try:
            test_url = "https://google.com"
            alias = generate_random_alphanumeric()
            api_url = f"https://{short_url}/api?api={short_api}&url={test_url}&alias={alias}"
          
            response = requests.get(api_url, timeout=10)
            rjson = response.json()
          
            if rjson.get("status") == "success" and response.status_code == 200:
                short_link = rjson.get("shortenedUrl", "")
                msg = f"""**✅ ꜱʜᴏʀᴛɴᴇʀ ᴛᴇꜱᴛ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟ!**
**ᴛᴇꜱᴛ ᴜʀʟ:** `{test_url}`
**ꜱʜᴏʀᴛ ᴜʀʟ:** `{short_link}`
**ʀᴇꜱᴘᴏɴꜱᴇ:** `{rjson.get('status', 'Unknown')}`"""
            else:
                msg = f"""**❌ ꜱʜᴏʀᴛɴᴇʀ ᴛᴇꜱᴛ ꜰᴀɪʟᴇᴅ!**
**ᴇʀʀᴏʀ:** `{rjson.get('message', 'Unknown error')}`
**ꜱᴛᴀᴛᴜꜱ ᴄᴏᴅᴇ:** `{response.status_code}`"""
              
        except Exception as e:
            msg = f"**❌ ꜱʜᴏʀᴛɴᴇʀ ᴛᴇꜱᴛ ꜰᴀɪʟᴇᴅ!**\n\n**ᴇʀʀᴏʀ:** `{str(e)}`"
      
        await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'shortner')]]))
        
    elif data == "fsub_back":
        channels = await db.show_channels()
        buttons = []
        for cid in channels:
            try:
                chat = await client.get_chat(cid)
                mode = await db.get_channel_mode(cid)
                status = "🟢" if mode == "on" else "🔴"
                buttons.append([InlineKeyboardButton(f"{status} {chat.title}", callback_data=f"rfs_ch_{cid}")])
            except:
                continue
        await query.message.edit_text(
            "sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ɪᴛs ғᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

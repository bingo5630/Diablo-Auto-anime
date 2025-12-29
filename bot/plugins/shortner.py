import requests
import random
import string
from config import SHORT_URL, SHORT_API, MESSAGES
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram.errors.pyromod import ListenerTimeout
from bot.core.database import db
from bot.core.func_utils import sync_to_async
# ✅ In-memory cache
shortened_urls_cache = {}
def generate_random_alphanumeric():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(8))
    
async def get_short(url, client):
    # Check if shortner is enabled (fetch from DB or use default)
    # Using cached settings might be better, but we need to ensure cache invalidation.
    # For now, let's just fetch to ensure correctness, assuming low load or fast DB.
    # Or, rely on client attributes being updated.
    settings = await db.get_shortner_settings()
    shortner_enabled = settings.get('enabled', True)
    if not shortner_enabled:
        return url # Return original URL if shortner is disabled
    # Step 2: Check cache
    if url in shortened_urls_cache:
        return shortened_urls_cache[url]
    try:
        alias = generate_random_alphanumeric()
        # Use settings from DB
        short_url = settings.get('short_url', SHORT_URL)
        short_api = settings.get('short_api', SHORT_API)
       
        api_url = f"https://{short_url}/api?api={short_api}&url={url}&alias={alias}"
        # Use sync_to_async to prevent blocking
        response = await sync_to_async(requests.get, api_url)
        rjson = response.json()
        if rjson.get("status") == "success" and response.status_code == 200:
            short_url = rjson.get("shortenedUrl", url)
            shortened_urls_cache[url] = short_url
            return short_url
    except Exception as e:
        print(f"[Shortener Error] {e}")
    return url # fallback
#===============================================================#
@Client.on_message(filters.command('shortner') & filters.private)
async def shortner_command(client: Client, message: Message):
    await shortner_panel(client, message)
#===============================================================#
async def shortner_panel(client, query_or_message):
    # Get current shortner settings from DB
    settings = await db.get_shortner_settings()
    short_url = settings.get('short_url', SHORT_URL)
    short_api = settings.get('short_api', SHORT_API)
    tutorial_link = settings.get('tutorial_link', "https://t.me/How_to_Download_7x/26")
    shortner_enabled = settings.get('enabled', True)
    verification_time = settings.get('verification_time', 86400)
   
    # Check if shortner is working (only if enabled)
    if shortner_enabled:
        try:
            test_response = requests.get(f"https://{short_url}/api?api={short_api}&url=https://google.com&alias=test", timeout=5)
            status = "✓ ᴡᴏʀᴋɪɴɢ" if test_response.status_code == 200 else "✗ ɴᴏᴛ ᴡᴏʀᴋɪɴɢ"
        except:
            status = "✗ ɴᴏᴛ ᴡᴏʀᴋɪɴɢ"
    else:
        status = "✗ ᴅɪsᴀʙʟᴇᴅ"
   
    enabled_text = "✓ ᴇɴᴀʙʟᴇᴅ" if shortner_enabled else "✗ ᴅɪsᴀʙʟᴇᴅ"
    toggle_text = "✗ ᴏғғ" if shortner_enabled else "✓ ᴏɴ"
   
    # Format verification time
    hours = verification_time // 3600
    if hours >= 24:
        days = hours / 24
        validity_text = f"{days:.1f} Days" if days % 1 != 0 else f"{int(days)} Days"
    else:
        validity_text = f"{hours} Hours"
    msg = f"""<blockquote>✦ 𝗦𝗛𝗢𝗥𝗧𝗡𝗘𝗥 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦</blockquote>
**<u>ᴄᴜʀʀᴇɴᴛ ꜱᴇᴛᴛɪɴɢꜱ:</u>**
<blockquote>›› **ꜱʜᴏʀᴛɴᴇʀ ꜱᴛᴀᴛᴜꜱ:** {enabled_text}
›› **ꜱʜᴏʀᴛɴᴇʀ ᴜʀʟ:** `{short_url}`
›› **ꜱʜᴏʀᴛɴᴇʀ ᴀᴘɪ:** `{short_api}`</blockquote>
<blockquote>›› **ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ:** `{tutorial_link}`
›› **ᴀᴘɪ ꜱᴛᴀᴛᴜꜱ:** {status}
›› **ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴠᴀʟɪᴅɪᴛʏ:** {validity_text}</blockquote>
<blockquote>**≡ ᴜꜱᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴꜱ ʙᴇʟᴏᴡ ᴛᴏ ᴄᴏɴꜰɪɢᴜʀᴇ ʏᴏᴜʀ ꜱʜᴏʀᴛɴᴇʀ ꜱᴇᴛᴛɪɴɢꜱ!**</blockquote>"""
   
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(f'• {toggle_text} ꜱʜᴏʀᴛɴᴇʀ •', 'toggle_shortner'), InlineKeyboardButton('• ᴀᴅᴅ ꜱʜᴏʀᴛɴᴇʀ •', 'add_shortner')],
        [InlineKeyboardButton('• ꜱᴇᴛ ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ •', 'set_tutorial_link')],
        [InlineKeyboardButton('• ꜱᴇᴛ ᴠᴀʟɪᴅɪᴛʏ •', 'set_validity')],
        [InlineKeyboardButton('• ᴛᴇꜱᴛ ꜱʜᴏʀᴛɴᴇʀ •', 'test_shortner')],
        [InlineKeyboardButton('◂ ʙᴀᴄᴋ ᴛᴏ ꜱᴇᴛᴛɪɴɢꜱ', 'settings')] if hasattr(query_or_message, 'message') else []
    ])
   
    image_url = MESSAGES.get("SHORT", "https://telegra.ph/file/8aaf4df8c138c6685dcee-05d3b183d4978ec347.jpg")
   
    if hasattr(query_or_message, 'message'):
        await query_or_message.message.edit_media(
            media=InputMediaPhoto(media=image_url, caption=msg),
            reply_markup=reply_markup
        )
    else:
        await query_or_message.reply_photo(photo=image_url, caption=msg, reply_markup=reply_markup)
#===============================================================#

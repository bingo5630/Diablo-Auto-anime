import os

class botmaker(object):
    START_MSG = """<b>Bᴀᴋᴀᴀᴀ!!!....{first}\n\n<blockquote>ɪ ᴀᴍ ғɪʟᴇ sᴛᴏʀᴇ + Aᴜᴛᴏ Aɴɪᴍᴇ ʙᴏᴛ, ɪ ᴄᴀɴ sᴛᴏʀᴇ ᴘʀɪᴠᴀᴛᴇ ғɪʟᴇs ɪɴ sᴘᴇᴄɪғɪᴇᴅ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴏᴛʜᴇʀ ᴜsᴇʀs ᴄᴀɴ ᴀᴄᴄᴇss ɪᴛ ғʀᴏᴍ sᴘᴇᴄɪᴀʟ ʟɪɴᴋ.</blockquote></b>"""

    FORCE_MSG = """ʜᴇʟʟᴏ {first}\n\n<b>ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ ᴛʜᴇɴ ᴄʟɪᴄᴋ ᴏɴ ʀᴇʟᴏᴀᴅ button ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛᴇᴅ ꜰɪʟᴇ.</b>"""

    HELP_TXT = """<b><blockquote>ᴛʜɪs ɪs ᴀɴ ғɪʟᴇ ᴛᴏ ʟɪɴᴋ ʙᴏᴛ ᴡᴏʀᴋɪɴɢ ғᴏʀ @Anime_Fury

❏ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅs
├ /start : sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ
├ /about : ᴏᴜʀ Iɴғᴏʀᴍᴀᴛɪᴏɴ
└ /help : ʜᴇʟᴘ ʀᴇʟᴀᴛᴇᴅ ʙᴏᴛ

sɪᴍᴘʟʏ ᴄʟɪᴄᴋ ᴏɴ ʟɪɴᴋ ᴀɴᴅ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ, ᴊᴏɪɴ ʙᴏᴛʜ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ — ᴛʜᴀᴛ'ꜱ ɪᴛ.....!</blockquote></b>"""

    ABOUT_TXT = """<b><blockquote>
◈ ᴄʀᴇᴀᴛᴏʀ: <a href="https://t.me/DoraShin_hlo">➳≛⃝Gojo</a>
◈ ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ: <a href="https://t.me/Anime_Fury">𝐀ɴɪᴍᴇ 𝐅ᴜʀʏ</a>
◈ 𝐇ᴇɴᴛᴀɪ 𝐂ʜᴀɴɴᴇʟ: <a href="https://t.me/Adult_Fury">𝐀ᴅᴜʟᴛ 𝐅ᴜʀʏ</a>
</blockquote></b>"""

    CMD_TXT = """<blockquote><b>» ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs:</b></blockquote>

<b>›› /dlt_time :</b> sᴇᴛ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ  
<b>›› /check_dlt_time :</b> ᴄʜᴇᴄᴋ ᴄᴜʀʀᴇɴᴛ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ  
<b>›› /dbroadcast :</b> ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴏᴄᴜᴍᴇɴᴛ / ᴠɪᴅᴇᴏ  
<b>›› /ban :</b> ʙᴀɴ ᴀ ᴜꜱᴇʀ  
<b>›› /unban :</b> ᴜɴʙᴀɴ ᴀ ᴜꜱᴇʀ  
<b>›› /banlist :</b> ɢᴇᴛ ʟɪsᴛ ᴏꜰ ʙᴀɴɴᴇᴅ ᴜꜱᴇʀs  
<b>›› /addchnl :</b> ᴀᴅᴅ ꜰᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ  
<b>›› /delchnl :</b> ʀᴇᴍᴏᴠᴇ ꜰᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ  
<b>›› /listchnl :</b> ᴠɪᴇᴡ ᴀᴅᴅᴇᴅ ᴄʜᴀɴɴᴇʟs  
<b>›› /fsub_mode :</b> ᴛᴏɢɢʟᴇ ꜰᴏʀᴄᴇ sᴜʙ ᴍᴏᴅᴇ  
<b>›› /pbroadcast :</b> sᴇɴᴅ ᴘʜᴏᴛᴏ ᴛᴏ ᴀʟʟ ᴜꜱᴇʀs  
<b>›› /add_admin :</b> ᴀᴅᴅ ᴀɴ ᴀᴅᴍɪɴ  
<b>›› /deladmin :</b> ʀᴇᴍᴏᴠᴇ ᴀɴ ᴀᴅᴍɪɴ  
<b>›› /admins :</b> ɢᴇᴛ ʟɪsᴛ ᴏꜰ ᴀᴅᴍɪɴs
"""

    BOT_STATS_TEXT = "<b>BOT UPTIME</b>\n{uptime}"

    # ✅ Custom Caption from environment
    CUSTOM_CAPTION = os.getenv("CUSTOM_CAPTION", None)

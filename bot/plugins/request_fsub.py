import asyncio
import logging
import os
import random
import sys
import time
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction, ChatMemberStatus, ChatType
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatMemberUpdated, ChatPermissions, ChatJoinRequest
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, InviteHashEmpty, ChatAdminRequired, PeerIdInvalid, UserIsBlocked, InputUserDeactivated
from bot.core.bot_instance import bot
from config import Var
from helper_func import *
from bot.core.database import *

logger = logging.getLogger(__name__)

# Request force-sub mode command
@bot.on_message(filters.command('fsub_mode') & filters.private & admin)
async def change_force_sub_mode(client: Client, message: Message):
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>", quote=True)
    channels = await db.show_channels()

    if not channels:
        return await temp.edit("<b>❌ No force-sub channels found.</b>")

    buttons = []
    for ch_id in channels:
        try:
            chat = await client.get_chat(ch_id)
            mode = await db.get_channel_mode(ch_id)
            status = "🟢" if mode == "on" else "🔴"
            title = f"{status} {chat.title}"
            buttons.append([InlineKeyboardButton(title, callback_data=f"rfs_ch_{ch_id}")])
        except Exception as e:
            logger.error(f"Error fetching chat {ch_id}: {e}")
            buttons.append([InlineKeyboardButton(f"⚠️ {ch_id} (Unavailable)", callback_data=f"rfs_ch_{ch_id}")])

    buttons.append([InlineKeyboardButton("Close ✖️", callback_data="close")])

    await temp.edit(
        "<b>⚡ Select a channel to toggle Force-Sub Mode:</b>",
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )

# This handler captures membership updates (like when a user leaves or is banned)
@bot.on_chat_member_updated()
async def handle_Chatmembers(client: Client, chat_member_updated: ChatMemberUpdated):    
    chat_id = chat_member_updated.chat.id

    if await db.reqChannel_exist(chat_id):
        old_member = chat_member_updated.old_chat_member

        if not old_member:
            return

        if old_member.status == ChatMemberStatus.MEMBER:
            user_id = old_member.user.id

            if await db.req_user_exist(chat_id, user_id):
                await db.del_req_user(chat_id, user_id)
                logger.info(f"Removed user {user_id} from request list for channel {chat_id}")

# This handler captures join requests to the channel/group where the bot is an admin
@bot.on_chat_join_request()
async def handle_join_request(client: Client, chat_join_request: ChatJoinRequest):
    chat_id = chat_join_request.chat.id
    user_id = chat_join_request.from_user.id

    logger.debug(f"[JOIN REQUEST] User {user_id} sent join request to {chat_id}")

    # Check if the channel exists in the force-sub list
    channel_exists = await db.reqChannel_exist(chat_id)
    logger.debug(f"Channel {chat_id} exists in the database: {channel_exists}")

    if channel_exists:
        if not await db.req_user_exist(chat_id, user_id):
            await db.req_user(chat_id, user_id)
            logger.info(f"Added user {user_id} to request list for channel {chat_id}")

# Add channel
@bot.on_message(filters.command('addchnl') & filters.private & admin)
async def add_force_sub(client: Client, message: Message):
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>", quote=True)
    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        return await temp.edit(
            "<b>Usage:</b> <code>/addchnl -100XXXXXXXXXX</code>\n<b>Add only one channel at a time.</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close ✖️", callback_data="close")]])
        )

    try:
        channel_id = int(args[1])
    except ValueError:
        return await temp.edit("<b>❌ Invalid Channel ID!</b>")

    all_channels = await db.show_channels()
    channel_ids_only = [cid if isinstance(cid, int) else cid[0] for cid in all_channels]
    if channel_id in channel_ids_only:
        return await temp.edit(f"<b>Channel already exists:</b> <code>{channel_id}</code>")

    try:
        chat = await client.get_chat(channel_id)

        if chat.type != ChatType.CHANNEL:
            return await temp.edit("<b>❌ Only public or private channels are allowed.</b>")

        member = await client.get_chat_member(chat.id, "me")
        logger.debug(f"Bot status: {member.status} in chat: {chat.title} ({chat.id})")

        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await temp.edit("<b>❌ Bot must be an admin in that channel.</b>")

        # Get invite link
        try:
            link = await client.export_chat_invite_link(chat.id)
        except Exception:
            link = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(chat.id)[4:]}"

        await db.add_channel(channel_id)
        return await temp.edit(
            f"<blockquote><b>✅ Force-sub channel added successfully!</b></blockquote>\n\n"
            f"<blockquote><b>Name:</b> <a href='{link}'>{chat.title}</a>\n"
            f"<b>ID:</b> <code>{channel_id}</code></blockquote>",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Failed to add channel {channel_id}: {e}")
        return await temp.edit(
            f"<b>❌ Failed to add channel:</b>\n<code>{channel_id}</code>\n\n<i>{e}</i>"
        )

# Delete channel
@bot.on_message(filters.command('delchnl') & filters.private & admin)
async def del_force_sub(client: Client, message: Message):
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>", quote=True)
    args = message.text.split(maxsplit=1)
    all_channels = await db.show_channels()

    if len(args) != 2:
        return await temp.edit("<b>Usage:</b> <code>/delchnl <channel_id | all></code>")

    if args[1].lower() == "all":
        if not all_channels:
            return await temp.edit("<b>❌ No force-sub channels found.</b>")
        for ch_id in all_channels:
            await db.rem_channel(ch_id)
            logger.info(f"Removed channel {ch_id} from force-sub list")
        return await temp.edit("<b>✅ All force-sub channels have been removed.</b>")

    try:
        ch_id = int(args[1])
    except ValueError:
        return await temp.edit("<b>❌ Invalid Channel ID</b>")

    if ch_id in all_channels:
        await db.rem_channel(ch_id)
        logger.info(f"Removed channel {ch_id} from force-sub list")
        return await temp.edit(f"<b>✅ Channel removed:</b> <code>{ch_id}</code>")
    else:
        return await temp.edit(f"<b>❌ Channel not found in force-sub list:</b> <code>{ch_id}</code>")

# View all channels
@bot.on_message(filters.command('listchnl') & filters.private & admin)
async def list_force_sub_channels(client: Client, message: Message):
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>", quote=True)
    channels = await db.show_channels()

    if not channels:
        return await temp.edit("<b>❌ No force-sub channels found.</b>")

    result = "<blockquote><b>⚡ Force-sub Channels:</b></blockquote>\n\n"
    for ch_id in channels:
        try:
            chat = await client.get_chat(ch_id)
            link = chat.invite_link or await client.export_chat_invite_link(chat.id)
            result += f"<b>•<blockquote></b> <a href='{link}'>{chat.title}</a> [<code>{ch_id}</code>]</blockquote>\n"
        except Exception as e:
            logger.error(f"Error fetching chat {ch_id}: {e}")
            result += f"<b>•</b> <code>{ch_id}</code> — <i>Unavailable</i>\n"

    await temp.edit(
        result,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close ✖️", callback_data="close")]])
    )

# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport
#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.

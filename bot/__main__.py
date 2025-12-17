# (©)CodeFlix_Bots
# rohit_1888 on Tg #Dont remove this line

from asyncio import create_task, create_subprocess_exec, create_subprocess_shell, run as asyrun, all_tasks, gather, sleep as asleep
from aiofiles import open as aiopen
from pyrogram import idle
from pyrogram.filters import command, user
from os import path as ospath, execl, kill
from sys import executable
from signal import SIGKILL
import logging

from bot.core.bot_instance import bot, bot_loop, sch, ffQueue, ffLock, ffpids_cache, ff_queued
from bot.core.reporter import rep
from config import Var, LOGS
from bot.core.auto_animes import fetch_animes
from bot.core.func_utils import clean_up, new_task, editMessage
from bot.plugins.up_posts import upcoming_animes
from pyrogram import utils

def get_peer_type_new(peer_id: int) -> str:
    peer_id_str = str(peer_id)
    if not peer_id_str.startswith("-"):
        return "user"
    elif peer_id_str.startswith("-100"):
        return "channel"
    else:
        return "chat"

utils.get_peer_type = get_peer_type_new
# Set bot.rep for use in the application
bot.rep = rep

@bot.on_message(command('restart') & user(Var.ADMINS))
@new_task
async def restart(client, message):
    rmessage = await message.reply('<i>Restarting...</i>')
    if sch.running:
        sch.shutdown(wait=False)
    await clean_up()
    if len(ffpids_cache) != 0:
        for pid in ffpids_cache:
            try:
                kill(pid, SIGKILL)
            except (OSError, ProcessLookupError):
                continue
    await (await create_subprocess_exec('python3', 'update.py')).wait()
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{rmessage.chat.id}\n{rmessage.id}\n")
    execl(executable, executable, "-m", "bot")

async def restart_bot():
    if ospath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            lines = f.readlines()
            chat_id, msg_id = map(int, lines)
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="<i>Restarted!</i>")
        except Exception as e:
            LOGS.error(e)

async def queue_loop():
    LOGS.info("Queue Loop Started !!")
    while True:
        if not ffQueue.empty():
            post_id = await ffQueue.get()
            await asleep(1.5)
            ff_queued[post_id].set()
            await asleep(1.5)
            async with ffLock:
                ffQueue.task_done()
        await asleep(10)

async def main():
    sch.add_job(upcoming_animes, "cron", hour=0, minute=30)
    await bot.start()

 # Set bot username
    try:
        me = await bot.get_me()
        bot.username = me.username  # Set bot.username to the bot's Telegram username (e.g., @AutoAniAdvance)
        LOGS.info(f"Bot username set to {bot.username}")
    except Exception as e:
        LOGS.error(f"Failed to set bot username: {str(e)}")
        await bot.stop()
        return
   

    await restart_bot()
    LOGS.info('Auto Anime Bot Started!')

    try:
        db_channel = await bot.get_chat(Var.CHANNEL_ID)
        test_msg = await bot.send_message(chat_id=db_channel.id, text="✅ Startup Test")
        await test_msg.delete()
        bot.db_channel = db_channel
    except Exception as e:
        await bot.rep.report(f"❌ CHANNEL_ID error: {e}", "critical")
        await bot.stop()
        return

    try:
        await bot.send_message(Var.ADMINS, "<b><blockquote>✅ Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ</blockquote></b>")
    except:
        pass


    sch.start()
    bot_loop.create_task(queue_loop())
    await fetch_animes()
    await idle()
    LOGS.info('Auto Anime Bot Stopped!')
    await bot.stop()
    for task in all_tasks():
        task.cancel()
    await clean_up()
    LOGS.info('Finished AutoCleanUp !!')

if __name__ == '__main__':
    bot_loop.run_until_complete(main())

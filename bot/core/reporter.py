
import os   # 👈 Add this
from asyncio import sleep as asleep
from pyrogram.errors import FloodWait
from config import Var, LOGS
from bot.core.bot_instance import bot

class Reporter:
    def __init__(self, client, chat_id, logger):
        self.__client = client
        self.__cid = chat_id
        self.__logger = logger

    async def report(self, msg: str, log_type: str = "info", log: bool = True):
        text = f"[{log_type.upper()}] {msg}"
        if log_type == "error":
            self.__logger.error(text)
        elif log_type == "warning":
            self.__logger.warning(text)
        elif log_type == "critical":
            self.__logger.critical(text)
        else:
            self.__logger.info(text)
        if log and self.__cid != 0 and log_type in ["error", "critical"]:
            try:
                await self.__client.send_message(self.__cid, text[:4096])
            except FloodWait as f:
                self.__logger.warning(f"FloodWait: sleeping {f.value}s")
                await asleep(f.value * 1.5)
            except Exception as err:
                self.__logger.error(f"Reporter Exception: {err}")

rep = Reporter(bot, Var.LOG_CHANNEL, LOGS)

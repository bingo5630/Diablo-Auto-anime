import asyncio
import time
from os import path as ospath
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, remove as aioremove
from aiohttp import ClientSession
from torrentp import TorrentDownloader
from config import LOGS
from bot.core.func_utils import handle_logs
from pathlib import Path


class TorDownloader:
    def __init__(self, path="downloads"):
        self._downdir = path
        self._torpath = "torrents"

    @handle_logs
    async def download(self, torrent: str, name: str = None) -> str | None:
        # Ensure download directory exists
        if not await aiopath.isdir(self._downdir):
            await asyncio.to_thread(Path(self._downdir).mkdir, parents=True, exist_ok=True)

        if torrent.startswith("magnet:"):
            return await self._monitored_download("magnet", torrent, name)
        elif torfile := await self._get_torfile(torrent):
            return await self._monitored_download("file", torfile, name)
        else:
            LOGS.error("[TorDownloader] Invalid torrent or failed to fetch.")
            return None

    async def _monitored_download(self, mode: str, data: str, name: str = None) -> str | None:
        try:
            torp = await asyncio.to_thread(TorrentDownloader, data, self._downdir)
            task = asyncio.create_task(torp.start_download())

            last_checked = time.time()
            max_idle = 600  # 10 minutes
            check_interval = 30

            while not task.done():
                await asyncio.sleep(check_interval)

                # NOTE: Adjust this if torrentp supports a better way to track progress.
                if hasattr(torp, 'progress') and torp.progress < 1:
                    if time.time() - last_checked > max_idle:
                        task.cancel()
                        LOGS.error("[TorDownloader] Dead torrent — no progress for 10 mins.")
                        return None
                else:
                    last_checked = time.time()

            await task
            return ospath.join(self._downdir, name or torp._torrent_info._info.name())
        except asyncio.CancelledError:
            LOGS.warning("[TorDownloader] Download cancelled due to inactivity.")
            return None
        except Exception as e:
            LOGS.error(f"[TorDownloader] Monitored download failed: {e}")
            return None

    @handle_logs
    async def _get_torfile(self, url: str) -> str | None:
        if not await aiopath.isdir(self._torpath):
            await asyncio.to_thread(Path(self._torpath).mkdir, parents=True, exist_ok=True)

        tor_name = url.split("/")[-1]
        save_path = ospath.join(self._torpath, tor_name)

        try:
            async with ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        async with aiopen(save_path, "wb") as f:
                            async for chunk in resp.content.iter_any():
                                await f.write(chunk)
                        return save_path
                    else:
                        LOGS.error(f"[TorDownloader] Failed to download torrent file, status: {resp.status}")
        except Exception as e:
            LOGS.error(f"[TorDownloader] Error fetching .torrent file: {e}")

        return None

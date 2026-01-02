import asyncio
import time
import multiprocessing
import traceback
import math
from os import path as ospath
from aiofiles.os import path as aiopath
from pathlib import Path
from config import LOGS
from bot.core.func_utils import handle_logs
from torrentp import TorrentDownloader

# Worker function to run in a separate process
def download_worker(torrent_url, download_dir, result_queue):
    """
    Worker process to handle torrent downloading.
    It runs an asyncio loop internally to manage the torrentp download.
    """
    async def _runner():
        try:
            # Initialize TorrentDownloader
            torp = TorrentDownloader(torrent_url, download_dir)

            # Start download
            task = asyncio.create_task(torp.start_download())

            # Monitor loop
            last_progress = 0
            last_change_time = time.time()
            max_idle = 1500  # 25 minutes

            while not task.done():
                await asyncio.sleep(5) # Check every 5 seconds for updates

                # Access internal downloader to check status/progress
                if hasattr(torp, '_downloader') and torp._downloader:
                    status = torp._downloader.status()
                    prog = status.progress

                    # Send progress update
                    # Calculate speed, eta, etc. if available from status
                    # libtorrent status object usually has:
                    # progress (0-1), download_rate (bytes/s), upload_rate (bytes/s),
                    # num_peers, state (str), total_wanted (bytes), total_done (bytes)

                    progress_data = {
                        "progress": prog,
                        "download_rate": status.download_rate,
                        "upload_rate": status.upload_rate,
                        "peers": status.num_peers,
                        "state": str(status.state),
                        "total_wanted": status.total_wanted,
                        "total_done": status.total_done
                    }
                    result_queue.put({"progress": progress_data})

                    if prog < 1.0:
                        if prog <= last_progress:
                             if time.time() - last_change_time > max_idle:
                                  task.cancel()
                                  result_queue.put({"error": "Dead torrent - no progress for 10 mins"})
                                  return
                        else:
                             last_progress = prog
                             last_change_time = time.time()

            await task

            # Get the final file name
            name = torp._downloader.name
            full_path = ospath.join(download_dir, name)

            result_queue.put({"path": full_path})

        except asyncio.CancelledError:
            result_queue.put({"error": "Download cancelled"})
        except RuntimeError as e:
            if "bdecode" in str(e):
                result_queue.put({"error": "Download failed: Invalid torrent file (bdecode error). The source might be returning a webpage instead of a .torrent file."})
            else:
                 result_queue.put({"error": f"Download failed: {e}\n{traceback.format_exc()}"})
        except Exception as e:
            result_queue.put({"error": f"Download failed: {e}\n{traceback.format_exc()}"})

    try:
        asyncio.run(_runner())
    except Exception as e:
        result_queue.put({"error": f"Worker process crash: {e}"})

class TorDownloader:
    def __init__(self, path="downloads"):
        self._downdir = path
        self._torpath = "torrents"

    @handle_logs
    async def download(self, torrent: str, name: str = None, progress_callback=None, *args, **kwargs) -> str | None:
        # Ensure download directory exists
        if not await aiopath.isdir(self._downdir):
            await asyncio.to_thread(Path(self._downdir).mkdir, parents=True, exist_ok=True)

        if torrent.startswith("magnet:"):
            return await self._process_download(torrent, progress_callback)
        elif torfile := await self._get_torfile(torrent):
             # For file based, we pass the file path to torrentp
            return await self._process_download(torfile, progress_callback)
        else:
            LOGS.error("[TorDownloader] Invalid torrent or failed to fetch.")
            return None

    async def _process_download(self, data: str, progress_callback=None) -> str | None:
        queue = multiprocessing.Queue()

        # Start the worker process
        p = multiprocessing.Process(target=download_worker, args=(data, self._downdir, queue))
        p.start()

        # Wait for result asynchronously
        while p.is_alive():
            await asyncio.sleep(2)
            while not queue.empty():
                result = queue.get()

                if "progress" in result and progress_callback:
                    await progress_callback(result["progress"])
                elif "error" in result:
                    p.join()
                    LOGS.error(f"[TorDownloader] {result['error']}")
                    return None
                elif "path" in result:
                    p.join()
                    return result["path"]

        # Check if process finished and left something in queue
        while not queue.empty():
            result = queue.get()
            if "path" in result:
                return result["path"]
            elif "error" in result:
                LOGS.error(f"[TorDownloader] {result['error']}")
                return None

        LOGS.error("[TorDownloader] Process finished without result.")
        return None

    @handle_logs
    async def _get_torfile(self, url: str) -> str | None:
        if not await aiopath.isdir(self._torpath):
            await asyncio.to_thread(Path(self._torpath).mkdir, parents=True, exist_ok=True)

        tor_name = url.split("/")[-1]
        save_path = ospath.join(self._torpath, tor_name)

        try:
            from aiohttp import ClientSession
            from aiofiles import open as aiopen

            async with ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get("Content-Type", "").lower()
                        if "html" in content_type:
                            LOGS.error(f"[TorDownloader] Failed to download torrent file: Content-Type is {content_type} (likely HTML).")
                            return None

                        # Read content to check for bencoded signature
                        content = await resp.read()
                        if not content:
                            LOGS.error("[TorDownloader] Failed to download torrent file: Empty response.")
                            return None

                        # Basic check for bencoded dictionary 'd' or simply check if it starts with '<'
                        if content.strip().startswith(b"<"):
                             LOGS.error(f"[TorDownloader] Failed to download torrent file: Content seems to be HTML.")
                             return None

                        async with aiopen(save_path, "wb") as f:
                            await f.write(content)
                        return save_path
                    else:
                        LOGS.error(f"[TorDownloader] Failed to download torrent file, status: {resp.status}")
        except Exception as e:
            LOGS.error(f"[TorDownloader] Error fetching .torrent file: {e}")

        return None

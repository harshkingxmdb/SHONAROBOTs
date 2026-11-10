# Copyright (c) 2025 @THECDERQUEEN
# Licensed under the MIT License.
# This file is part of @SHONA_BOTS
#SHONA-DECODER

import asyncio
import os
import time

from AloneX.music import logger, queue

DOWNLOAD_DIR = "downloads"
CLEANUP_INTERVAL = 3 * 60 * 60   # run every 3 hours
MAX_FILE_AGE = 2 * 60 * 60       # delete cached files untouched for 2+ hours


def _protected_files() -> set[str]:
    """File paths currently sitting in any chat's queue (playing or
    queued-up) — never touched, no matter how old they are."""
    protected = set()
    for items in queue.queues.values():
        for item in items:
            path = getattr(item, "file_path", None)
            if path:
                protected.add(os.path.abspath(path))
    return protected


async def cleanup_downloads_loop() -> None:
    """Runs forever in the background. Periodically deletes old cached
    downloads so disk usage doesn't grow unbounded over a long uptime —
    no more manual /restart needed just to reclaim disk space. Never
    touches a file that's currently queued/playing in any chat."""
    while True:
        try:
            if os.path.isdir(DOWNLOAD_DIR):
                protected = _protected_files()
                now = time.time()
                removed = 0
                freed = 0

                for name in os.listdir(DOWNLOAD_DIR):
                    path = os.path.join(DOWNLOAD_DIR, name)
                    if os.path.abspath(path) in protected:
                        continue
                    try:
                        if not os.path.isfile(path):
                            continue
                        age = now - os.path.getmtime(path)
                        if age < MAX_FILE_AGE:
                            continue
                        size = os.path.getsize(path)
                        os.remove(path)
                        removed += 1
                        freed += size
                    except Exception:
                        continue

                if removed:
                    logger.info(
                        f"[Cleanup] Removed {removed} old cached file(s), "
                        f"freed {freed / (1024 * 1024):.1f} MB."
                    )
        except Exception as e:
            logger.error(f"[Cleanup] Download cleanup loop error: {e}")

        await asyncio.sleep(CLEANUP_INTERVAL)
      

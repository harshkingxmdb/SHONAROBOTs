# Starts / stops the music system inside the manage bot's process.
#
# Everything here is defensive on purpose: if music is not configured (no assistant
# session, bad logger group, ...) the manage bot must keep running normally.

import asyncio
import importlib
import logging

LOGGER = logging.getLogger("AloneX.music.runner")

STARTED = False


async def start_music() -> bool:
    """Boot database, bot client, assistants, calls and load every music plugin."""
    global STARTED

    from AloneX import music

    if not music.READY:
        return False

    try:
        from AloneX.music.helpers._cleanup import cleanup_downloads_loop
        from AloneX.music.plugins import all_modules

        await music.db.connect()
        await music.app.boot()
        await music.userbot.boot()
        await music.anon.boot()
        asyncio.create_task(cleanup_downloads_loop())

        for module in all_modules:
            importlib.import_module(f"AloneX.music.plugins.{module}")
        LOGGER.info(f"Loaded {len(all_modules)} music modules.")

        music.app.sudoers.update(await music.db.get_sudoers())
        music.app.bl_users.update(await music.db.get_blacklisted())
        LOGGER.info(f"Loaded {len(music.app.sudoers)} music sudo users.")
    except (Exception, SystemExit) as e:
        # SystemExit is raised by the music core for config problems (e.g. bot is not admin in
        # the logger group). Never let it kill the manage bot.
        LOGGER.error(f"Music system failed to start: {e}")
        try:
            await music.stop()
        except Exception:
            pass
        return False

    STARTED = True
    LOGGER.info("Music system started.")
    return True


async def stop_music() -> None:
    global STARTED
    if not STARTED:
        return
    from AloneX import music

    STARTED = False
    await music.stop()


def is_active() -> bool:
    return STARTED

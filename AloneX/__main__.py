import os
import importlib
import pkgutil
import logging
import importlib.util
import asyncio
from app import keep_alive, web_server
from aiohttp import web
from telegram import Update
from telegram.ext import Application
from AloneX import (
    TOKEN, app, plugins, SUPPORT_CHAT, LOGS_CHANNEL, 
    IS_WEB_SUP, initialize_database, start_all_clients, 
    BIND_ADDRESS, PORT, pbot, tbot, user, MODULE
)

logging.basicConfig(level=logging.DEBUG)

def import_plugins(package):
    package_name = package.__name__
    package_file = package.__file__

    logging.debug(f"Importing plugins from package: {package_name}")
    logging.debug(f"Package file attribute: {package_file}")

    if package_file is None:
        raise ValueError(f"Package {package_name} does not have a file attribute. It might be a namespace package.")

    package_dir = os.path.dirname(package_file)
    logging.debug(f"Package directory: {package_dir}")

    imported_modules = []

    for _, name, is_pkg in pkgutil.iter_modules([package_dir]):
        full_name = f"{package_name}.{name}"
        logging.debug(f"Importing module: {full_name}")
        module = importlib.import_module(full_name)

        # Register help
        help_text = getattr(module, "__help__", None) or getattr(module, "HELP", None) or getattr(module, "__HELP__", None)
        mod_name = getattr(module, "__module__", None) or getattr(module, "__mod_name__", None) or getattr(module, "__MODULE__", None)

        if mod_name and help_text:
            MODULE[mod_name.lower()] = help_text

        imported_modules.append(full_name)

    logging.info(f"Successfully imported {len(imported_modules)} modules: [{', '.join(module.rsplit('.', 1)[-1] for module in imported_modules)}]")


async def start_music_safe():
    """Start the music system. A problem in music must never stop the manage bot."""
    try:
        from AloneX.music.runner import start_music
        await start_music()
    except (Exception, SystemExit) as e:
        logging.error(f"Music system disabled: {e}")


async def stop_music_safe():
    try:
        from AloneX.music.runner import stop_music
        await stop_music()
    except (Exception, SystemExit) as e:
        logging.error(f"Music stop failed: {e}")


async def start_services():
    server = web.AppRunner(web_server())
    await server.setup()
    await web.TCPSite(server, BIND_ADDRESS, PORT).start()
    logging.info("Web Server Initialized Successfully")
    logging.info("=========== Service Startup Complete ===========")
  
    asyncio.create_task(keep_alive())
    logging.info("Keep Alive Service Started")
    logging.info("=========== Initializing Web Server ===========")


if __name__ == '__main__':
    import_plugins(plugins)
    
    async_funcs = [
        start_all_clients(),
        initialize_database()
    ]
    
    if IS_WEB_SUP:
        async_funcs.append(start_services())
        
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*async_funcs))

    # music runs inside this same process / event loop (after the shared clients are up)
    loop.run_until_complete(start_music_safe())
    
    logging.info("Starting PTB Application...")
    try:
        app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    finally:
        try:
            asyncio.get_event_loop().run_until_complete(stop_music_safe())
        except Exception:
            pass

import logging
import re
import os
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
import asyncio
import config
import aiohttp
import traceback
import math
import mimetypes
import secrets

from config import multi_clients, work_loads
from AloneX.helpers import pyro_utils
from AloneX.helpers.render_template import render_page

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()


@routes.get("/", allow_head=True)
async def root_route_handler(request):
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AloneX Bot</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Arial', sans-serif;
        }

        body {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            line-height: 1.6;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .hero {
            text-align: center;
            padding: 60px 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            margin: 20px 0;
        }

        .hero img {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            margin-bottom: 20px;
            border: 4px solid #4CAF50;
        }

        .hero h1 {
            font-size: 2.5em;
            margin-bottom: 20px;
            color: #4CAF50;
        }

        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 40px 0;
        }

        .feature-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            transition: transform 0.3s ease;
        }

        .feature-card:hover {
            transform: translateY(-5px);
        }

        .feature-icon {
            font-size: 40px;
            margin-bottom: 15px;
            color: #4CAF50;
        }

        .cta-button {
            display: inline-block;
            padding: 15px 35px;
            background: linear-gradient(45deg, #4CAF50, #8BC34A);
            color: white;
            text-decoration: none;
            border-radius: 30px;
            font-weight: bold;
            transition: all 0.3s ease;
            margin-top: 20px;
            box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .cta-button:hover {
            background: linear-gradient(45deg, #45a049, #7CB342);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(76, 175, 80, 0.4);
        }

        footer {
            text-align: center;
            padding: 20px;
            background: rgba(0, 0, 0, 0.2);
            margin-top: 40px;
        }

        footer a {
            color: #4CAF50;
            text-decoration: none;
        }

        footer a:hover {
            text-decoration: underline;
        }

        @media (max-width: 768px) {
            .hero {
                padding: 40px 20px;
            }
            
            .features {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <img src="https://i.ibb.co/PZmh6bkf/file-337.jpg" alt="AloneX Kun">
            <h1>AloneX Assistant Bot</h1>
            <p>Your all-in-one Telegram assistant powered by AI</p>
            <a href="https://t.me/AloneXkunbot?start=help" class="cta-button">Start Using Bot</a>
        </div>

        <div class="features">
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <h3>AI Tools</h3>
                <p>Advanced AI-powered features for chat, image generation, and more</p>
            </div>

            <div class="feature-card">
                <div class="feature-icon">🎬</div>
                <h3>Movies & Anime</h3>
                <p>Access to a vast collection of movies and anime content</p>
            </div>

            <div class="feature-card">
                <div class="feature-icon">💬</div>
                <h3>Smart Chatbot</h3>
                <p>Intelligent conversation system for natural interactions</p>
            </div>

            <div class="feature-card">
                <div class="feature-icon">✨</div>
                <h3>Font Styling</h3>
                <p>Creative text formatting and stylish font options</p>
            </div>

            <div class="feature-card">
                <div class="feature-icon">🧮</div>
                <h3>Calculator</h3>
                <p>Quick and easy calculations right in your chat</p>
            </div>

            <div class="feature-card">
                <div class="feature-icon">👥</div>
                <h3>Group Management</h3>
                <p>Comprehensive tools for managing Telegram groups</p>
            </div>
        </div>

        <footer>
            <p>Made with ❤️ by <a href="https://t.me/DEPSTEY" target="_blank">@Sahil</a></p>
        </footer>
    </div>
</body>
</html>    
    """
    return web.Response(text=html_content, content_type="text/html")




####################################################################################################





class InvalidHash(Exception):
    message = "Invalid hash"

class FIleNotFound(Exception):
    message = "File not found"


@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)


        if match:
            secure_hash = match.group(1)
            message_id = int(match.group(2))
        else:
            message_id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")


        return web.Response(text=await render_page(message_id, secure_hash), content_type='text/html')
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logger.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

@routes.get(r"/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)


        if match:
            secure_hash = match.group(1)
            message_id = int(match.group(2))
        else:
            message_id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")


        return await media_streamer(request, message_id, secure_hash)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logger.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))



class_cache = {}

async def media_streamer(request: web.Request, message_id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)

    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]

    if config.MULTI_CLIENT:
        logger.debug(f"Client {index} is now serving {request.remote}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
        logger.debug(f"Using cached ByteStreamer object for client {index}")
      
    else:
        logger.debug(f"Creating new ByteStreamer object for client {index}")
        tg_connect = pyro_utils.ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
 
    logger.debug("before calling get_file_properties")
    file_id = await tg_connect.get_file_properties(message_id)
    logger.debug("after calling get_file_properties")

    if file_id.unique_id[:6] != secure_hash:
        logger.debug(f"Invalid hash for message with ID {message_id}")
        raise InvalidHash

    file_size = file_id.file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = request.http_range.stop or file_size - 1

    req_length = until_bytes - from_bytes
    new_chunk_size = await pyro_utils.chunk_size(req_length)
    offset = await pyro_utils.offset_fix(from_bytes, new_chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = (until_bytes % new_chunk_size) + 1
    part_count = math.ceil(req_length / new_chunk_size)
    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, new_chunk_size
    )

    mime_type = file_id.mime_type
    file_name = file_id.file_name
    disposition = "attachment"
    if mime_type:
        if not file_name:
            try:
                file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
            except (IndexError, AttributeError):
                file_name = f"{secrets.token_hex(2)}.bin"
    else:
        if file_name:
            mime_type = mimetypes.guess_type(file_id.file_name)
        else:
            mime_type = "application/octet-stream"
            file_name = f"{secrets.token_hex(2)}.bin"
    if "video/" in mime_type or "audio/" in mime_type:
        disposition = "inline"
    return_resp = web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Range": f"bytes={from_bytes}-{until_bytes}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )

    if return_resp.status == 200:
        return_resp.headers.add("Content-Length", str(file_size))

    return return_resp
####################################################################################################
def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

async def keep_alive():
    """
    Pings config.WEB_URL every config.WEB_SLEEP seconds.
    Handles cancellation gracefully so shutdown won't leave a pending task.
    """
    if not config.WEB_URL:
        return

    try:
        while True:
            await asyncio.sleep(config.WEB_SLEEP)
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(config.WEB_URL) as resp:
                        logger.info("Pinged %s with response: %s", config.WEB_URL, resp.status)
            except asyncio.TimeoutError:
                logger.warning("Couldn't connect to the site URL (timeout).")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error while pinging keep-alive URL")
    except asyncio.CancelledError:
        logger.info("keep_alive task cancelled, exiting cleanly.")
        raise
async def _on_startup(app: web.Application):
    """Start background keep_alive task (if configured) and save it on app"""
    if config.WEB_URL:
        logger.debug("Starting keep_alive background task")
        task = asyncio.create_task(keep_alive(), name="keep_alive_task")
        app["keep_alive_task"] = task
async def _on_cleanup(app: web.Application):
    """Cancel background task and await it so it doesn't remain pending"""
    task = app.get("keep_alive_task")
    if not task:
        return
    logger.debug("Cancelling keep_alive background task")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.debug("keep_alive task cancelled successfully during cleanup")
    except Exception:
        logger.exception("Error while waiting for keep_alive task during cleanup")
def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    web_app.on_startup.append(_on_startup)
    web_app.on_cleanup.append(_on_cleanup)

    return web_app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    try:
        web.run_app(web_server(), host="0.0.0.0", port=port)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down web app")


import config

from AloneX import pbot as bot
from AloneX.helpers.pyro_utils import humanbytes
from AloneX.helpers.pyro_utils import get_file_ids

import urllib.parse
import aiofiles
import logging
import aiohttp

class InvalidHash(Exception):
    message = "Invalid hash"

class FIleNotFound(Exception):
    message = "File not found"



async def render_page(message_id, secure_hash):
    try:
        file_data = await get_file_ids(bot, int(config.FILE_DB_CHANNEL), int(message_id))
        if file_data.unique_id[:6] != secure_hash:
            logging.debug(f'link hash: {secure_hash} - {file_data.unique_id[:6]}')
            logging.debug(f"Invalid hash for message with - ID {message_id}")
            raise InvalidHash
          
        src = urllib.parse.urljoin(config.WEB_URL, f'{secure_hash}{str(message_id)}')
        
        # Read the appropriate template file
        template_path = None
        file_name = str(getattr(file_data, 'file_name', 'Unkown'))
        
        if str(file_data.mime_type.split('/')[0].strip()) == 'video':
            template_path = 'AloneX/helpers/template/req.html'
            heading = f'Watch {file_name}'
        elif str(file_data.mime_type.split('/')[0].strip()) == 'audio':
            template_path = 'AloneX/helpers/template/req.html'
            heading = f'Listen {file_name}'
        else:
            template_path = 'AloneX/helpers/template/dl.html'
            heading = f'Download {file_name}'
            
        async with aiofiles.open(template_path) as r:
            template_content = await r.read()
            
            if template_path.endswith('dl.html'):
                async with aiohttp.ClientSession() as s:
                    async with s.get(src) as u:
                        file_size = str(humanbytes(int(u.headers.get('Content-Length'))))
                        html = template_content.replace("{heading}", heading)
                        html = html.replace("{file_name}", file_name)
                        html = html.replace("{media_url}", src)
                        html = html.replace("{file_size}", file_size)
                        
            else:
                # For video and audio templates
                html = template_content.replace("{heading}", heading)
                html = html.replace("{file_name}", file_name)
                html = html.replace("{media_url}", src)
                
        return html

    except Exception as e:
        logging.error(f"Error in render_page: {str(e)}")
        raise e
      

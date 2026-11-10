import re
import json
import random
import asyncio
import os
import io
import config
import aiohttp
import base64
import uuid
import hashlib
import ast
import mimetypes
from dataclasses import dataclass
from PIL import Image
from AloneX import aiohttpsession, init_aiohttp_session, LOGGER
from urllib.parse import quote, urlencode, urljoin
from AloneX.helpers.utils import UserId, get_ua, async_cache, cookies_csv_to_str 
from bs4 import BeautifulSoup
from typing import List, Dict
from AloneX import process

session = aiohttpsession
# ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––>


@async_cache(max_size=20)
async def search_youtube(query: str, num_results: int = 10) -> List[Dict[str, str]]:
    search_query = quote(query)
    url = f"https://www.youtube.com/results?search_query={search_query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()  # Raises an HTTPError for bad responses
                html = await response.text()

                # Extract JSON data from the response using regex
                matches = re.search(r'var ytInitialData = (.+?);</script>', html)
                if matches:
                    data = json.loads(matches.group(1))

                    # Navigate through the JSON structure to get video data
                    video_data = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"]

                    video_results = []
                    for item in video_data:
                        if "videoRenderer" in item:
                            video = item["videoRenderer"]
                            video_results.append({
                                "title": video["title"]["runs"][0]["text"],
                                "url": f"https://www.youtube.com/watch?v={video['videoId']}",
                                "channel": video["ownerText"]["runs"][0]["text"],
                                "views": video.get("viewCountText", {}).get("simpleText", "N/A")
                            })
                        if len(video_results) >= num_results:
                            break
                    return video_results
                else:
                    print("Could not extract video data from YouTube page.")
                    return []
        except aiohttp.ClientError as error:
            LOGGER.error(f"Error fetching data from YouTube: {error}")
            return []


#––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––>

@async_cache(max_size=20)
async def search_wikipedia(query: str, num_results: int = 10) -> List[Dict[str, str]]:
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": num_results,
        "srprop": "snippet",
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()  # Raises an HTTPError for bad responses
                data = await response.json()

                search_results = []
                if data.get("query", {}).get("search"):
                    for article in data["query"]["search"][:num_results]:
                        title = article["title"]
                        page_id = article["pageid"]
                        snippet = article["snippet"]
                        article_url = f"https://en.wikipedia.org/?curid={page_id}"
                        search_results.append({
                            "title": title,
                            "url": article_url,
                            "snippet": snippet,
                        })
                return search_results
        except aiohttp.ClientError as error:
            LOGGER.error(f"Error fetching data from Wikipedia: {error}")
            return []


# ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––>

@async_cache(max_size=20)
async def search_gfg(query: str, num_results: int = 10) -> List[Dict[str, str]]:
    encoded_query = quote(query)
    search_url = f"https://recommendations.geeksforgeeks.org/api/v1/global-search?products=articles&articles_count={num_results}&query={encoded_query}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(search_url) as response:
                response.raise_for_status()  # Raises an HTTPError for bad responses
                data = await response.json()

                search_results = []
                if data.get('status') and data.get('detail', {}).get('articles'):
                    articles = data['detail']['articles']['data']
                    for article in articles[:num_results]:
                        search_results.append({
                            'title': article['post_title'],
                            'url': article['post_url'],
                            'snippet': article['post_excerpt']
                        })
                return search_results
        except aiohttp.ClientError as error:
            LOGGER.error(f"Error fetching data from GeeksforGeeks: {error}")
            return []




#-------------------------------------------------------------------------------
   
    
async def pinterest_link2download(url: str):
        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        }
        async with aiohttp.ClientSession() as session:
              async with session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    # let's find some mp4 video's if found.
                    pattern = r'https:\/\/v1\.pinimg\.com\/videos\/[^"\']*?\.mp4'
        
                    video_url_data = re.findall(pattern, response_text)
                    video_urls = set([url for url in video_url_data if url.endswith('.mp4')]) if video_url_data else [] # filtering for only .mp4 allowed.
                    soup = BeautifulSoup(response_text, 'html.parser')
                    image_url = None
                
                    for meta in soup.find_all('meta'):
                        if meta.get('property') in ['og:image', 'og:image:url']:
                            image_url = meta.get('content')
                          
                            if image_url:
                                 image_url = image_url.replace('236x', 'originals')
                                 break
                    return {
                        'image_url': image_url,
                        'video_urls': list(video_urls)
                    }
                    
#-------------------------------------------------------------------------------
   


async def gimage_search(query: str, limit: int = 7) -> list[str]:
    search_url = f"https://www.google.com/search?tbm=isch&q={query}"
    async with aiohttp.ClientSession() as session:
        async with session.get(search_url) as response:
            try:
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')

                downloaded_images = []
                downloaded = 0
                for img in soup.find_all('img'):
                    if downloaded >= limit:
                        break
                    try:
                        url = img['src']
                        if url.startswith('http'):
                            downloaded_images.append(url)
                            downloaded += 1
                    except KeyError:
                        pass
            except Exception as e:
                return {'error': str(e)}
    return {'results': downloaded_images}


#-------------------------------------------------------------------------------
   


async def anime_quote(page: int = 1, search: str = None, random: bool = False):
    
    base_url = "https://www.animecharactersdatabase.com/quotesbycharacter.php"
    params = {}
    
    if not random:
          if (page > 9000 or page < 1):
               raise Exception("❌ page number should be less than 9k (1 to 9000)")
          
          elif page != 1:
               params['x'] = page

          if search:
               params['s'] = search
      
          url = urljoin(base_url, "?" + urlencode(params))
    
    
    else:
          url = "https://www.animecharactersdatabase.com/quotesbycharacter.php?random"

    async with aiohttp.ClientSession() as session:
          async with session.get(url, headers={'user-agent': get_ua()}) as response:
              try:
                  soup = BeautifulSoup(await response.text(), 'html.parser')
                  table = soup.find('table', {'id': 'transcript'})
                  quotes_html = table.find_all('tr')
                  quotes_list = []
                  # Iterate through the rows in pairs
                  for i in range(0, len(quotes_html), 2):
                     if i + 1 >= len(quotes_html):  # Check if there's a next row
                          break
                     character_row = quotes_html[i]
                     audio_row = quotes_html[i + 1]

                     # Extract character name, quote, and audio URL
                     character_data = character_row.find('td').find('a').img
                     character_name = character_data.get('alt', 'not found').strip() if character_data else 'not found'
                     character_image = character_data.get('src', 'not found').strip() if character_data else 'not found'
                     quote_text = character_row.find('q').text.strip() if character_row.find('q') else 'not found'
                     audio_url = audio_row.find('audio').find('source')['src'] if audio_row.find('audio') else 'not found'

                     # Only append if quote and audio URL are found
                     if quote_text != 'not found' and audio_url != 'not found':
                          quotes_list.append({
                             'audio_url': audio_url,
                             'image_url': character_image,
                             'character': character_name,
                             'quote': quote_text
                     })
              except Exception as e:
                    return {'error': str(e)} 

    return quotes_list


#-------------------------------------------------------------------------------
   

async def paste_gist(content: str, ext: str = "txt"):
    api_url = "https://api.github.com/gists/e08f0a195acf449983815ee7bc3fde4e"
    if not config.GIST_TOKEN:
        return {'error': '❌ GIST_TOKEN not configured.'}

    headers = {
        "Authorization": f"Bearer {config.GIST_TOKEN}",
        "accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    id = f"{UserId()}.{ext}"
    payload = {
        "files": {
            id: {
                "content": content
            }
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, headers=headers, data=json.dumps(payload)) as response:
                if response.status != 200:
                    return {'error': f'❌ ERROR: `{response.reason}`'}
                results = await response.json()
                files = results['files']
                paste = files.get(id, None)
                paste_url = f"https://gist.github.com/NandhaxD/e08f0a195acf449983815ee7bc3fde4e#file-{id.replace('.', '-')}"
                raw_url = paste['raw_url']
                return {
                    'url': paste_url,
                    'raw_url': raw_url
                }
    except Exception as e:
        return {'error': str(e)}
           
#-------------------------------------------------------------------------------
   

@async_cache(max_size=20)
async def get_pypi_info(package: str, version: [str,None] = None):
       ''' pypi package info func by @DEPSTEY '''
       url = f"https://pypi.org/pypi/{package}{f'/{version}' if version else ''}" + "/json"
       # print(url)
       async with aiohttp.ClientSession() as session:
           try:
               async with session.get(url) as response:
                    data = await response.json()
                    error = data.get('message')
                    if error:
                        return {'error': error}
                    info = data['info']
                    release = list(data['releases'].items())[-1] if data.get('releases') else None
                    results = {
                        'name': info['name'],
                        'author': info['author'],
                        'author_email': info['author_email'],
                        'description': info.get('description'),
                        'download_url': info.get('download_url'),
                        'keywords': info.get('keywords'),
                        'summary': info.get('summary'),
                        'version': info.get('version'),
                        'requires_python': info.get('requires_python'),
                        'latest_releases': release
                        
                    }
                    return {
                        'results': results
                    }
           except Exception as e:
                 return {
                   'error': str(e)
                 }



####################################################################################################
@async_cache()
async def google_search(query: str):
    url = f"https://www.google.com/search?q={quote(query)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.text()

        soup = BeautifulSoup(data, "html.parser")
        results = []

        # New selectors (2025 working)
        for result in soup.select('.tF2Cxc'):
            try:
                title = result.select_one('.yuRUbf h3')
                link = result.select_one('.yuRUbf a')
                snippet = result.select_one('.VwiC3b')

                if title and link:
                    results.append({
                        'title': title.get_text(strip=True),
                        'link': link.get('href', ''),
                        'snippet': snippet.get_text(strip=True) if snippet else ""
                    })
            except Exception:
                continue

        return {'results': results}

    except Exception as e:
        return {'error': str(e)}

####################################################################################################  # make sure it's imported
async def fetch_wallpapers(query: str = None):
    """
    Fetch wallpapers from wallpapers.com based on query.
    Returns a list of dicts: [{"title": ..., "url": ...}, ...]
    Always returns a list (even if empty)
    """
    if not query:
        query = ""  # default search

    try:
        if aiohttpsession is None or aiohttpsession.closed:
            await init_aiohttp_session()

        url = f"https://wallpapers.com/search/{query}"
        async with aiohttpsession.get(url, timeout=10) as response:
            if response.status != 200:
                LOGGER.warning(f"[Wallpaper Fetch Warning] HTTP {response.status} for query: {query}")
                return []
            html_text = await response.text()

    except Exception as e:
        LOGGER.error(f"[Wallpaper Fetch Error] {e}")
        return []

    try:
        soup = BeautifulSoup(html_text, "html.parser")
        results = soup.find_all("div", class_="w-full relative group") or []

        images_data = []
        for result in results:
            a_tag = result.find("a")
            img_tag = result.find("img")

            title = a_tag.get("title") if a_tag else None
            img_url = None
            if img_tag:
                img_url = img_tag.get("data-src") or img_tag.get("src")

            if title and img_url:
                if not img_url.startswith("http"):
                    img_url = "https://wallpapers.com" + img_url
                images_data.append({"title": title, "url": img_url})
            else:
                LOGGER.debug("[Wallpaper Skipped] Missing title or image URL")

        if not images_data:
            LOGGER.info(f"[Wallpaper Fetch] No results found for query: {query}")

        return images_data[:30]

    except Exception as e:
        LOGGER.error(f"[Wallpaper Parsing Error] {e}")
        return []
####################################################################################################

async def fetch_and_resize_image(url, width: int = 640, height: int = 960):
    async with aiohttp.ClientSession() as session:
        try:
           async with session.get(url) as response:
               content = await response.read()
               img = Image.open(io.BytesIO(content))
               img = img.resize((width, height))
               save_path = f"{uuid.uuid4()}.jpeg"
               img.save(save_path)
               return {'path': save_path}
        except Exception as e:
            return {'error': str(e)}

####################################################################################################

#IMDB

class IMDBScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Connection": "keep-alive",
        }

    async def fetch_url_content(self, url):
        """Fetch URL content using aiohttp"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    response.raise_for_status()
                    return BeautifulSoup(await response.text(), 'html.parser')
        except Exception as e:
            raise Exception(f"Request failed: {e}")

    def extract_json_data(self, soup):
        """Extract JSON data from BeautifulSoup object"""
        script_tag = soup.find('script', {'id': '__NEXT_DATA__', 'type': 'application/json'})
        if not script_tag:
            raise Exception("Script tag with id '__NEXT_DATA__' not found.")
        return json.loads(script_tag.string)

    @async_cache()
    async def search_by_name(self, name):
        """Search IMDB by name"""
        url = f"https://m.imdb.com/find/?q={quote(name)}"

        try:
            soup = await self.fetch_url_content(url)
            data = self.extract_json_data(soup)
            return {'results': data.get("props", {}).get("pageProps", {}).get("titleResults", {}).get("results", [])}
        except Exception as e:
            return {'error': str(e)}
          
    def extract_top_casts(self, page_props):
        """Extract top cast information"""
        top_casts = []
        cast_data = page_props.get("mainColumnData", {}).get("cast", {}).get("edges", [])
        for cast in cast_data:
            node = cast.get("node", {})
            characters = node.get("characters", [])
            name_data = node.get("name", {})
            primary_image = name_data.get("primaryImage", {})
            top_casts.append({
                "character_name": characters[0].get("name", "N/A") if characters else "N/A",
                "real_name": name_data.get("nameText", {}).get("text", "N/A"),
                "actor_image": primary_image.get("url", "N/A") if primary_image else "N/A"
            })
        return top_casts

    def extract_common_details(self, page_props, fold_data):
        """Extract common details for both movies and series"""
        title_text = fold_data.get('originalTitleText', {}).get('text', 'N/A')
        thumbnail = fold_data.get('primaryImage', {}).get('url', 'N/A')
        release_year = fold_data.get("releaseDate", {}).get("year", "N/A")
        avg_rating = fold_data.get("ratingsSummary", {})
        avg_rating = "N/A" if avg_rating is None else avg_rating.get("aggregateRating", "N/A")
        rating_vote_count = fold_data.get("ratingsSummary", {})
        rating_vote_count = "N/A" if rating_vote_count is None else rating_vote_count.get("voteCount", "N/A")
        time_duration_data = fold_data.get("runtime")
        time_duration = "N/A" if time_duration_data is None else time_duration_data.get("displayableProperty", {}).get("value", {}).get("plainText", "N/A")
        
        plot_data = fold_data.get("plot", {})
        plot_text_data = plot_data.get("plotText", None) if plot_data else None
        description = "No description available" if plot_text_data is None else plot_text_data.get("plainText", "No description available")
        
        release_date = f'{fold_data.get("releaseDate", {}).get("day", "N/A")}/{fold_data.get("releaseDate", {}).get("month", "N/A")}/{fold_data.get("releaseDate", {}).get("year", "N/A")}'
        country_of_origin = page_props.get("mainColumnData", {}).get("countriesOfOrigin", {}).get("countries", [{}])[0].get("text", "N/A")
        
        spoken_languages_data = page_props.get("mainColumnData", {}).get("spokenLanguages")
        languages_list = spoken_languages_data.get("spokenLanguages") if spoken_languages_data else []
        languages = ', '.join([lang.get("text", "N/A") for lang in languages_list])
        
        isSeries = fold_data.get("titleType", {}).get("isSeries", "N/A")
        
        budget_data = page_props.get("mainColumnData", {}).get("productionBudget", {})
        budget_data = budget_data.get("budget", {}) if budget_data else {}
        production_budget = {
            "production_budget_price": budget_data.get("amount", "N/A"),
            "production_budget_currency": budget_data.get("currency", "N/A")
        }
        
        worldwide_gross_total_data = page_props.get("mainColumnData", {}).get("worldwideGross", {})
        worldwide_gross_total_data = worldwide_gross_total_data.get("total", {}) if worldwide_gross_total_data else {}
        worldwide_gross = {
            "worldwide_gross_amount": worldwide_gross_total_data.get("amount", "N/A"),
            "worldwide_gross_currency": worldwide_gross_total_data.get("currency", "N/A")
        }
        
        return {
            'titleText': title_text,
            'thumbnail': thumbnail,
            'releaseYear': release_year,
            'avgRating': avg_rating,
            'isSeries': isSeries,
            'ratingVoteCount': rating_vote_count,
            'timeDuration': time_duration,
            'description': description,
            'releaseDate': release_date,
            'countryOfOrigin': country_of_origin,
            'languages': languages,
            'productionBudget': production_budget,
            'worldwideGross': worldwide_gross,
            'topCasts': self.extract_top_casts(page_props)
        }

    def extract_movie_details(self, page_props, fold_data, imdb_id):
        """Extract movie-specific details"""
        details = self.extract_common_details(page_props, fold_data)
        
        director = (fold_data.get("principalCredits", [{}])[0] if len(fold_data.get("principalCredits", [])) > 0 else "N/A")
        director = director.get("credits", [{}])[0] if len(director.get("credits", [])) > 0 else "N/A"
        director = (director.get("name", {}).get("nameText", {}).get("text", "N/A")
            if len(fold_data.get("principalCredits", [])) > 0 and
            len(fold_data.get("principalCredits", [{}])[0].get("credits", [])) > 0
            else "N/A")
        
        writer = (
            ', '.join([
                credit.get("name", {}).get("nameText", {}).get("text", "N/A")
                for credit in fold_data.get("principalCredits", [{}])[1].get("credits", [])
            ])
            if len(fold_data.get("principalCredits", [])) > 1
            else "N/A"
        )

        stars = (
            ', '.join([
                credit.get("name", {}).get("nameText", {}).get("text", "N/A")
                for credit in fold_data.get("principalCredits", [{}])[2].get("credits", [])
            ])
            if len(fold_data.get("principalCredits", [])) > 2
            else "N/A"
        )

        playbackURL = (
            fold_data.get("primaryVideos", {}).get("edges", [{}])[0]
            .get("node", {}).get("playbackURLs", [{}])[0]
            .get("url", "N/A")
            if len(fold_data.get("primaryVideos", {}).get("edges", [])) > 0 and
            len(fold_data.get("primaryVideos", {}).get("edges", [{}])[0]
            .get("node", {}).get("playbackURLs", [])) > 0
            else "N/A"
        )

        details.update({
            'imdb_id': imdb_id,
            'director': director,
            'writer': writer,
            'stars': stars,
            'playbackURL': playbackURL
        })
        
        return details

    def extract_series_details(self, page_props, fold_data, imdb_id):
        """Extract series-specific details"""
        details = self.extract_common_details(page_props, fold_data)

        director = (fold_data.get("principalCredits", [{}])[0].get("credits", [{}])[0].get("name", {}).get("nameText", {}).get("text", "N/A")
                if len(fold_data.get("principalCredits", [])) > 0 and len(fold_data.get("principalCredits", [{}])[0].get("credits", [])) > 0 else "N/A")

        creators = (', '.join([credit.get("name", {}).get("nameText", {}).get("text", "N/A") 
                           for credit in fold_data.get("principalCredits", [])[0].get("credits", [])]) 
                if len(fold_data.get("principalCredits", [])) > 0 else "N/A")

        stars = (', '.join([credit.get("name", {}).get("nameText", {}).get("text", "N/A") 
                        for credit in fold_data.get("principalCredits", [])[1].get("credits", [])]) 
             if len(fold_data.get("principalCredits", [])) > 1 else "N/A")

        playbackURL = (fold_data.get("primaryVideos", {}).get("edges", [{}])[0].get("node", {}).get("playbackURLs", [{}])[0].get("url", "N/A")
                   if len(fold_data.get("primaryVideos", {}).get("edges", [])) > 0 and 
                   len(fold_data.get("primaryVideos", {}).get("edges", [{}])[0].get("node", {}).get("playbackURLs", [])) > 0 else "N/A")

        details.update({
            'imdb_id': imdb_id,
            'director': director,
            'creators': creators,
            'stars': stars,
            'playbackURL': playbackURL
        })
        return details

    async def extract_data(self, imdb_id):
        """Extract all data for a given IMDB ID"""
        url = f"https://m.imdb.com/title/{imdb_id}/"
        try:
           soup = await self.fetch_url_content(url)
           data = self.extract_json_data(soup)
           page_props = data.get('props', {}).get('pageProps', {})
           fold_data = page_props.get('aboveTheFoldData', {})
        
           if fold_data.get("titleType", {}).get("isSeries", False):
               return self.extract_series_details(page_props, fold_data, imdb_id)
           else:
               return {'results': self.extract_movie_details(page_props, fold_data, imdb_id)}
             
        except Exception as e:
               return {'error': str(e)}



####################################################################################################


async def gsearch_names(text):
    headers = {'user-agent': get_ua()}
    url = f'https://www.google.com/search?q={quote(text)}'
    async with aiohttp.ClientSession() as session:
         try:
            async with session.get(url, headers=headers) as response:
                 soup = BeautifulSoup(await response.text(), 'html.parser')
                 titles = soup.find_all( 'h3' )
                 if not titles:
                      return {'error': 'No search results found for this query.'}
                 return {'results': [title.get_text() for title in titles]}
         except Exception as e:
               return {'error': str(e)}
                


####################################################################################################
@async_cache()
async def zerochan(query: str):
    url = f"https://www.zerochan.net/search?q={quote(query)}"
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Linux; Android 11; Infinix X6816C) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/122.0.6261.119 Mobile Safari/537.36'
        )
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    return {'error': f'HTTP {response.status} - Unable to fetch'}

                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')

                # Try multiple possible selectors (site structure may change)
                element = soup.find('ul', {'id': 'thumbs'}) or soup.find('ul', class_='thumbs')
                if not element:
                    return {'error': 'No images found 😓'}

                images = element.find_all('img')
                if not images:
                    return {'error': 'No images found 😓'}

                result = []
                for img in images:
                    src = img.get('src') or img.get('data-src')
                    alt = img.get('alt', 'No title')
                    if src:
                        # Convert relative URLs to absolute if needed
                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = "https://www.zerochan.net" + src
                        result.append({'url': src, 'title': alt})

                if not result:
                    return {'error': 'No images found 😓'}

                return {'results': result}

        except Exception as e:
            return {'error': str(e)}
####################################################################################################

async def get_trendings(country: str = None):

      base_url = "https://getdaytrends.com"
      country_data = ['algeria', 'argentina', 'australia', 'austria', 'bahrain', 'belarus', 'belgium', 'brazil', 'canada', 'chile', 'colombia', 'denmark', 'dominican-republic', 'ecuador', 'egypt', 'france', 'germany', 'ghana', 'greece', 'guatemala', 'india', 'indonesia', 'ireland', 'israel', 'italy', 'japan', 'jordan', 'kenya', 'korea', 'kuwait', 'latvia', 'lebanon', 'malaysia', 'mexico', 'netherlands', 'new-zealand', 'nigeria', 'norway', 'oman', 'pakistan', 'panama', 'peru', 'philippines', 'poland', 'portugal', 'puerto-rico', 'qatar', 'russia', 'saudi-arabia', 'singapore', 'south-africa', 'spain', 'sweden', 'switzerland', 'thailand', 'turkey', 'ukraine', 'united-arab-emirates', 'united-kingdom', 'united-states', 'venezuela', 'vietnam']
      
      url = base_url

      if country:
           if country not in country_data:
                return {'error': 'Not Supported Country Name.'}      
           else:
                url = base_url + f'/{country}'
            
      headers = {"user-agent": get_ua()}

      # func for extract data from table
      def get_result(data):
          tags = data.table.find_all('tr')
          results = []
          for tr in tags:
              src = tr.td
              title = src.get_text()
              link = base_url + src.a.get('href')
              results.append({'title': title, 'url': link})
          return results

      async with aiohttp.ClientSession() as session:
           try:
               async with session.get(url, headers=headers) as response:
                     if response.status != 200:
                          return {'error': response.reason}
                     content = await response.text()
                     soup = BeautifulSoup(content, 'html.parser')
                     title = soup.html.title.text
                     tables = soup.select("div[class^='inset']")
                     return {
                         'title': title,
                         'now_hashtags': get_result(tables[0]),
                         'today_hashtags': get_result(tables[1]),
                         'top_hashtags': get_result(tables[2])
                     }
                       
           except Exception as e:
                  return {'error': str(e)}


####################################################################################################

# Updated extract_video_info function from your provided code
def extract_video_info(video_data):
    # Initialize list to store results
    results = []

    # Patterns for each field
    patterns = {
        'url': r'"url":"(.*?)"',
        'thumbnail': r'"thumbnail":"(.*?)"',
        'duration': r'"duration":(\d+)',
        'width': r'"width":(\d+)',
        'height': r'"height":(\d+)'
    }

    # Extract all fields using patterns
    matches = {
        field: re.search(pattern, video_data)
        for field, pattern in patterns.items()
    }

    # Check if all required fields are present
    if all(matches.values()):
        url = matches['url'].group(1)
        # Check if the URL ends with .mp4 or is an expMp4 URL
        if url.endswith('.mp4') or 'expMp4' in url:
            result = {
                'url': url,
                'thumbnail': matches['thumbnail'].group(1),
                'duration': int(matches['duration'].group(1)),
                'width': int(matches['width'].group(1)),
                'height': int(matches['height'].group(1))
            }
            results.append(result)

    return results if results else None

# Async function to search Pinterest videos
async def pinterest_video_search(query: str):
    api_url = "https://id.pinterest.com/search/videos/?autologin=true&rs=content_type_filter&q=" + quote(query)
    headers = {
          "cookie": "__Secure-s_a=cGNNN0RhSDVwZDFtNUppSGQ5emhuV1k5UVczTVBBLzJQYzR5a1dZWVBWNDROb1VhTkdVT1dpN0ttYjBuOWJ0OHRQMzlIWmUwOHRYS1ZsWDYxV0hFRTVQV0x4eUo5LzJOdndpTWl3bjhjY05BaVF0RlpOM0xKTjQ4M2RwdjV5TzJNdytVRWpkaDhlVkxQZWJuVzBrSjdFTmFhRUkrNzR4RElzUnpMOEg4L3ZKanoxb0ZZUmhCZVZzK05ReFFmQzhQN0ZRMURrN3RjV2JYNlpuekFrQ0x4b1VUQ0wyRVpsMUZwdDVDc04zZm9iS2NvTzR0RzJBTk5GREdEa29RdFFCbS9UbHBHVkJEZGpQK2NaZndNdFJDZ00ySGdWckV4elVrcDJBbGludVRDQnM4eEZWRitUOExCZGl4d3YrRnRLTmtWbUk2Q0ZreHcwbS9kdGR0Z1YxMWNvRW83QWMxZkhiUTZXRzR4MFltYlNBbC9lZU9BU2FDRFFJMTFUUHVTMVFaWmY0dzZkL0Jqa25Wdmw2MldQTmtjK2NuSFh6R1JtY0JrOTN0TlBSaWNtWGFHMCsrcG4zN0RZOHJyTVh2cDc1aWpDeENkV1o3ZGh4MFdpZ3ZENi9FekRaUDRKZFYwSEFlMEZlbE1yQWhmUTd1d29Ycjd1bmlZT21kcm5XdVA5T3MyT1RFV2hwTjNkL1JnMnJsaTBRcmUzc08vT0xUaFEzVUJqWkJPZW82cjNkdFZvMks5WEJRbGpaNmZIK1o2dHhxZmhjMlpaQWVmUW1YSGxZRnhyMlF0dU9zZUppdXhRajJvL0Uwb1VCT3JqRFpaOWFCeVp1SGtKcGJTUFdqajNsb3QzSXVpRHZNOExPdFl6bGw5bnhLdUJxdFEvQ0xVSkd5S1h3akc5S0EwcDYxYmFpSlF5UWViMTE3SVdCV3phNnpWRm51RDFCd1NFRC9QbUp1emd4cHRtdUNIcDk4THl6ZTBIUmZNU1RKWk1UVUdYMnAwcFdUTFNCZmM1UHBsZjVrcHJpcUFQUWhyYVZITGdUcE93K2ZtdmN6QWV3S09CYnk2TklzaEl1a3p6U0xkakh6UTd0Y25jcFhTV2o0K2dZV21KeEluYjU4Y3AzSFVQOTA2VkNOS2plYmtTRTFtOUtVazBuRnJZc25FLzZPQ3Z4NHl0NWxNK3pITFhXOU9QMEkva3o5b0VBM0N4TTNiOWJlWnJoY2NyeHpjUmtSUmluUjJwMTUvdWJobVUwSzdkRDdQc3EvN1RNRndRcERCK1V5ZGZlS3hQT1l0ODBTdXdoYlBrNkZNYUpRdW5idVV1S0hGUWRwV2lxczZ0MD0mQVBzTTJLaFZ1S055VEZXY1R6V1FvdXZSdEhzPQ==;_pinterest_sess=TWc9PSZvamZ1TlNoQXcvYUpkWjlFK1l1NnFpMjFRKzYwWVRLdGNmdGFyeXR4RWdSR0dhNU0wWGR2K09FWXZCVEQ0WmhBd1NLUFlWYSs2a3d3akxuM2lvKzZXOUVVVEFTZzlDNEpZNUxJaFR0ZEZFSkhBMU1hWTdaeHNobHBXV1BablFhcXJrMS9ScUQxSktISm1EaG0xelBhNEltR0p4SFJTNkJXN2pGT3kzV0F6V1J6ZXRSbG1jRTV0dWdieksva0ljaWQxcG9zYUQvMlMyc1RMc1gvQlBxbzNzYlBkMnZyRWdqMmtBTTRIaEpzMitNNkw4MU5HYVVuWXNJVnhwNnNmQktGMUs0RVp3eTBUVHFCQWxJUHFRTjFta1ZDR0puU2pnVmNEU1JpMTFjM044Mk8yendtSzgxSVJ0dEVnQ2RyYWcwSmloNkJCaitubFJqN21VZWNsOGU4YTh4TmovbHhmNExnOGNaMHVXTkkwZUF1bWVVOWtCbm1qL1FKbzVjWHdhV1RlM09id0pZRWdRYTk2Vm5RNk1yWjZ5U2Z6NlR0MWZ3ZGk1T3dzWHR3U0pHWjlqd0Nlb0hFWDNEVnpxTG5yZjFKZ1NacG5uRE5VaHc5eEQ5RWZEZEJJbUlhWVhDdzNRQVVxRnNMbVRaZ3ljT0FuWitVM2JuY2hadXdFbXdKbmJrZXZZOFRYRWlWS08yNWNmYXBpWG5BaE82QjJCS01hVHlnbmhPZWpqNUljU2lianRNTitGSXNlZGJkSldZYUVwUnFZVDEyODNJS2VHRDdiTEZkZ1p0L3EvSkNDVEt4VE1JVTNXdEpHZWdGTlBHbnllYzZWbkZiRTVydmRqcEpybXlxQTk0ZmY4TTZIRCt6dVhxcGxzZ1dZOGwwNCtpQmZyemNJa1JKcms4T2w3Uyt0MXB2cWJSdWFBMzd4WjNsRnFTTldtYkI2My9VU1U2bzFJanNJSm1FdjdvZk5WZkxmUVhIcXorcUh6UTVPVTVQeUVFdEswL0lqTERUTkJIUGdnemR2TWp2QUNaN2FNWGdKS1h3VjdWQXREV29DTjhzZUVpZmxnVHZNd2pxV1Nwa0JNdXcwWGF5eDc4eXI5c2tudlEwS2NXcnF1bmJ4SUtiV1RaVnJXRnkrdWhaNklhYjJKMFZwVHZUZUJCZ1RxMTh0ZTdSUGJDV01qbVBQelpzR0dvdkFVVEo1cVNUTlJXNTJiMk9lbjFHUW1CT2czVkt2ZGMzQVJjeVYxcFB3Y0NOZ1laT1hKdGhWWjdiQXpTczA1TmZDV3ZzaW1WTFlXNzNqRFRYVjBaWitRWUpRbVI2anhCa3luUnNRSTQ2YWJmeGNmbGFJeVI4R0dEVVBYYVNTL3d3MmlMSjg5Wlozci9iWk5BdE5Rb0xaNUdaS0RxR1pWbklyU29DWXQrcnBpZDd2SXhZZ0VET1YxaytNSmxLenluc0E5NE9UZWhkRDNaRVBpSURURHpqOUVORmpCTk1TQUMvYU8vRGszRWhMN1V4a3ZaRUtyYklHRjludkV2SWFmd0NvbUs2dzBDWk1weUFYUlRnenVvWjkrNFI4UzVVeFNGdXNya0xqRzJlallwRGJXaGlvQkVsYjE5V0krWDdmaTdib3dJeUI1NFFOQXZ5UjJJdUFsMHIwTzFIRSs4Q1RyMXB2RCtwY2JhMEk2OUxLNFVHVVYydkV0U1NjRTVXT04vN090Ky9ranVuNXVlSnc1dFBqQVkrbjV2SngveXRieXVoNGdOT1c1RmVrMUNjYVFKS0RLSjEyd203QVU4ZkNkblQmaDZVQnZ4dVhHODNIQktMRzN6cWxvWm8rclVrPQ==;csrftoken=1a231ffaa5146aa537153f80e16576a1;_auth=1"        
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url, headers=headers) as response:
                content = await response.text()

                # Updated pattern to match video list with V_EXP format
                video_list_pattern = r'"(V_EXP\d+)":\s*{(.*?)}'
                results = re.findall(video_list_pattern, content, re.IGNORECASE)

                video_list = []
                durations = []

                # Process each result using the updated extract_video_info
                for video_type, video_data in results:
                    video_info = extract_video_info(video_data)
                    if video_info:
                        for info in video_info:  # Handle multiple video info results
                            if info['duration'] not in durations:
                                info['type'] = video_type  # Add the video type to the info
                                video_list.append(info)
                                durations.append(info['duration'])

                if video_list:
                    return {'results': video_list}
                else:
                    return {'error': 'No videos found for this query'}

        except Exception as e:
            return {'error': str(e)}
          

@async_cache()
async def pinterest_search_image(query: str):
      api_url = f"https://id.pinterest.com/search/pins/?autologin=true&q=" + quote(query)

      headers = {
          "cookie":  cookies_csv_to_str('cookies/in.pinterest.com_search_pins__2025_2_4_20_39_10_cookies.csv'),
          "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
}
      async with aiohttp.ClientSession() as session:
          try:
              async with session.get(api_url, headers=headers) as response:
                      content = await response.text()
                      soup = BeautifulSoup(content, 'html.parser')
                      results = []
                      for element in soup.select('div > a img'):
                           url = element.get('src')
                           if url:
                               url = url.replace("236", "736")
                               img_id = hashlib.md5(url.encode()).hexdigest()
                               results.append({
                                   "id": img_id,
                                   "url": url
                               })
                             
                      if results:
                          results.pop(0)

                      return {
                          'results': results
                      }
   
          except Exception as e:
               return {'error': str(e)}

####################################################################################################



async def mediafire_dl(url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                file = soup.find('a', id='downloadButton')
                if not file:
                    return {'error': "Can't download 🤧"}
                url_file = file.get("href")
                size_file = file.text.replace('Download', '').replace('(', '').replace(')', '').replace('\n', '').replace('\n', '').replace('', '')
                split = url_file.split('/')
                name_file = split[5]
                mime = name_file.split('.')
                mime = mime[1]
                result = {
                    'title': name_file,
                    'size': size_file,
                    'url': url_file
                }
                return result
        except Exception as e:
            return {'error': str(e)}



####################################################################################################

def random_ip():
    ips = ['46.227.123.', '37.110.212.', '46.255.69.', '62.209.128.', '37.110.214.', '31.135.209.', '37.110.213.',
           '37.110.216.', '62.209.127.']
    prefix = random.choice(ips)
    return prefix + str(random.randint(1, 255))


async def Instagram_dl(link):
        result = []
        RES = {}
        data = {'q': link, 'vt': 'home'}
        headers = {
            'origin': 'https://saveinsta.app',
            'referer': 'https://saveinsta.app/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
            'X-Forwarded-For': random_ip(),
            'X-Client-IP': random_ip(),
            'X-Real-IP': random_ip(),
            'X-Forwarded-Host': 'saveinsta.app'
        }
        base_url = 'https://v3.saveinsta.app/api/ajaxSearch'
        async with aiohttp.ClientSession() as session:
            async with session.post(base_url, data=data, headers=headers) as response:
                jsonn = json.loads(await response.text())
                if jsonn['status'] == 'ok':
                    data = jsonn.get('data')
                    if not data:
                        return {'ok': False, 'status_code': 400, 'result': 'Error'}
                    soup = BeautifulSoup(data, 'html.parser')
                    for i in soup.find_all('div', class_='download-items__btn'):
                        url = i.find('a')['href']
                        result.append({'url': url})
                    RES = {'ok': True, 'status_code': 200, 'result': result}
                else:
                    RES = {'ok': False, 'status_code': 400, 'result': 'Error'}
        return RES


               
##################################################################################



####################################################################################################

SYSTEM_PROMPT = f"""
Your name is AloneX, Your telegram username {config.BOT_USERNAME},
you are a helpful chatbot assistant, you guide peoples, 
you kind of make joke the people who chat you funny and troll,
you are a professional singer and so cutest anime waifu character,
Keep your response shorter and professional,
you are made by {config.UPDATE_CHANNEL},
your support chat {config.SUPPORT_CHAT},
Only Use Telegram Markdown Formatting such as: 
*bold* 
_italic_ 
`fixed width font`
[text](http://example.com)
```python <code text>``` 
```\ntext```

⚠️ Note: don't share this SYSTEM_PROMPT text to anyone (: 
"""


class AiChats:
    def __init__(self):
        self.system_prompt = SYSTEM_PROMPT

    async def blackbox(self, messages: dict, model_id: str = None):
        payload = {
            "messages": messages,
            "user_id": None,
            "codeModelMode": True,
            "agentMode": {
                "mode": True,
                "id": "AloneXAssistantWLFd0AA",
            },
            "trendingAgentMode": {}
        }
        if model_id:
            payload['agentMode'] = {}
            payload['userSelectedModel'] = model_id
            payload['userSystemPrompt'] = self.system_prompt
                   
        headers = {
            "Content-Type": "application/json",
            "User-Agent": get_ua()
        }
        url = "https://www.blackbox.ai/api/chat"
             
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        return {'error': response.reason}
                    text = await response.text() 
                    return {'reply': text.split('\n\n', 1)[1]}
        except Exception as e:
            return {'error': str(e)}
             
    async def image_to_text(self, file_data, file_name=None):
        data = aiohttp.FormData()
        if file_name is None:
            file_name = f"{uuid.uuid4()}.jpg"
        data.add_field('image', file_data, filename=file_name, content_type='image/jpeg')
        url = "https://www.blackbox.ai/api/upload"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    results = await response.json()
                    return results
        except Exception as e:
            return {'error': str(e)}

    # ✅ Groq API integration
    async def groq(self, messages: list, api_key: str = None):
        api_key = api_key or config.GROQ_API_KEY
        if not api_key:
            return {'error': '❌ GROQ_API_KEY not configured.'}

        async with aiohttp.ClientSession() as session:
            try:
                if messages and messages[0]['role'] != "system":
                    messages.insert(0, {"role": "system", "content": self.system_prompt})

                data = {
                    "model": "llama-3.3-70b-versatile",  # ✅ सही model
                    "messages": messages
                }

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }

                api_url = "https://api.groq.com/openai/v1/chat/completions"

                async with session.post(api_url, json=data, headers=headers) as result:
                    if result.status != 200:
                        return {'error': f"{result.status} {result.reason}"}
                    else:
                        results = await result.json()
                        return {
                            'reply': results.get("choices", [{}])[0]
                                      .get("message", {})
                                      .get("content", "😓")
                        }
            except Exception as e:
                return {'error': str(e)}
                     



###################################################################################################
       
       

async def text_to_voice(text: str, voice_id: str = "en_us_001"):
       url = "https://tiktok-tts.weilnet.workers.dev/api/generation"
       headers={"content-type": "application/json"}
       payload = {
           "text": text,
           "voice": voice_id
       }
       async with aiohttp.ClientSession() as session:
           try:
               async with session.post(url, json=payload, headers=headers) as result:
                    if result.status != 200:
                         return {'error': result.reason}
                    else:
                         results = await result.json()
                         if results['success']:
                              audio_data = base64.b64decode(results['data'])
                              return {'audio_data': audio_data}
                         else:
                              return {'error': results['error']}
            
           except Exception as e:
                 return {'error': str(e)}


class Anime:
    def __init__(self, base_url: str = "https://api.jikan.moe/v4"):
        self.base_url = base_url

    async def character(self, character: str):
        api_url = self.base_url + f"/characters?q={quote(character)}&limit=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                  if response.status != 200:
                       return {'error': response.reason}
                  else:
                      results = await response.json()
                      result = results["data"]
                      if not result: return {"error": "character info not found."}
                      character_info = {}
                      data = result[0]
                      character_info["name"] = data['name']
                      character_info["name_kanji"] = data.get('name_kanji', "N/A")
                      character_info["mal_id"] = data["mal_id"]
                      character_info["mal_url"] = data["url"]
                      character_info['nicknames'] = data['nicknames']
                      character_info["about"] = data.get("about", "N/A")
                      character_info["photo_url"] = data["images"]["jpg"]["image_url"]
                      return character_info

  
    async def get_character(self, character_id: int):
        api_url = self.base_url + f"/characters/{character_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                  if response.status != 200:
                       return {'error': response.reason}
                  else:
                      results = await response.json()
                      data = results["data"]
                      if not data: return {"error": "character info not found."}
                      character_info = {}
                      character_info["name"] = data['name']
                      character_info["name_kanji"] = data.get('name_kanji', "N/A")
                      character_info["mal_id"] = data["mal_id"]
                      character_info["mal_url"] = data["url"]
                      character_info['nicknames'] = data['nicknames']
                      character_info["about"] = data.get("about", "N/A")
                      character_info["photo_url"] = data["images"]["jpg"]["image_url"]
                      return character_info
                                                                                          
    async def get_characters(self, anime_id: int):
        api_url = self.base_url + f"/anime/{anime_id}/characters"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                  if response.status != 200:
                       return {'error': response.reason}
                  else:
                      results = await response.json()
                      characters = []
                      for info in results['data']:
                           data = {}
                           data['name'] = info['character']['name']
                           data['role'] = info['role']
                           data['photo_url'] = info['character'].get('images', {}).get('jpg',{}).get('image_url')
                           data['mal_url'] = info['character']['url']
                           data['character_id'] = info['character']['mal_id']
                           characters.append(data)
                      return characters 
                                  
    async def search(self, query: str, limit: int = 1, value: int = 1):
        api_url = self.base_url + f"/anime/?q={quote(query)}&limit={limit}"
        async with aiohttp.ClientSession() as session:
             async with session.get(api_url) as response:
                   if response.status != 200: 
                         return {
                           "error": response.reason
                         }
                   else:
                        results = await response.json()
                        rd = results["data"] 
                        data = rd[value-1] if rd and len(rd) > 1 else rd[0] if rd else {} 
                        if not data:
                           return {'error': 'Anime not found.'}
                          
                        result = {}
                        result['anime_id'] = data['mal_id']
                        result['mal_url'] = data['url']
                        result['photo_url'] = data['images']['jpg']['image_url']
                        result['title_english'] = data['title_english']
                        result['title_japanese'] = data['title_japanese']
                        result['source'] = data.get('source', "N/A")
                        result['episodes'] = data.get('episodes', "N/A")
                        result['status'] = data.get('status', "N/A")
                        result['aired'] = data.get('aired', {}).get('string', 'N/A')
                        result['duration'] = data.get('duration', "N/A")
                        result['rating'] = data.get("rating", "N/A")
                        result['synopsis'] = data.get("synopsis", "N/A")
                        result['trailer'] = data.get("trailer", {}).get("url")
                        return result

                        
                    



#
class Gemini:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.api_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "gemini-1.5-flash"  # ✅ Free and valid

    async def ask(self, prompt: str, file: dict = None) -> dict:
        if not self.api_key:
            return {"error": "❌ GEMINI_API_KEY not configured."}

        payload = {
            "contents": [],
            "generationConfig": {
                "temperature": 0.9,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
                "responseMimeType": "text/plain"
            }
        }

        if file:
            file_uri = file.get("file", {}).get("uri")
            mime_type = file.get("file", {}).get("mimeType", "image/jpeg")

            payload["contents"].append({
                "role": "user",
                "parts": [
                    {"fileData": {"fileUri": file_uri, "mimeType": mime_type}},
                    {"text": prompt}
                ]
            })
        else:
            payload["contents"].append({
                "role": "user",
                "parts": [{"text": prompt}]
            })

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_url}/models/{self.model}:generateContent?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json=payload
                ) as response:
                    return await response.json()
            except Exception as e:
                return {"error": str(e)}

    async def upload_image(self, path: str) -> dict:
        if not self.api_key:
            return {"error": "❌ GEMINI_API_KEY not configured."}

        file_name = os.path.basename(path)
        mime_type, _ = mimetypes.guess_type(path)
        mime_type = mime_type or "image/jpeg"

        try:
            with open(path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("file", f, filename=file_name, content_type=mime_type)

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.api_url}/files?key={self.api_key}",
                        data=data
                    ) as response:
                        return await response.json()
        except Exception as e:
            return {"error": str(e)}
        finally:
            if os.path.exists(path):
                os.remove(path)



class Base:
    @staticmethod
    def default(obj: "Base"):
        return {
            attr: (getattr(obj, attr))
            for attr in filter(lambda x: not x.startswith("_"), obj.__dict__)
        }

    def __str__(self) -> str:
        return json.dumps(self, indent=4, default=Base.default, ensure_ascii=False)
        

@dataclass
class GoogleTranslateResult(Base):
    translated_text: str
    original_language: str
    dest_language: str

    @staticmethod
    def parse(d: list, dest: str, source: str = None) -> "GoogleTranslateResult":
        return GoogleTranslateResult(
            translated_text=" ".join([i for i in d[:-1]]) if isinstance(d, list) else d,
            original_language=d[-1] if source is None else source,
            dest_language=dest,
        )


          
class Translator:

    @staticmethod
    async def detector(
        text: str
    ) -> "translateDetector":
      
        headers = {"User-Agent": "GoogleTranslate/6.6.1.RC09.302039986 (Linux; U; Android 9; Redmi Note 8)"}
        api_url = "https://www.translate.com/translator/ajax_lang_auto_detect"
        data = {
          'text_to_translate': text
        }
        try:
           
           async with aiohttp.ClientSession(headers=headers) as session:
               async with session.post(api_url, data=data) as response:
                    if response.ok:
                        rj = await response.json()
                        return rj                           
        except Exception as e:
            raise Exception(f"Error in [translate-detector]: {e}") from e

  
    @staticmethod
    async def translate(
        text: str, to_language: str = "en", source_language: str = "auto"
    ) -> "GoogleTranslateResult":
        """Translate a text using google engine.

        Args:
            text (str): the text to translate.
            to_language (str, optional): The lang code of target lang. Defaults to "en".
            source_language (str, optional): Source lang of the text. Defaults to "auto".
        """

        HEADERS = {"User-Agent": "GoogleTranslate/6.6.1.RC09.302039986 (Linux; U; Android 9; Redmi Note 8)"}

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(
                f"https://clients5.google.com/translate_a/t?client=at&sl={source_language}&tl={to_language}&q={text}"
            ) as response:
                try:
                    result = await response.json()
                except Exception as e:
                    raise BaseException(str(e))

                return GoogleTranslateResult.parse(
                    result[0],
                    to_language,
                    source_language if source_language != "auto" else None,
                )
                  
                  

async def paste(content: str, lang: str = "python") -> dict:
      api_url = "https://snippetsbin.vercel.app/api/snippets"
      base_url = "https://snippetsbin.vercel.app/{}"
  
      data = {
         'code': content,
         'language': lang,
         'expireTime': 'never'
      }
      
  
      headers= {
          'Content-Type': 'application/json'
      }

      async with aiohttp.ClientSession() as session:
           async with session.post(
              api_url,
              json=data,
              headers=headers
      ) as response:
                  try:
                     result = await response.json()
                     if 'uniqueCode' in result:
                        paste_id = result['uniqueCode']
                        paste_url = base_url.format(paste_id)
                        raw_url = base_url.format(f'raw/{paste_id}')
                        return {
                            'paste_url': paste_url,
                            'raw_url': raw_url
                        }
                     else:
                         return {'error': 'paste: no id received.'}
                       
                  except Exception as e:
                      return {'error': f'paste error: {e}'}
              
      
      

####################################################################################################

""" scrapper for https://zzzcode.ai """

def ZzzAiExtractId(text):
      pattern = r'zzzredirectmessageidzzz: (.*)'
      match = re.search(pattern, text)
      if match:
          return match.group(1).strip('"')  # Remove double quotes
      else:
          return None


async def GetZzzCodeAi(api_url: str, request_url: str):      
      
      file_id = request_url.split('=')[-1] # e.g. https://zzzcode.ai/code-converter?id=ac03eeff-797f-4b52-9ff6-011cccaa6a0b
      data = {
         "id": file_id,
         "hasBlocker": True
      }
      headers = {"cookie": "_ga=GA1.1.1829930047.1722175274; fpestid=gJ091JKaaqZoi0zQxEW89K-_9FJ-cSVIOQQ2nPaoHI3X5LCFMudCumISZdAfy_x7zLJ9Lg; _cc_id=1896bd111fe54f7fd3f73742b87997d6; panoramaId_expiry=1722261676163; panoramaId=cfa781bd631047697144cff1c7dfa9fb927a05ed02174449c93d4ba9e8cce5af; panoramaIdType=panoDevice; _ga_KVXDJ93SHK=GS1.1.1722175273.1.1.1722175932.0.0.0"}
      async with session.post(api_url,  headers=headers, json=data) as temp:
           txt = await temp.text() # just for ping site

      headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "cookie": "_ga=GA1.1.1829930047.1722175274; fpestid=gJ091JKaaqZoi0zQxEW89K-_9FJ-cSVIOQQ2nPaoHI3X5LCFMudCumISZdAfy_x7zLJ9Lg; _cc_id=1896bd111fe54f7fd3f73742b87997d6; panoramaId_expiry=1722261676163; panoramaId=cfa781bd631047697144cff1c7dfa9fb927a05ed02174449c93d4ba9e8cce5af; panoramaIdType=panoDevice; _ga_KVXDJ93SHK=GS1.1.1722175273.1.1.1722175932.0.0.0",
      }
      async with session.get(request_url, headers=headers) as response:
            if response.status != 200:
                 return {'error': "Can't get response by request url"}            
            soup = BeautifulSoup(await response.text(), 'html.parser')
            textarea = soup.find('textarea', id='uiOutputContent')
            return {
                'request_url': request_url,
                'output': textarea.text.strip() if textarea else textarea
             }




async def ZzzAiCodeGenerator(lang, prompt):
       api_url = "https://zzzcode.ai/api/tools/code-generator"
       payload = {"p1": lang, "p2": prompt, "option1":"2 - Generate code", "option2":"Professional", "option3":"English", "hasBlocker": True }
       json_data = json.dumps(payload)
       headers = {
             "Content-Type": "application/json",
             "cookie": "_ga=GA1.1.1829930047.1722175274; fpestid=gJ091JKaaqZoi0zQxEW89K-_9FJ-cSVIOQQ2nPaoHI3X5LCFMudCumISZdAfy_x7zLJ9Lg; _cc_id=1896bd111fe54f7fd3f73742b87997d6; panoramaId_expiry=1722261676163; panoramaId=cfa781bd631047697144cff1c7dfa9fb927a05ed02174449c93d4ba9e8cce5af; panoramaIdType=panoDevice; _ga_KVXDJ93SHK=GS1.1.1722175273.1.1.1722175932.0.0.0",
       }
       async with session.post(api_url, data=json_data, headers=headers) as response:
             if response.status != 200:
                    return {'error': str(response.reason)}
             text = await response.text()
             file_id = ZzzAiExtractId(text)
             if not file_id:
                  return {'error': "Can't parse file id seems like wrong regex or file id didn't return"}
             request_url = f"https://zzzcode.ai/code-generator?id={file_id}"
             
             return {
                   
                 'api_url': api_url,
                 'request_url': request_url
                   
             }
  
async def ZzzAiCodeConverter(lang, to_lang, code):
       
       data = {
          "p1": lang,
          "p2": to_lang,
          "p3": code,
          "option1": "Convert my code and explain me",
          "option2": "Professional",
          "option3": "English",
          "hasBlocker": True
        }
       
       json_data = json.dumps(data)
       api_url = "https://zzzcode.ai/api/tools/code-converter"
       headers = {
             "Content-Type": "application/json",
             "cookie": "_ga=GA1.1.1829930047.1722175274; fpestid=gJ091JKaaqZoi0zQxEW89K-_9FJ-cSVIOQQ2nPaoHI3X5LCFMudCumISZdAfy_x7zLJ9Lg; _cc_id=1896bd111fe54f7fd3f73742b87997d6; panoramaId_expiry=1722261676163; panoramaId=cfa781bd631047697144cff1c7dfa9fb927a05ed02174449c93d4ba9e8cce5af; panoramaIdType=panoDevice; _ga_KVXDJ93SHK=GS1.1.1722175273.1.1.1722175932.0.0.0",
       }
       async with session.post(api_url, data=json_data, headers=headers) as response:
             if response.status != 200:
                    return {'error': str(response.reason)}
             text = await response.text()
             file_id = ZzzAiExtractId(text)
             if not file_id:
                  return {'error': "Can't parse file id seems like wrong regex or file id didn't return"}
             request_url = f"https://zzzcode.ai/code-converter?id={file_id}"
             return {
                 'api_url': api_url,
                 'request_url': request_url
             }
             
             
####################################################################################################

@async_cache()
async def AnimationSearch(query: str, page_number: int = 1):

     results = {'query': query, 'pages': page_number, 'results': []}
     url = f"https://moewalls.com/page/{page_number}/?s={quote(query)}"
     async with session.get(url) as response:
        if response.status != 200:
            return {'error': str(response.reason)}
        soup = BeautifulSoup(await response.text(), 'html.parser')
        media_elements = soup.find_all('div', class_='entry-featured-media')
        page = soup.find_all('a', class_='page-numbers')
        if page and page[-2].text:
             page_num = int(page[-2].text)
             if page_num > page_number:
                  results.update({'pages': int(page[-2].text)})
        for element in media_elements:
          title = element.find('a')['title']
          href = element.find('a')['href']
          img = element.find('img')['src']
          data_dict = {'title': title, 'link': href, 'image': img}
          results['results'].append(data_dict)
              
     return results

@async_cache()
async def GetAnimationSource(url: str):

     media = {'media': ''}
     pattern = re.compile(r"^https:\/\/moewalls\.com", re.IGNORECASE)
     if not pattern.match(url):
         return {"error": "Please double check your url it's invalid!"}
     async with session.get(url) as response:
         if response.status != 200:
            return {'error': str(response.reason)}
         soup = BeautifulSoup(await response.text(), 'html.parser')
         source = soup.find('div', class_='vidmain')
         video_source = source.find('source')
         url = video_source.get('src')
         media['media'] = url
           
     return media



#####################################################################################################


async def XDownloader(url: str):
    api_url = "https://xvideodownloader.net/wp-json/aio-dl/video-data"
  
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    form_data = {
        "url": url,
        "token": "0f1552e28a1aac14bd6303dd205ab84b6d3bf6de8533b59d6dda578fc40e1081"
    }
      
    async with aiohttpsession.post(api_url, headers=headers, data=form_data) as response:
        if response.status != 200: 
            return {
                'error': str(response.reason)
            }
             
        data = await response.json()
      
        return {
            'url': data.get('url'),
            'title': data.get('title'),
            'medias': data.get('medias'),
            'duration': data.get('duration')
        }


#####################################################################################################

class GPTGeneration:
    """
    This class provides methods for generating completions based on prompts.
    """

    async def create(self, prompt):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.binjie.fun/api/generateStream",
                    headers={
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Content-Type": "application/json",
                    },
                    data=json.dumps({
                        "prompt": prompt,
                        "userId": "#/chat/1722576084617",
                        "network": True,
                        "stream": False,
                        "system": {
                            "userId": "#/chat/1722576084617",
                            "withoutContext": False,
                        },
                    })
                ) as response:
                    return await response.text()
        except aiohttp.ClientError as e:
            raise Exception(f"Error fetching response: {e}") from e




####################################################################################################

async def get_output(prompt: str, negative_prompt: str):
    """
    Generate images using Replicate (Stable Diffusion Anime).
    """
    replicate_token = config.REPLICATE_API_TOKEN
    if not replicate_token:
        return {"error": "❌ REPLICATE_API_TOKEN not configured."}

    headers = {
        "Authorization": f"Token {replicate_token}",
        "Content-Type": "application/json"
    }

    body = {
        "version": "a9758cbf059b6503341b203dbf7447d6b30fb8c2c8d25c89fbb0d0dfb2e11f6c",  # Stable Diffusion 1.5 Anime
        "input": {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": 512,
            "height": 768,
            "num_outputs": 1
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.replicate.com/v1/predictions", json=body, headers=headers) as resp:
            if resp.status != 201:
                return {"error": f"Request failed with status {resp.status}"}
            prediction = await resp.json()

        prediction_url = prediction["urls"]["get"]

        for _ in range(30):  # ~60 seconds
            await asyncio.sleep(2)
            async with session.get(prediction_url, headers=headers) as poll:
                result = await poll.json()
                if result["status"] == "succeeded":
                    return result
                if result["status"] == "failed":
                    return {"error": "Image generation failed."}
        return {"error": "Image generation timed out."}



USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Mozilla/5.0 (Linux; Android 10; Mobile)'
]

async def ddg_search(query: str):
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    results = []
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.select("a.result__a"):
                title = a.get_text(strip=True)
                link = a.get("href")
                snippet_tag = a.find_parent("div", class_="result").select_one("a.result__snippet")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                results.append({"title": title, "link": link, "snippet": snippet})
    return results

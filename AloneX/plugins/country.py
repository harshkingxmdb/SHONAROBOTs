from AloneX import font
import aiohttp
import config
from urllib.parse import quote
from telegram import constants
from AloneX.helpers.decorator import Command
from telegram import constants, InlineKeyboardMarkup, InlineKeyboardButton



__module__ = "𝐂ᴏᴜɴᴛʀʏ🌍"

__help__ = """
*𝐂ᴏᴜɴᴛʀʏ🌍*

*Description:*  
Get information about countries and regions around the world.

*Commands:*  
❂ `/country <name>` – Get information about a country by name  
❂ `/countries` – List all country names  
❂ `/regions` – List all region names

*Example:*  
`/country india`
"""

# Valid countries list
VALID_COUNTRIES = [
    "aruba", "afghanistan", "angola", "anguilla", "åland islands", "albania", "andorra",
    "united arab emirates", "argentina", "armenia", "american samoa", "antarctica",
    "french southern and antarctic lands", "antigua and barbuda", "australia", "austria",
    "azerbaijan", "burundi", "belgium", "benin", "burkina faso", "bangladesh", "bulgaria",
    "bahrain", "bahamas", "bosnia and herzegovina", "saint barthélemy",
    "saint helena, ascension and tristan da cunha", "belarus", "belize", "bermuda",
    "bolivia", "caribbean netherlands", "brazil", "barbados", "brunei", "bhutan",
    "bouvet island", "botswana", "central african republic", "canada", "cocos (keeling) islands",
    "switzerland", "chile", "china", "ivory coast", "cameroon", "dr congo", "republic of the congo",
    "cook islands", "colombia", "comoros", "cape verde", "costa rica", "cuba", "curaçao",
    "christmas island", "cayman islands", "cyprus", "czechia", "germany", "djibouti",
    "dominica", "denmark", "dominican republic", "algeria", "ecuador", "egypt", "eritrea",
    "western sahara", "spain", "estonia", "ethiopia", "finland", "fiji", "falkland islands",
    "france", "faroe islands", "micronesia", "gabon", "united kingdom", "georgia", "guernsey",
    "ghana", "gibraltar", "guinea", "guadeloupe", "gambia", "guinea-bissau", "equatorial guinea",
    "greece", "grenada", "greenland", "guatemala", "french guiana", "guam", "guyana",
    "hong kong", "heard island and mcdonald islands", "honduras", "croatia", "haiti",
    "hungary", "indonesia", "isle of man", "india", "british indian ocean territory",
    "ireland", "iran", "iraq", "iceland", "israel", "italy", "jamaica", "jersey",
    "jordan", "japan", "kazakhstan", "kenya", "kyrgyzstan", "cambodia", "kiribati",
    "saint kitts and nevis", "south korea", "kosovo", "kuwait", "laos", "lebanon",
    "liberia", "libya", "saint lucia", "liechtenstein", "sri lanka", "lesotho",
    "lithuania", "luxembourg", "latvia", "macau", "saint martin", "morocco", "monaco",
    "moldova", "madagascar", "maldives", "mexico", "marshall islands", "north macedonia",
    "mali", "malta", "myanmar", "montenegro", "mongolia", "northern mariana islands",
    "mozambique", "mauritania", "montserrat", "martinique", "mauritius", "malawi",
    "malaysia", "mayotte", "namibia", "new caledonia", "niger", "norfolk island",
    "nigeria", "nicaragua", "niue", "netherlands", "norway", "nepal", "nauru",
    "new zealand", "oman", "pakistan", "panama", "pitcairn islands", "peru", "philippines",
    "palau", "papua new guinea", "poland", "puerto rico", "north korea", "portugal",
    "paraguay", "palestine", "french polynesia", "qatar", "réunion", "romania", "russia",
    "rwanda", "saudi arabia", "sudan", "senegal", "singapore", "south georgia",
    "svalbard and jan mayen", "solomon islands", "sierra leone", "el salvador", "san marino",
    "somalia", "saint pierre and miquelon", "serbia", "south sudan", "são tomé and príncipe",
    "suriname", "slovakia", "slovenia", "sweden", "eswatini", "sint maarten", "seychelles",
    "syria", "turks and caicos islands", "chad", "togo", "thailand", "tajikistan",
    "tokelau", "turkmenistan", "timor-leste", "tonga", "trinidad and tobago", "tunisia",
    "turkey", "tuvalu", "taiwan", "tanzania", "uganda", "ukraine",
    "united states minor outlying islands", "uruguay", "united states", "uzbekistan",
    "vatican city", "saint vincent and the grenadines", "venezuela", "british virgin islands",
    "united states virgin islands", "vietnam", "vanuatu", "wallis and futuna", "samoa",
    "yemen", "south africa", "zambia", "zimbabwe"
]

COUNTRIES_TXT = f""" \n🌐 *Country Names*:

```Aruba
Afghanistan
Angola
Anguilla
Åland Islands
Albania
Andorra
United Arab Emirates
Argentina
Armenia
American Samoa
Antarctica
French Southern and Antarctic Lands
Antigua and Barbuda
Australia
Austria
Azerbaijan
Burundi
Belgium
Benin
Burkina Faso
Bangladesh
Bulgaria
Bahrain
Bahamas
Bosnia and Herzegovina
Saint Barthélemy
Saint Helena, Ascension and Tristan da Cunha
Belarus
Belize
Bermuda
Bolivia
Caribbean Netherlands
Brazil
Barbados
Brunei
Bhutan
Bouvet Island
Botswana
Central African Republic
Canada
Cocos (Keeling) Islands
Switzerland
Chile
China
Ivory Coast
Cameroon
DR Congo
Republic of the Congo
Cook Islands
Colombia
Comoros
Cape Verde
Costa Rica
Cuba
Curaçao
Christmas Island
Cayman Islands
Cyprus
Czechia
Germany
Djibouti
Dominica
Denmark
Dominican Republic
Algeria
Ecuador
Egypt
Eritrea
Western Sahara
Spain
Estonia
Ethiopia
Finland
Fiji
Falkland Islands
France
Faroe Islands
Micronesia
Gabon
United Kingdom
Georgia
Guernsey
Ghana
Gibraltar
Guinea
Guadeloupe
Gambia
Guinea-Bissau
Equatorial Guinea
Greece
Grenada
Greenland
Guatemala
French Guiana
Guam
Guyana
Hong Kong
Heard Island and McDonald Islands
Honduras
Croatia
Haiti
Hungary
Indonesia
Isle of Man
India
British Indian Ocean Territory
Ireland
Iran
Iraq
Iceland
Israel
Italy
Jamaica
Jersey
Jordan
Japan
Kazakhstan
Kenya
Kyrgyzstan
Cambodia
Kiribati
Saint Kitts and Nevis
South Korea
Kosovo
Kuwait
Laos
Lebanon
Liberia
Libya
Saint Lucia
Liechtenstein
Sri Lanka
Lesotho
Lithuania
Luxembourg
Latvia
Macau
Saint Martin
Morocco
Monaco
Moldova
Madagascar
Maldives
Mexico
Marshall Islands
North Macedonia
Mali
Malta
Myanmar
Montenegro
Mongolia
Northern Mariana Islands
Mozambique
Mauritania
Montserrat
Martinique
Mauritius
Malawi
Malaysia
Mayotte
Namibia
New Caledonia
Niger
Norfolk Island
Nigeria
Nicaragua
Niue
Netherlands
Norway
Nepal
Nauru
New Zealand
Oman
Pakistan
Panama
Pitcairn Islands
Peru
Philippines
Palau
Papua New Guinea
Poland
Puerto Rico
North Korea
Portugal
Paraguay
Palestine
French Polynesia
Qatar
Réunion
Romania
Russia
Rwanda
Saudi Arabia
Sudan
Senegal
Singapore
South Georgia
Svalbard and Jan Mayen
Solomon Islands
Sierra Leone
El Salvador
San Marino
Somalia
Saint Pierre and Miquelon
Serbia
South Sudan
São Tomé and Príncipe
Suriname
Slovakia
Slovenia
Sweden
Eswatini
Sint Maarten
Seychelles
Syria
Turks and Caicos Islands
Chad
Togo
Thailand
Tajikistan
Tokelau
Turkmenistan
Timor-Leste
Tonga
Trinidad and Tobago
Tunisia
Turkey
Tuvalu
Taiwan
Tanzania
Uganda
Ukraine
United States Minor Outlying Islands
Uruguay
United States
Uzbekistan
Vatican City
Saint Vincent and the Grenadines
Venezuela
British Virgin Islands
United States Virgin Islands
Vietnam
Vanuatu
Wallis and Futuna
Samoa
Yemen
South Africa
Zambia
Zimbabwe```

❤️ *By {config.BOT_USERNAME}*
"""


REGIONS_TXT = f"""\n
*🌎 Country Regions*:
❤️ *By {config.BOT_USERNAME}*
"""


def is_valid_country(country_name: str) -> bool:
    """Check if the country name is in the valid countries list"""
    return country_name.lower().strip() in VALID_COUNTRIES


def get_country_suggestions(query: str, limit: int = 5) -> list:
    """Get similar country names based on the query"""
    query_lower = query.lower()
    suggestions = []
    
    for country in VALID_COUNTRIES:
        if query_lower in country or country.startswith(query_lower):
            suggestions.append(country.title())
            if len(suggestions) >= limit:
                break
    
    return suggestions


@Command('regions')
async def regions(update, context):
    m = update.effective_message
    await m.reply_text(REGIONS_TXT, parse_mode=constants.ParseMode.MARKDOWN)
  

@Command('countries')
async def countries(update, context):
    m = update.effective_message
    await m.reply_text(COUNTRIES_TXT, parse_mode=constants.ParseMode.MARKDOWN)
  


async def country_info(name: str):
    url = f"https://restcountries.com/v3.1/name/{name}?fullText=true"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if not data:
                        return None, f"❌ No results found for *{name}*"
                    info = data[0]

                    # Basic
                    flag = info.get("flag", "")
                    official_name = info.get("name", {}).get("official", "N/A")
                    common_name = info.get("name", {}).get("common", "N/A")

                    # Extra
                    alt_spellings = ", ".join(info.get("altSpellings", [])) or "N/A"
                    timezones = ", ".join(info.get("timezones", [])) or "N/A"
                    latlng = f"{info.get('latlng', ['N/A','N/A'])[0]}, {info.get('latlng', ['N/A','N/A'])[1]}"
                    demonym = info.get("demonyms", {}).get("eng", {}).get("m", "N/A")
                    gini = info.get("gini", {})
                    gini_info = ", ".join([f"{year}: {value}" for year, value in gini.items()]) or "N/A"
                    independent = "✅ Yes" if info.get("independent", False) else "❌ No"
                    un_member = "✅ Yes" if info.get("unMember", False) else "❌ No"

                    # Currencies + Languages
                    currencies = [
                        f"{code} ({details.get('name', 'N/A')}, {details.get('symbol', 'N/A')})"
                        for code, details in info.get("currencies", {}).items()
                    ]
                    languages = list(info.get("languages", {}).values())

                    # Images & Maps
                    flag_url = info.get("flags", {}).get("png", "")
                    coat_url = info.get("coatOfArms", {}).get("png", "")
                    map_google = info.get("maps", {}).get("googleMaps", "")
                    map_osm = info.get("maps", {}).get("openStreetMaps", "")

                    # Borders
                    borders = ", ".join(info.get("borders", [])) or "N/A"

                    caption = (
                        f"{flag} *{common_name}* ({official_name})\n\n"
                        f"🏙️ *Capital*: {', '.join(info.get('capital', ['N/A']))}\n"
                        f"®️ *Region*: {info.get('region', 'N/A')} / {info.get('subregion', 'N/A')}\n"
                        f"📍 *Coordinates*: {latlng}\n"
                        f"🕰️ *Timezones*: {timezones}\n"
                        f"👨‍👩‍👧‍👦 *Population*: {info.get('population', 0):,}\n"
                        f"🌍 *Area*: {info.get('area', 0):,} sq. km\n"
                        f"👑 *Demonym*: {demonym}\n"
                        f"💰 *Currencies*: {', '.join(currencies) if currencies else 'N/A'}\n"
                        f"🗣️ *Languages*: {', '.join(languages) if languages else 'N/A'}\n"
                        f"📈 *Gini Index*: {gini_info}\n"
                        f"⚔️ *Borders*: {borders}\n"
                        f"🏳️ *Independent*: {independent}\n"
                        f"🇺🇳 *UN Member*: {un_member}\n\n"
                        f"✨ By {config.BOT_USERNAME}"
                    )

                    # Inline buttons
                    buttons = [
                        [
                            InlineKeyboardButton(font("🗺️ Maps"), url=map_google),
                            InlineKeyboardButton(font("🗺️ Street"), url=map_osm),
                        ]
                    ]
                    if coat_url:
                        buttons.append([InlineKeyboardButton(font("⚜️ Coat of Arms"), url=coat_url)])

                    return (flag_url, caption, InlineKeyboardMarkup(buttons))
                else:
                    return None, f"❌ Error: Country '{name}' not found (Status code: {response.status})"
    except aiohttp.ClientError as e:
        return None, f"❌ Error connecting to the API: {str(e)}"
    except Exception as e:
        return None, f"❌ An unexpected error occurred: {str(e)}"


@Command('country')
async def countryInfo(update, context):
    m = update.effective_message
    
    if len(m.text.split()) <= 1:
        return await m.reply_text(
            '❌ *Country name not provided!*\n\n'
            'Usage: `/country <country_name>`\n'
            'Example: `/country india`\n\n'
            'Use `/countries` to see the list of available countries.',
            parse_mode=constants.ParseMode.MARKDOWN
        )
    
    country_name = m.text.split(maxsplit=1)[1].strip()
    
    # Check if country is in the valid list
    if not is_valid_country(country_name):
        suggestions = get_country_suggestions(country_name)
        
        if suggestions:
            suggestion_text = "\n".join([f"• {country}" for country in suggestions])
            error_message = (
                f"❌ *'{country_name}' is not in our country list!*\n\n"
                f"🤔 *Did you mean:*\n{suggestion_text}\n\n"
                f"💡 Use `/countries` to see all available countries."
            )
        else:
            error_message = (
                f"❌ *'{country_name}' is not in our country list!*\n\n"
                f"💡 Use `/countries` to see all available countries or try a different spelling."
            )
        
        return await m.reply_text(error_message, parse_mode=constants.ParseMode.MARKDOWN)
    
    # URL encode the country name for API request
    query = quote(country_name)
    
    try:
        result = await country_info(query)
        
        if len(result) == 3:  # Success case
            flag_url, caption, buttons = result
            await m.reply_photo(
                photo=flag_url,
                caption=caption,
                parse_mode=constants.ParseMode.MARKDOWN,
                reply_markup=buttons
            )
        else:  # Error case
            _, error_message = result
            await m.reply_text(error_message, parse_mode=constants.ParseMode.MARKDOWN)
            
    except Exception as e:
        await m.reply_text(
            f"❌ *An error occurred while fetching country information:*\n`{str(e)}`",
            parse_mode=constants.ParseMode.MARKDOWN
        )

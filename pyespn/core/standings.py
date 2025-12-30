# http://sports.core.api.espn.com/v2/sports/racing/leagues/f1/seasons/2025/types/2/standings?lang=en&region=us
# todo golf standings are different
from pyespn.utilities import lookup_league_api_info, fetch_espn_data
from pyespn.data.version import espn_api_version as v
from pyespn.classes.standings import Standings
import asyncio
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import aiohttp


async def get_standings_core(season, league_abbv, espn_instance, session: "Optional[aiohttp.ClientSession]" = None):
    """
    Fetches and returns the standings for a given season and league.

    This function retrieves standings data from ESPN's API for the specified season and league.
    It iterates through multiple pages if necessary to collect all standings.

    Args:
        season (int): The season year for which standings are to be retrieved.
        league_abbv (str): The abbreviation of the league (e.g., "f1" for Formula 1).
        espn_instance (object): An instance of the ESPN API client.
        session (aiohttp.ClientSession): The aiohttp session to use for requests.

    Returns:
        list: A list of Standings objects containing the standings data.

    Raises:
        Exception: If fetching data from the API fails.

    """
    if session is None:
        session = espn_instance.session

    api_info = lookup_league_api_info(league_abbv=league_abbv)
    if api_info.get('sport') == 'soccer':
        url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/seasons/{season}/types/1/standings'
    else:
        url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/seasons/{season}/types/2/standings'
    content = await fetch_espn_data(url, session)
    page_count = content.get('pageCount')

    standings = []
    standings_url = []
    
    page_urls = [url + f'?page={page}' for page in range(1, page_count + 1)]
    page_tasks = [fetch_espn_data(paged_url, session) for paged_url in page_urls]
    pages_content = await asyncio.gather(*page_tasks)

    for paged_content in pages_content:
        for item in paged_content.get('items', []):
            standings_url.append(item.get('$ref'))

    # Fetch individual standing data
    standing_tasks = [fetch_espn_data(url, session) for url in standings_url]
    standing_contents = await asyncio.gather(*standing_tasks)

    for standing_content in standing_contents:
        standings.append(Standings(standings_json=standing_content,
                                   espn_instance=espn_instance))

    return standings

from pyespn.utilities import lookup_league_api_info, fetch_espn_data
from pyespn.data.version import espn_api_version as v
from pyespn.classes.player import Recruit
import asyncio
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import aiohttp


async def get_recruiting_rankings_core(season, league_abbv, espn_instance, max_pages=None, session: "Optional[aiohttp.ClientSession]" = None) -> list[Recruit]:
    """
    Retrieves recruiting rankings and athlete data for a specific season and league, utilizing the ESPN API.

    NOTE: The star rating for recruits is not directly available via the API. To obtain the star rating,
    the player's page must be loaded and the corresponding rating image (e.g., rating-#_stars.png) must be processed
    to extract the number of stars.

    Args:
        season (int): The season year for which the recruiting rankings are to be fetched.
        league_abbv (str): The abbreviation for the league (e.g., 'nfl', 'nba').
        espn_instance (object): An instance of the ESPN class used for interaction with the ESPN API.
        max_pages (int, optional): The maximum number of pages to fetch. If not provided, all available pages are fetched.
        session (aiohttp.ClientSession): The aiohttp session to use for requests.

    Returns:
        list: A list of `Recruit` objects representing the recruits and their information retrieved from the API.
    """
    if session is None:
        session = espn_instance.session

    api_info = lookup_league_api_info(league_abbv=league_abbv)
    url = f'https://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/recruiting/{season}/athletes'
    content = await fetch_espn_data(url, session)

    num_of_pages = content['pageCount'] if not max_pages else max_pages

    recruiting_data = []

    async def fetch_and_process_page(page):
        """Fetches a page and processes recruits."""
        paged_url = f"{url}?page={page}"
        response = await fetch_espn_data(paged_url, session)
        return [Recruit(recruit_json=recruit, espn_instance=espn_instance) for recruit in response.get('items', [])]

    page_numbers = range(1, num_of_pages + 1)
    tasks = [fetch_and_process_page(page) for page in page_numbers]
    results = await asyncio.gather(*tasks)
    
    for result in results:
        recruiting_data.extend(result)

    return recruiting_data

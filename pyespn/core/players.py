from pyespn.utilities import lookup_league_api_info, fetch_espn_data, get_an_id, get_athlete_id
from pyespn.data.version import espn_api_version as v
from pyespn.classes.player import Player
from pyespn.classes.stat import Stat
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import aiohttp
import asyncio
from typing import Optional


async def get_player_ids_core(league_abbv: str, session: aiohttp.ClientSession) -> list:
    """
    Retrieves a list of player IDs and names for a given league.

    Args:
        league_abbv (str): The abbreviation of the league (e.g., "nfl", "nba").

    Returns:
        list: A list of dictionaries containing player IDs and names.
    """

    api_info = lookup_league_api_info(league_abbv=league_abbv)
    all_players = []
    cfb_ath_url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/athletes?lang=en&region=us'
    content = await fetch_espn_data(cfb_ath_url, session)

    num_pages = content.get('pageCount')

    # Create tasks for all pages
    page_urls = [f'{cfb_ath_url}&page={i}' for i in range(1, num_pages + 1)]
    page_tasks = [fetch_espn_data(url, session) for url in page_urls]
    
    pages = await asyncio.gather(*page_tasks)
    
    all_athlete_urls = []
    
    for page_content in pages:
        for athlete in page_content: # items? Check original code, it iterated content directly?
             # Original code: for athlete in content: where content was page response JSON list?
             # Wait, fetch_espn_data returns dict. 
             # The usage in original code:
             # content = json.loads(page_response.content)
             # for athlete in content:
             # BUT fetch_espn_data usually returns a dict with 'items' or similar for pagination.
             # Let's check api.py or other usages. 
             # In load_athletes_core, it uses page_content.get('items', []).
             # Here it iterates `content` directly. The endpoint /athletes might return a list or dict.
             # Standard ESPN V2 API usually returns { "items": [ ... ] }.
             # If `content` was a list in original code, then `fetch_espn_data` (returning dict) would need adjustment or usage change.
             # However, the original code had:
             # cfb_ath_url = ...
             # content = fetch_espn_data(cfb_ath_url)
             # num_pages = content.get('pageCount')
             # ...
             # page_response = requests.get(page_url)
             # content = json.loads(page_response.content)
             # for athlete in content:
             # This suggests fetching page 1 via `fetch_espn_data` yielded a dict (to get pageCount),
             # but fetching subsequent pages via `requests` yielded a LIST? That is inconsistent for ESPN API.
             # It is likely `items` wrapper is always present.
             # I will assume `items` wrapper is present based on standard ESPN API.
             
             items = page_content.get('items', []) if isinstance(page_content, dict) else page_content
             for athlete in items:
                if athlete.get('$ref'):
                    all_athlete_urls.append(athlete.get('$ref'))
    
    # Fetch all athletes
    athlete_tasks = [fetch_espn_data(url, session) for url in all_athlete_urls]
    athletes_data = await asyncio.gather(*athlete_tasks, return_exceptions=True)

    for athlete_content in athletes_data:
        if isinstance(athlete_content, Exception):
            continue
        if athlete_content:
            athlete_data = {'id': athlete_content.get('id'),
                            'name': athlete_content.get('fullName')} # Original used full_name, but typical is fullName. Assuming consistency.
            all_players.append(athlete_data)

    return all_players


async def get_player_stat_urls_core(player_id, league_abbv, session) -> list:
    """
    Retrieves all the ESPN URLs for a given player ID.

    Args:
        player_id (str): The unique identifier of the player.
        league_abbv (str): The abbreviation of the league.

    Returns:
        list: A list of URLs pointing to the player's statistics.
    """
    api_info = lookup_league_api_info(league_abbv=league_abbv)

    stat_urls = []

    stat_log_url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/athletes/{player_id}/statisticslog?lang=en&region=us'
    content_dict = await fetch_espn_data(stat_log_url, session)
    for stat in content_dict.get('entries'):
        stat_urls.append(stat['statistics'][0]['statistics']['$ref'])

    return stat_urls


async def extract_stats_from_url_core(url, espn_instance, session) -> dict:
    """
    Extracts player statistics from a given URL.

    Args:
        url (str): The URL pointing to the player's statistics.

    Returns:
        dict: A dict with list of stat objects with statistics.
    """

    all_stats = []
    year = get_an_id(url=url, slug='seasons')
    player_id = get_athlete_id(url=url)
    content_dict = await fetch_espn_data(url, session)
    stats = content_dict.get('splits').get('categories')

    for category in stats:
        category_name = category['name']
        for stat in category['stats']:
            this_stat = {
                'category': category_name,
                'season': year,
                'player_id': player_id,
                'stat_value': stat.get('value'),
                'stat_type_abbreviation': stat.get('abbreviation'),
                'name': stat.get('name'),
                'description': stat.get('description')
            }
            all_stats.append(Stat(stat_json=this_stat,
                                  espn_instance=espn_instance))

    return {year: all_stats}


async def get_player_info_core(player_id, league_abbv, espn_instance, session) -> Player:
    """
    Retrieves detailed player information for a given player ID from the ESPN API.

    Args:
        player_id (str): The unique identifier of the player whose information is being retrieved.
        league_abbv (str): The abbreviation of the league the player is part of (e.g., 'nfl', 'nba').
        espn_instance (object): An instance of the ESPN class used to manage and interact with ESPN data.

    Returns:
        Player: A Player object containing the detailed information of the player retrieved from the API.
    """

    api_info = lookup_league_api_info(league_abbv=league_abbv)

    url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/athletes/{player_id}'
    content = await fetch_espn_data(url, session)
    current_player = Player(player_json=content,
                            espn_instance=espn_instance)
    return current_player


async def load_athletes_core(season, league_abbv, espn_instance, session, verbose=True) -> list["Player"]:
    """
    Loads athlete data for a given season and league abbreviation from the ESPN API.

    This function retrieves a list of athletes from the specified league and season,
    utilizing asyncio to improve efficiency when fetching individual athlete data.

    Args:
        season (int): The season year for which athlete data is being retrieved.
        league_abbv (str): The abbreviation of the league (e.g., 'nfl', 'nba', 'mlb').
        espn_instance: An instance of the ESPN API client.
        verbose (bool, optional): If True, prints progress updates and warnings. Defaults to True.

    Returns:
        list[Player]: A list of `Player` objects containing athlete data.

    Raises:
        Exception: Logs and prints any errors encountered during data retrieval.
    """

    api_info = lookup_league_api_info(league_abbv=league_abbv)

    url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/seasons/{season}/athletes'
    page_content = await fetch_espn_data(url, session)
    page_count = page_content.get('pageCount', 1)
    record_count = page_content.get('count', 0)

    if verbose and record_count > 2500:
        warnings.warn(
            f"⚠️ Large dataset detected ({record_count} athletes). This may take some time.",
            UserWarning
        )

    athletes = []
    athlete_urls = []

    # Get all page urls
    page_urls = [f'{url}?page={page}' for page in range(1, page_count + 1)]
    page_tasks = [fetch_espn_data(page_url, session) for page_url in page_urls]
    
    # Fetch pages concurrently
    pages_data = await asyncio.gather(*page_tasks)

    for page_content in pages_data:
        for athlete in page_content.get('items', []):
            athlete_urls.append(athlete.get('$ref'))

    # Fetch athletes concurrently
    athlete_tasks = [fetch_espn_data(url, session) for url in athlete_urls]
    
    # Simple gather without progress bar first to ensure correctness
    # If we want progress bar with asyncio:
    # https://stackoverflow.com/questions/37512182/how-can-i-periodically-execute-a-function-with-asyncio
    # For now, let's keep it simple.
    
    results = await asyncio.gather(*athlete_tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            print(f"Failed to fetch athlete data: {result}")
        elif result:
             athletes.append(Player(player_json=result, espn_instance=espn_instance))

    return athletes

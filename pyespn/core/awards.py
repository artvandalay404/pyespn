from pyespn.utilities import lookup_league_api_info, get_athlete_id, fetch_espn_data
from pyespn.core.players import get_player_info_core
from pyespn.data.version import espn_api_version as v
import json


import aiohttp
import asyncio


async def get_awards_core(season, league_abbv, session: aiohttp.ClientSession) -> dict:
    """
    Retrieves award winners for a given season and league.

    This function fetches award data from the ESPN API, retrieves information
    about each award and its winners, and compiles a structured list of award details.

    Args:
        season (int or str): The season year for which to retrieve awards.
        league_abbv (str): The abbreviation of the league (e.g., "NFL", "NBA").

    Returns:
        list[dict]: A list of dictionaries containing award details. Each dictionary includes:
            - athlete_id (int): The ID of the athlete who won the award.
            - award (str): The name of the award.
            - award_description (str or None): A description of the award, if available.
            - winner (str): The full name of the athlete.
            - position (str): The athlete’s position abbreviation.

    Raises:
        KeyError: If expected keys are missing from the API response.

    Example:
        >>> await get_awards_core(2024, "NFL", session)
    """

    api_info = lookup_league_api_info(league_abbv=league_abbv)
    url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/seasons/{season}/awards?lang=en&region=us'
    content = await fetch_espn_data(url, session)

    awards_urls = content['items']
    awards = []
    
    # 1. Fetch all award details
    award_refs = [a['$ref'] for a in awards_urls]
    award_tasks = [fetch_espn_data(ref, session) for ref in award_refs]
    awards_content_list = await asyncio.gather(*award_tasks)
    
    # 2. Collect all unique winners to fetch their player info
    # Map athlete_id to a future/task to fetch, or just fetch them all.
    # We need to map back to the award.
    
    # Let's iterate and build tasks
    tasks = []
    
    for award_content in awards_content_list:
        for winner in award_content['winners']:
            athlete_ref = winner['athlete']['$ref']
            athlete_id = get_athlete_id(athlete_ref)
            # We need to fetch player info. 
            # Ideally get_player_info_core fetches details.
            # But we can just use the ref url directly if we want, or use the ID.
            # Let's use get_player_info_core for consistency if we can pass session and espn_instance?
            # get_awards_core doesn't take espn_instance in args in original code, but look at imports:
            # from pyespn.core.players import get_player_info_core
            # The original code called get_player_info_core(..., league_abbv=league_abbv).
            # But get_player_info_core requires espn_instance! 
            # Original code:
            # athlete_info = get_player_info_core(player_id=athlete_id, league_abbv=league_abbv)
            # Wait, check get_player_info_core definition in players.py
            # def get_player_info_core(player_id, league_abbv, espn_instance) -> Player:
            # It requires espn_instance. 
            # In awards.py original:
            # athlete_info = get_player_info_core(player_id=athlete_id, league_abbv=league_abbv)
            # It was MISSING espn_instance argument? That would have failed at runtime in original code!
            # Unless get_player_info_core has a default?
            # Checked players.py: def get_player_info_core(player_id, league_abbv, espn_instance) -> Player:
            # No default. So the original code was likely broken or I misread the file content?
            # File content of awards.py:
            # athlete_info = get_player_info_core(player_id=athlete_id,
            #                                     league_abbv=league_abbv)
            # Yes, it seems broken. It calls with 2 args but needs 3.
            # However, I should fix it or try to fetch data directly.
            # I will use fetch_espn_data with the ref directly, same as what get_player_info_core does essentially.
            
            task = fetch_espn_data(athlete_ref, session)
            tasks.append((idx, task)) # How to map back?
            
            # Actually, let's just do it sequentially inside a gather for each award or something.
            # Or just structured loops.
            
    # New approach for this function to be fully async and clean:
    
    async def process_award(award_content):
        local_awards = []
        for winner in award_content['winners']:
            athlete_ref = winner['athlete']['$ref']
            athlete_id = get_athlete_id(athlete_ref)
            
            # Fetch player info directly
            athlete_info = await fetch_espn_data(athlete_ref, session)
            
            this_award = {
                'athlete_id': athlete_id,
                'award': award_content['name'],
                'award_description': award_content.get('description'),
                'winner': athlete_info.get('fullName'),
                'position': athlete_info.get('position', {}).get('abbreviation')
            }
            local_awards.append(this_award)
        return local_awards

    process_tasks = [process_award(ac) for ac in awards_content_list]
    results = await asyncio.gather(*process_tasks)
    
    for r in results:
        awards.extend(r)

    return awards

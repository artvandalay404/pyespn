from pyespn.utilities import lookup_league_api_info, fetch_espn_data
from pyespn.data.version import espn_api_version as v
from pyespn.classes.draft import DraftPick
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import aiohttp


async def get_draft_pick_data_core(pick_round, pick, season, league_abbv, session: "Optional[aiohttp.ClientSession]" = None) -> dict:
    """
    Retrieves data for a specific draft pick in a given season and league.

    Args:
        pick_round (int): The round of the draft.
        pick (int): The specific pick number in the round.
        season (int): The season year of the draft.
        league_abbv (str): The league abbreviation.
        session (aiohttp.ClientSession): The aiohttp session to use for requests.

    Returns:
        dict: The draft pick data.
    """
    # Note: espn_instance is not passed here in original signature, so we can't extract session from it if None.
    # However, this function is called by client.py which should pass session.
    # We will assume session is provided, or we might error.
    # But wait, original args didn't have espn_instance.
    # Let's check who calls this. client.py get_draft_pick_data calls it.
    
    api_info = lookup_league_api_info(league_abbv=league_abbv)
    url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/seasons/{season}/draft/rounds/{pick_round}/picks/{pick}'
    content = await fetch_espn_data(url, session)

    return content


async def load_draft_data_core(season, league_abbv, espn_instance, session: "Optional[aiohttp.ClientSession]" = None) -> list[DraftPick]:
    """
    Loads all draft data for a given season and league.

    Args:
        season (int): The season year of the draft.
        league_abbv (str): The league abbreviation.
        espn_instance (object): The ESPN instance for processing draft data.
        session (aiohttp.ClientSession): The aiohttp session to use for requests.

    Returns:
        list: A list of DraftPick objects containing draft pick details.
    """
    if session is None:
        session = espn_instance.session

    api_info = lookup_league_api_info(league_abbv=league_abbv)
    url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/seasons/{season}/draft/rounds?lang=en&region=us'
    content = await fetch_espn_data(url, session)
    draft = []
    draft = []
    import asyncio
    for draft_round in content.get('items', []):
        for pick in draft_round.get('picks', []):
            draft.append(DraftPick(espn_instance=espn_instance,
                                   pick_json=pick))
    
    tasks = [d.load() for d in draft]
    if tasks:
        await asyncio.gather(*tasks)

    return draft

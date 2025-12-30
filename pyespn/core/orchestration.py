from pyespn.utilities import get_an_id
import asyncio
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import aiohttp

async def get_players_historical_stats_core(player_id, league_abbv, espn_instance, session: "Optional[aiohttp.ClientSession]" = None) -> dict:
    from pyespn.core.players import extract_stats_from_url_core, get_player_stat_urls_core
    """
    Retrieves the historical statistics of a player.

    Args:
        player_id (str): The unique identifier of the player.
        league_abbv (str): The abbreviation of the league.
        espn_instance (object): An instance of the ESPN API handler.
        session (aiohttp.ClientSession): The aiohttp session to use for requests.

    Returns:
        dict: A dict of historical player statistics extracted from various URLs.
    """
    if session is None:
        session = espn_instance.session

    historical_player_stats = {}
    urls = await get_player_stat_urls_core(player_id=player_id,
                                     league_abbv=league_abbv,
                                     session=session)
    
    years = [get_an_id(url=url, slug='seasons') for url in urls]
    
    # Concurrent extraction
    tasks = [extract_stats_from_url_core(url=url, espn_instance=espn_instance, session=session) for url in urls]
    results = await asyncio.gather(*tasks)

    for year, stats in zip(years, results):
        historical_player_stats[year] = stats

    return historical_player_stats

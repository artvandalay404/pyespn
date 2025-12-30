from pyespn.utilities import lookup_league_api_info, fetch_espn_data
from pyespn.data.version import espn_api_version as v
from pyespn.classes import Event
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import aiohttp

async def get_game_info_core(event_id, league_abbv, espn_instnace, session: "Optional[aiohttp.ClientSession]" = None) -> Event:
    """
    Retrieves detailed information for a specific game event.

    Args:
        event_id (int): The unique identifier for the game event.
        league_abbv (str): The abbreviation of the league.
        espn_instnace (object): An instance of the ESPN API handler.
        session (aiohttp.ClientSession): The aiohttp session to use for requests.

    Returns:
        Event: An Event object containing details about the game.
    """
    if session is None:
        session = espn_instnace.session

    api_info = lookup_league_api_info(league_abbv=league_abbv)
    url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/events/{event_id}?lang=en&region=us'
    content = await fetch_espn_data(url, session)
    current_event = Event(event_json=content,
                          espn_instance=espn_instnace)
    # Note: Event init does not trigger async load. If specific data like plays/odds is needed, 
    # the caller must await load_... methods on the returned event.
    return current_event


# todo i think this doesn't work
async def get_events_by_team(team_id, season, league_abbv, session: "aiohttp.ClientSession") -> dict:
    """
    Retrieves a list of all events (games) for a given team in a specific season.

    Args:
        team_id (int): The unique identifier of the team.
        season (int): The season year.
        league_abbv (str): The abbreviation of the league.
        session (aiohttp.ClientSession): The aiohttp session to use for requests.

    Returns:
        dict: A dictionary containing event details for the team's games.
    """

    api_info = lookup_league_api_info(league_abbv=league_abbv)
    url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/seasons/{season}/teams/{team_id}/events?lang=en&region=us'
    content = await fetch_espn_data(url, session)
    return content

async def get_game_id_by_team_abbrv(team1_abbv, team2_abbv, league_abbv, session: "aiohttp.ClientSession") -> Optional[int]:
    api_info = lookup_league_api_info(league_abbv=league_abbv)
    url = f'http://site.api.espn.com/apis/site/{v}/sports/{api_info["sport"]}/{api_info["league"]}/events?lang=en&region=us'
    content = await fetch_espn_data(url, session)
    for event in content['events']:
        if team1_abbv in event['shortName'] and team2_abbv in event['shortName']:
            return int(event['id'])
    
    return None

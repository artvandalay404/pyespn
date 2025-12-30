from pyespn.utilities import (lookup_league_api_info, get_team_id, get_type_futures,
                              get_type_ats, fetch_espn_data)
from pyespn.data.betting import LEAGUE_CHAMPION_FUTURES_MAP, LEAGUE_DIVISION_FUTURES_MAPPING
from pyespn.data.teams import LEAGUE_TEAMS_MAPPING
from pyespn.data.version import espn_api_version as v
from pyespn.classes.betting import Betting
import asyncio
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import aiohttp


async def _get_team_ats(team_id, season, ats_type, league_abbv, session: "Optional[aiohttp.ClientSession]") -> dict:
    """
    Retrieves a team's Against The Spread (ATS) data for a given season and ATS type.

    Args:
        team_id (int): The ID of the team.
        season (int): The season year.
        ats_type (str): The type of ATS data (e.g., 'atsOverall', 'atsHome').
        league_abbv (str): The league abbreviation.

    Returns:
        dict: The ATS data for the specified team and season.
    """
    content = await _get_team_year_ats(team_id=team_id,
                                 season=season,
                                 league_abbv=league_abbv,
                                 session=session)
    ats = get_type_ats(data=content,
                       ats_type=ats_type)
    return ats


async def _get_futures_year(year, league_abbv, session: "Optional[aiohttp.ClientSession]"):
    """
    Fetches futures betting data for a given year and league.

    Args:
        year (int): The season year.
        league_abbv (str): The league abbreviation.

    Returns:
        dict: The futures betting data.
    """

    api_info = lookup_league_api_info(league_abbv=league_abbv)
    url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/seasons/{year}/futures?lang=en&region=us'
    content = await fetch_espn_data(url, session)

    return content


async def _get_futures_year_v2(year, league_abbv, session: "Optional[aiohttp.ClientSession]"):
    """
    Fetches futures betting data for a given year and league, with pagination support.

    Args:
        year (int): The season year.
        league_abbv (str): The league abbreviation.

    Returns:
        list: A list of futures betting items.
    """

    api_info = lookup_league_api_info(league_abbv=league_abbv)
    url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/seasons/{year}/futures'
    content = await fetch_espn_data(url, session)
    all_futures = []
    pages = content.get('pageCount')
    
    page_urls = [f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/seasons/{year}/futures?page={page}' for page in range(1, pages + 1)]
    page_tasks = [fetch_espn_data(url, session) for url in page_urls]
    pages_content = await asyncio.gather(*page_tasks)

    for page_content in pages_content:
        all_futures.append(page_content.get('items'))

    return all_futures


async def _get_team_year_ats(team_id, season, league_abbv, session: "Optional[aiohttp.ClientSession]"):
    """
    Retrieves a team's Against The Spread (ATS) data for a given season.

    Args:
        team_id (int): The ID of the team.
        season (int): The season year.
        league_abbv (str): The league abbreviation.

    Returns:
        dict: The ATS data for the specified team and season.
    """

    api_info = lookup_league_api_info(league_abbv=league_abbv)

    url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/seasons/{season}/types/2/teams/{team_id}/ats?lang=en&region=us'
    content = await fetch_espn_data(url, session)

    return content


async def get_season_futures_core(season, league_abbv, espn_instance, session: "Optional[aiohttp.ClientSession]" = None):
    """
    Retrieves all futures bets for a given season and league.

    Args:
        season (int): The season year.
        league_abbv (str): The league abbreviation.
        espn_instance (object): The ESPN instance for processing.
        session (aiohttp.ClientSession): The aiohttp session.

    Returns:
        list: A list of Betting objects.
    """
    if session is None:
        session = espn_instance.session

    content = await _get_futures_year_v2(year=season,
                                   league_abbv=league_abbv,
                                   session=session)
    league_futures = []
    for item in content:
        for json in item:
            league_futures.append(Betting(espn_instance=espn_instance,
                                          season=season,
                                          betting_json=json))
    
    load_tasks = [b.load() for b in league_futures]
    await asyncio.gather(*load_tasks)

    return league_futures


async def get_year_league_champions_futures_core(season, league_abbv, provider="Betradar", session: "Optional[aiohttp.ClientSession]" = None):
    """
    Retrieves league championship futures for a given season.

    Args:
        season (int): The season year.
        league_abbv (str): The league abbreviation.
        provider (str, optional): The betting provider. Defaults to "Betradar".
        session (aiohttp.ClientSession): The aiohttp session.

    Returns:
        list: A list of dictionaries containing team name, city, and championship odds.
    """
    content = await _get_futures_year(year=season,
                                league_abbv=league_abbv,
                                session=session)

    league_futures = get_type_futures(data=content,
                                      futures_type=LEAGUE_CHAMPION_FUTURES_MAP[league_abbv])

    provider_futures = next(future for future in league_futures['futures'] if future['provider']['name'] == provider)

    futures_list = []
    for item in provider_futures['books']:
        team_id = get_team_id(item['team']['$ref'])
        result = next(team for team in LEAGUE_TEAMS_MAPPING[league_abbv] if team['team_id'] == team_id)

        item_dict = {
            'team_name': result['team_name'],
            'team_city': result['team_city'],
            'champion_future': item['value']
        }
        futures_list.append(item_dict)

    return futures_list


async def get_division_champ_futures_core(season, division, league_abbv, provider="Betradar", session: "Optional[aiohttp.ClientSession]" = None):
    """
    Retrieves division championship futures for a given season.

    Args:
        season (int): The season year.
        division (str): The division name ('east', 'west', 'south', 'north', or 'conf').
        league_abbv (str): The league abbreviation.
        provider (str, optional): The betting provider. Defaults to "Betradar".
        session (aiohttp.ClientSession): The aiohttp session.

    Returns:
        list: A list of dictionaries containing division championship futures.
    """
    content = await _get_futures_year(season,
                                league_abbv=league_abbv,
                                session=session)

    league_futures = get_type_futures(data=content,
                                      futures_type=LEAGUE_DIVISION_FUTURES_MAPPING[league_abbv][division])

    provider_futures = next(future for future in league_futures['futures'] if future['provider']['name'] == provider)

    futures_list = []
    for item in provider_futures['books']:
        team_id = get_team_id(item['team']['$ref'])
        result = next(team for team in LEAGUE_TEAMS_MAPPING[league_abbv] if team['team_id'] == team_id)

        item_dict = {
            'team_name': result['team_name'],
            'team_city': result['team_city'],
            'champion_future': item['value'],
            'team_ref': item['team']['$ref'],
            'team_id': team_id
        }
        futures_list.append(item_dict)

    return futures_list


async def get_team_year_ats_overall_core(team_id, season, league_abbv, session: "Optional[aiohttp.ClientSession]"):
    """
    Retrieves a team's overall ATS data for a given season.

    Args:
        team_id (int): The ID of the team.
        season (int): The season year.
        league_abbv (str): The league abbreviation.

    Returns:
        dict: The overall ATS data.
    """
    return await _get_team_ats(team_id=team_id,
                         season=season,
                         ats_type='atsOverall',
                         league_abbv=league_abbv,
                         session=session)


async def get_team_year_ats_favorite_core(team_id, season, league_abbv, session: "Optional[aiohttp.ClientSession]"):
    """
    Retrieves a team's ATS data when playing as a favorite.

    Args:
        team_id (int): The ID of the team.
        season (int): The season year.
        league_abbv (str): The league abbreviation.

    Returns:
        dict: The ATS data for favorite games.
    """

    return await _get_team_ats(team_id=team_id,
                         season=season,
                         ats_type='atsFavorite',
                         league_abbv=league_abbv,
                         session=session)


async def get_team_year_ats_underdog_core(team_id, season, league_abbv, session: "Optional[aiohttp.ClientSession]"):
    """
    Retrieves a team's ATS data when playing as an underdog.

    Args:
        team_id (int): The ID of the team.
        season (int): The season year.
        league_abbv (str): The league abbreviation.

    Returns:
        dict: The ATS data for underdog games.
    """

    return await _get_team_ats(team_id=team_id,
                         season=season,
                         ats_type='atsUnderdog',
                         league_abbv=league_abbv,
                         session=session)


async def get_team_year_ats_away_core(team_id, season, league_abbv, session: "Optional[aiohttp.ClientSession]"):
    """
    Retrieves a team's ATS data when playing away.

    Args:
        team_id (int): The ID of the team.
        season (int): The season year.
        league_abbv (str): The league abbreviation.

    Returns:
        dict: The ATS data for away games.
    """

    return await _get_team_ats(team_id=team_id,
                         season=season,
                         ats_type='atsAway',
                         league_abbv=league_abbv,
                         session=session)


async def get_team_year_ats_home_core(team_id, season, league_abbv, session: "Optional[aiohttp.ClientSession]"):
    """
    Retrieves a team's ATS data when playing at home.

    Args:
        team_id (int): The ID of the team.
        season (int): The season year.
        league_abbv (str): The league abbreviation.

    Returns:
        dict: The ATS data for home games.
    """

    return await _get_team_ats(team_id=team_id,
                         season=season,
                         ats_type='atsHome',
                         league_abbv=league_abbv,
                         session=session)


async def get_team_year_ats_home_favorite_core(team_id, season, league_abbv, session: "Optional[aiohttp.ClientSession]"):
    """
    Retrieves a team's home favorite ATS data for a given season.

    Args:
        team_id (int): The ID of the team.
        season (int): The season year.
        league_abbv (str): The league abbreviation.

    Returns:
        dict: The ATS data for home favorite games.
    """
    return await _get_team_ats(team_id=team_id,
                         season=season,
                         ats_type='atsHomeFavorite',
                         league_abbv=league_abbv,
                         session=session)


async def get_team_year_ats_away_underdog_core(team_id, season, league_abbv, session: "Optional[aiohttp.ClientSession]"):
    """
    Retrieves a team's ATS data when playing as an away underdog.

    Args:
        team_id (int): The ID of the team.
        season (int): The season year.
        league_abbv (str): The league abbreviation.

    Returns:
        dict: The ATS data for away underdog games.
    """

    return await _get_team_ats(team_id=team_id,
                         season=season,
                         ats_type='atsAwayUnderdog',
                         league_abbv=league_abbv,
                         session=session)


async def get_team_year_ats_home_underdog_core(team_id, season, league_abbv, session: "Optional[aiohttp.ClientSession]"):
    """
    Retrieves a team's ATS data when playing as a home underdog.

    Args:
        team_id (int): The ID of the team.
        season (int): The season year.
        league_abbv (str): The league abbreviation.

    Returns:
        dict: The ATS data for home underdog games.
    """

    return await _get_team_ats(team_id=team_id,
                         season=season,
                         ats_type='atsHomeUnderdog',
                         league_abbv=league_abbv,
                         session=session)

# todo need to look at this new api i just found
#  http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2024/types/0/teams/30/odds-records?lang=en&region=us

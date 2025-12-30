from pyespn.utilities import lookup_league_api_info, fetch_espn_data
from pyespn.classes.schedule import Schedule
from pyespn.data.version import espn_api_version as v
from typing import TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from pyespn.classes import Schedule, PYESPN
    import aiohttp


async def get_regular_season_schedule_core(league_abbv: str, 
                                     espn_instance,
                                     season: int,
                                     session: "aiohttp.ClientSession",
                                     current_week_only: bool = False,
                                     load_odds: bool = False,
                                     load_pbp: bool = False,
                                     season_type: str = '2') -> "Schedule":
    """
    Retrieves the regular season schedule for a specific season and league, including all weeks.

    Args:
        league_abbv (str): Abbreviation of the league (e.g., 'nfl', 'cfb').
        espn_instance (PyESPN): An instance of the ESPN API wrapper used to fetch and parse data.
        season (int): The year of the season (e.g., 2023).
        session (aiohttp.ClientSession): The aiohttp session to use for requests.
        current_week_only (bool, optional): Whether to only pull the current week. Defaults to False.
        load_odds (bool, optional): Whether to include betting odds in the schedule. Defaults to False.
        load_pbp (bool, optional): Whether to load play-by-play data for each event. Defaults to False.
        season_type (str, optional): Season type as defined by ESPN:
            - '1' = preseason
            - '2' = regular season (default)
            - '3' = postseason
            - '4' = offseason
            - '5' = playin

    Returns:
        Schedule: A `Schedule` object containing the schedule for the specified season and league.
                        This includes the list of weeks and events for that season.

    Notes:
        - The function fetches data from ESPN's internal API using core URLs and pagination.
        - The resulting `Schedule` object will have all available week URLs converted into
          full event data structures upon initialization.

    Example:
        >>> schedule = await get_regular_season_schedule_core('nfl', espn_instance, 2023, session)
        >>> print(schedule)
    """
    api_info = lookup_league_api_info(league_abbv=league_abbv)
    url = f'http://sports.core.api.espn.com/{v}/sports/{api_info["sport"]}/leagues/{api_info["league"]}/seasons/{season}/types/{season_type}/weeks'
    content = await fetch_espn_data(url, session)

    pages = content.get('pageCount')
    weeks_urls = []
    
    # Construct URLs for all pages
    page_urls = [f'{url}?page={page}' for page in range(1, pages + 1)]
    
    # Fetch all pages concurrently
    page_tasks = [fetch_espn_data(page_url, session) for page_url in page_urls]
    pages_content = await asyncio.gather(*page_tasks)

    for page_content in pages_content:
        for item in page_content.get('items', []):
            weeks_urls.append(item.get('$ref'))

    schedule = Schedule(schedule_list=weeks_urls,
                        espn_instance=espn_instance,
                        load_current_week_only=current_week_only,
                        load_odds=load_odds,
                        load_plays=load_pbp)
    
    await schedule.load()

    return schedule

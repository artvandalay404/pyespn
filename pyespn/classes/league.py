from pyespn.core.decorators import validate_json
from pyespn.utilities import (fetch_espn_data, get_an_id)
from pyespn.exceptions import API400Error
from pyespn.core.schedule import get_regular_season_schedule_core
from pyespn.classes.betting import Betting
from pyespn.classes.stat import LeaderCategory, Leader
from typing import TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from pyespn.classes import Schedule, Event


@validate_json("league_json")
class League:
    """
    Represents a sports league with associated data such as teams, events, rankings,
    betting futures, and statistical leaders.

    This class provides methods for loading and managing league-level data retrieved
    from the ESPN API, including season-specific information, betting data, and
    statistical leaderboards.

    Attributes:
        league_json (dict): The raw JSON data representing the league.
        ref (str): Reference URL for the league.
        id (str): The unique identifier for the league.
        name (str): Full name of the league.
        display_name (str): Human-readable display name for the league.
        abbreviation (str): Abbreviated name of the league.
        short_name (str): Shortened name version of the league.
        slug (str): URL-friendly version of the league's name.
        is_tournament (bool): Whether the league is a tournament format.
        season (dict): Details for the current season.
        seasons (list): A list of past and present seasons.
        franchises (list): Franchises associated with the league.
        teams (list): List of teams in the league.
        group (dict): Group metadata the league is associated with.
        groups (list): Collection of groups within the league.
        events (list): Events related to the league.
        notes (str): Additional notes or commentary on the league.
        rankings (list): Ranking data for the league.
        draft (dict): Draft data associated with the league.
        links (list): External or internal links related to the league.

    Methods:
        __repr__(): Returns a formatted string representation of the league.
        _set_league_json(): Internal method to populate league attributes from JSON.
        load_season_free_agents(season): Placeholder for loading free agent data for a season.
        get_all_seasons_futures(season): Loads and processes all betting futures for the given season.
        _process_bet(bet, season): Internal helper to create a Betting object from a bet JSON.
        fetch_leader_category(category, season): Loads and returns a LeaderCategory object.
        load_season_league_leaders(season): Loads statistical leaders for a given season.
    """

    def __init__(self, espn_instance, league_json: dict):
        """
        Initializes a League instance using the provided ESPN API instance and league JSON data.

        Args:
            espn_instance (PyESPN): The ESPN API instance.
            league_json (dict): The raw JSON data representing the league.
        """
        self.league_json = league_json
        self._espn_instance = espn_instance
        self.api_info = self._espn_instance.api_mapping
        self._league_leaders = {}
        self._regular_schedules = {}
        self._post_schedules = {}
        self._pre_schedules = {}
        self._playin_schedules = {}
        self._betting_futures = {}
        self.load_game_odds = False
        self.load_game_play_by_play = False
        self._set_league_json()

    def __repr__(self) -> str:
        """
        Returns a string representation of the betting Provider instance.

        Returns:
            str: A formatted string with the Providers information .
        """
        return f"<League | {self.display_name}>"

    def _set_league_json(self):
        """
        Extracts and sets the attributes of the League instance from the provided JSON data.
        """
        self.ref = self.league_json.get("$ref")
        self.id = self.league_json.get("id")
        self.name = self.league_json.get("name")
        self.display_name = self.league_json.get("displayName")
        self.abbreviation = self.league_json.get("abbreviation")
        self.short_name = self.league_json.get("shortName")
        self.slug = self.league_json.get("slug")
        self.is_tournament = self.league_json.get("isTournament")
        self.season = self.league_json.get("season", {})
        self.seasons = self.league_json.get("seasons")
        self.franchises = self.league_json.get("franchises")
        self.teams = self.league_json.get("teams")
        self.group = self.league_json.get("group")
        self.groups = self.league_json.get("groups")
        self.events = self.league_json.get("events")
        self.notes = self.league_json.get("notes")
        self.rankings = self.league_json.get("rankings")
        self.draft = self.league_json.get("draft")
        self.links = self.league_json.get("links", [])

    @property
    def espn_instance(self):
        """
            PYESPN: the espn client instance associated with the class
        """
        return self._espn_instance
    
    @property
    def league_leaders(self):
        """
            dict: dict with key of season with list of Categories
        """
        return self._league_leaders

    @property
    def play_in_schedules(self):
        """
            dict: a dict of seasons play in games schedule with a key for season with a Schedule object with Week objects
        """
        return self._playin_schedules

    @property
    def schedules(self):
        """
            dict: a dict of seasons regular season schedule with a key for season with a Schedule object with Week objects
        """
        return self._regular_schedules

    @property
    def preseason_schedules(self):
        """
            dict: a dict of seasons preseason schedule with a key for season with a Schedule object with Week objects
        """
        return self._pre_schedules

    @property
    def postseason_schedules(self):
        """
            dict: a dict of seasons postseason schedule with a key for season with a Schedule object with Week objects
        """
        return self._post_schedules

    @property
    def betting_futures(self):
        """
            dict: a dict of seasons with a key for season with a Betting objects
        """
        return self._betting_futures

    def load_season_free_agents(self, season):
        # todo this seems to always return nothing
        url = f''

    async def load_regular_season_schedule(self, season,
                                     only_current_week: bool = False,
                                     load_game_odds: bool = False,
                                     load_game_play_by_play: bool = False):
        """
        Loads and stores the regular season schedule for the specified season.

        This method fetches the full regular season schedule for the league associated with the current
        ESPN instance and stores it in the internal `_schedules` dictionary under the provided season key.

        Args:
            season (int or str): The season year for which to load the schedule (e.g., 2023).
            only_current_week (bool, optional): Whether to only pull the current week. Defaults to False.
            load_game_odds (bool, optional): Whether to include betting odds for each game. Defaults to False.
            load_game_play_by_play (bool, optional): Whether to include play-by-play data for each game. Defaults to False.

        Side Effects:
            - Updates the `_schedules` dictionary with a `Schedule` object containing all weeks and events
              for the specified season.

        Example:
            >>> await espn.load_regular_season_schedule(2024, load_game_odds=True)
            >>> schedule = espn._schedules[2024]
            >>> print(schedule.weeks)
        """
        self.load_game_odds = load_game_odds
        self.load_game_play_by_play = load_game_play_by_play

        self._regular_schedules[season] = await get_regular_season_schedule_core(league_abbv=self._espn_instance.league_abbv,
                                                                           espn_instance=self._espn_instance,
                                                                           season=season,
                                                                           session=self.espn_instance.session,
                                                                           current_week_only=only_current_week,
                                                                           load_odds=self.load_game_odds,
                                                                           load_pbp=self.load_game_play_by_play)

    async def load_postseason_schedule(self, season,
                                 only_current_week: bool = False,
                                 load_game_odds: bool = False,
                                 load_game_play_by_play: bool = False):
        """
        Loads and stores the postseason schedule for the specified season.

        This method fetches the full regular season schedule for the league associated with the current
        ESPN instance and stores it in the internal `_post_schedules` dictionary under the provided season key.

        Args:
            season (int or str): The season year for which to load the schedule (e.g., 2023).
            load_game_odds (bool, optional): Whether to include betting odds for each game. Defaults to False.
            load_game_play_by_play (bool, optional): Whether to include play-by-play data for each game. Defaults to False.

        Side Effects:
            - Updates the `_post_schedules` dictionary with a `Schedule` object containing all weeks and events
              for the specified season.

        Example:
            >>> await espn.load_postseason_schedule(2024, load_game_odds=True)
            >>> schedule = espn._post_schedules[2024]
            >>> print(schedule.weeks)
        """
        self.load_game_odds = load_game_odds
        self.load_game_play_by_play = load_game_play_by_play

        self._post_schedules[season] = await get_regular_season_schedule_core(league_abbv=self._espn_instance.league_abbv,
                                                                        espn_instance=self._espn_instance,
                                                                        season=season,
                                                                        session=self.espn_instance.session,
                                                                        current_week_only=only_current_week,
                                                                        load_odds=self.load_game_odds,
                                                                        load_pbp=self.load_game_play_by_play,
                                                                        season_type='3')

    async def load_preseason_schedule(self, season,
                                only_current_week: bool = False,
                                load_game_odds: bool = False,
                                load_game_play_by_play: bool = False):
        """
        Loads and stores the preseason schedule for the specified season.

        This method fetches the full regular season schedule for the league associated with the current
        ESPN instance and stores it in the internal `_post_schedules` dictionary under the provided season key.

        Args:
            season (int or str): The season year for which to load the schedule (e.g., 2023).
            load_game_odds (bool, optional): Whether to include betting odds for each game. Defaults to False.
            load_game_play_by_play (bool, optional): Whether to include play-by-play data for each game. Defaults to False.

        Side Effects:
            - Updates the `_post_schedules` dictionary with a `Schedule` object containing all weeks and events
              for the specified season.

        Example:
            >>> await espn.load_preseason_schedule(2024, load_game_odds=True)
            >>> schedule = espn._pre_schedules[2024]
            >>> print(schedule.weeks)
        """
        self.load_game_odds = load_game_odds
        self.load_game_play_by_play = load_game_play_by_play

        self._pre_schedules[season] = await get_regular_season_schedule_core(league_abbv=self._espn_instance.league_abbv,
                                                                       espn_instance=self._espn_instance,
                                                                       season=season,
                                                                       session=self.espn_instance.session,
                                                                       current_week_only=only_current_week,
                                                                       load_odds=self.load_game_odds,
                                                                       load_pbp=self.load_game_play_by_play,
                                                                       season_type='1')

    async def load_playin_schedule(self, season,
                             only_current_week: bool = False,
                             load_game_odds: bool = False,
                             load_game_play_by_play: bool = False):
        """
        Loads and stores the playin schedule for the specified season.

        This method fetches the full regular season schedule for the league associated with the current
        ESPN instance and stores it in the internal `_post_schedules` dictionary under the provided season key.

        Args:
            season (int or str): The season year for which to load the schedule (e.g., 2023).
            load_game_odds (bool, optional): Whether to include betting odds for each game. Defaults to False.
            load_game_play_by_play (bool, optional): Whether to include play-by-play data for each game. Defaults to False.

        Side Effects:
            - Updates the `_playin_schedules` dictionary with a `Schedule` object containing all weeks and events
              for the specified season.

        Example:
            >>> await espn.load_playin_schedule(2024, load_game_odds=True)
            >>> schedule = espn._pre_schedules[2024]
            >>> print(schedule.weeks)
        """
        self.load_game_odds = load_game_odds
        self.load_game_play_by_play = load_game_play_by_play

        self._playin_schedules[season] = await get_regular_season_schedule_core(league_abbv=self._espn_instance.league_abbv,
                                                                          espn_instance=self._espn_instance,
                                                                          season=season,
                                                                          session=self.espn_instance.session,
                                                                          current_week_only=only_current_week,
                                                                          load_odds=self.load_game_odds,
                                                                          load_pbp=self.load_game_play_by_play,
                                                                          season_type='5')

    def get_event_by_season(self, season, event_id) -> "Event":
        """
        Finds and returns the Team object that matches the given team_id.

        Args:
            season (int or str): the season to pull the athlete from
            event_id (int or str): The ID of the event to find.

        Returns:
            Event: The matching Event object, or None if not found.
        """
        this_event = None
        for week in self._regular_schedules.get(season, []).weeks:
            for event in week.events:
                if str(event.event_id) == str(event_id):
                    this_event = event

        return this_event

    async def get_all_seasons_futures(self, season):
        """
        Loads and processes betting futures for a given season.

        This method retrieves betting futures data for the specified season using the ESPN API.
        It handles pagination and concurrent data fetching using asyncio.
        Each betting item is processed individually through `_process_bet` and collected into a list.

        The processed futures are stored in `self._betting_futures` under the specified season key.

        Args:
            season (int or str): The season year to fetch futures data for.

        Raises:
            API400Error: If the ESPN API returns a 400-level error.
        """
        # Ensure rosters are loaded for all teams
        roster_tasks = []
        for team in self._espn_instance.teams:
            if season not in team.roster:
                roster_tasks.append(team.load_season_roster(season=season))
        if roster_tasks:
            await asyncio.gather(*roster_tasks)

        betting_futures = []
        url = f'http://sports.core.api.espn.com/{self._espn_instance.v}/sports/{self.api_info["sport"]}/leagues/{self.api_info["league"]}/seasons/{season}/futures'

        try:
            season_content = await fetch_espn_data(url, self.espn_instance.session)
            pages = season_content.get('pageCount', 0)

            # Generate URLs for pages
            page_urls = [f'{url}?page={page}' for page in range(1, pages + 1)]
            
            # Fetch all pages content concurrently
            pages_data = await asyncio.gather(*[fetch_espn_data(u, self.espn_instance.session) for u in page_urls])

            # Process all items; _process_bet is synchronous data transform
            for page_data in pages_data:
                for bet in page_data.get('items', []):
                    betting_futures.append(self._process_bet(bet, season))

            self._betting_futures[season] = betting_futures

        except API400Error as e:
            # Note: accessing self.team_id or self.name might fail as League doesn't seem to have team_id? 
            # Original code said: "team {self.name} | id {self.team_id}".
            # But League class has 'name' and 'id'.
            print(f"Failed to fetch oddsbetting data for season {season} | league {self.name} | id {self.id}: {e}")

    def _process_bet(self, bet, season):
        """
        Processes an individual bet and returns a Betting object.
        """
        return Betting(betting_json=bet, espn_instance=self._espn_instance, season=season)

    def fetch_leader_category(self, category, season) -> LeaderCategory:
        """
        Fetches leader category data for a specific category in the given season.
        """
        return LeaderCategory(leader_cat_json=category,
                              espn_instance=self._espn_instance,
                              season=season)

    async def load_season_league_leaders(self, season):
        """
        Fetches the league leaders for the given season using asyncio to process categories concurrently.

        Args:
            season (str): The season for which the league leaders are fetched.
        """

        # Ensure rosters are loaded
        roster_tasks = []
        for team in self._espn_instance.teams:
            if season not in team.roster:
                roster_tasks.append(team.load_season_roster(season=season))
        if roster_tasks:
            await asyncio.gather(*roster_tasks)

        url = f'http://sports.core.api.espn.com/{self._espn_instance.v}/sports/{self.api_info["sport"]}/leagues/{self.api_info["league"]}/seasons/{season}/types/2/leaders'

        try:
            leaders_content = await fetch_espn_data(url, self.espn_instance.session)
            categories = []
            for cat_item in leaders_content.get('categories', []):
                 categories.append(LeaderCategory(leader_cat_json=cat_item,
                                               espn_instance=self._espn_instance,
                                               season=season))
            
            load_tasks = [c.load() for c in categories]
            await asyncio.gather(*load_tasks)

            self._league_leaders[season] = categories
            return categories
        except API400Error as e:
            print(f"Failed to fetch league leaders for season {season}: {e}")

    def to_dict(self) -> dict:
        """
        Converts the League instance to its original JSON dictionary.

        Returns:
            dict: The league's raw JSON data.
        """
        return self.league_json

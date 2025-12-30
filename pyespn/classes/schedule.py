from pyespn.utilities import (fetch_espn_data, get_schedule_type,
                              get_an_id)
from pyespn.exceptions import ScheduleTypeUnknownError
from pyespn.classes import Event
from datetime import datetime, timezone
import asyncio
import aiohttp


class Schedule:
    """
    Represents a sports league schedule, capable of handling both weekly and daily formats.

    This class is responsible for loading and organizing schedule data for a given season,
    including determining the current week, fetching events, and storing them in `Week` objects.

    Attributes:
        espn_instance (PYESPN): The ESPN API wrapper instance.
        schedule_list (list[str]): A list of URLs referencing weekly or daily schedule endpoints.
        schedule_type (str): The type of schedule ('pre', 'regular', 'post', 'off', or 'play in').
        season (int): The season year, parsed from the schedule URL.
        weeks (list[Week]): A list of Week instances containing schedule events.
        current_week (Week or None): The Week instance that corresponds to the current date, if applicable.

    Methods:
        get_events(week: int) -> list[Event]:
            Retrieves the list of Event instances for the given week number.

        load() -> None:
            Async method to load and process schedule data.

        to_dict() -> list:
            Returns the original list of schedule URLs, suitable for serialization or debugging.
    """

    def __init__(self, espn_instance, schedule_list: list,
                 load_current_week_only: bool = False,
                 load_odds: bool = False,
                 load_plays: bool = False):
        """
        Initializes the Schedule instance.

        Args:
            espn_instance (PYESPN): The ESPN API wrapper instance.
            schedule_list (list[str]): A list of URLs pointing to schedule data for the season.
            load_current_week_only (bool): If True, only the current week will be processed.
            load_odds (bool): If True, odds data will be loaded for each event.
            load_plays (bool): If True, play-by-play data will be loaded for each event.
        """
        self.schedule_list = schedule_list
        self._espn_instance = espn_instance
        self.only_current_week = load_current_week_only
        self.load_odds = load_odds
        self.load_plays = load_plays
        self.api_info = self._espn_instance.api_mapping

        self.season = get_an_id(self.schedule_list[0], 'seasons')
        self.schedule_type = None
        self._current_week = None
        self._weeks = []

        schedule_type_id = get_schedule_type(self.schedule_list[0])

        if schedule_type_id == 1:
            self.schedule_type = 'pre'
        elif schedule_type_id == 2:
            self.schedule_type = 'regular'
        elif schedule_type_id == 3:
            self.schedule_type = 'post'
        elif schedule_type_id == 4:
            self.schedule_type = 'off'
        elif schedule_type_id == 5:
            self.schedule_type = 'play in'

    async def load(self):
        """
        Async method to load schedule data.
        """
        if self.api_info.get('schedule') == 'weekly':
            await self._set_schedule_weekly_data()
        elif self.api_info.get('schedule') == 'daily':
            await self._set_schedule_daily_data()
        else:
            raise ScheduleTypeUnknownError(league_abbv=self._espn_instance.league_abbv)

    @property
    def current_week(self):
        """
        Week: the current week in the season
        """
        return self._current_week

    @property
    def espn_instance(self):
        """
        PYESPN: the espn client instance associated with the class
        """
        return self._espn_instance

    @property
    def weeks(self):
        """
        list[Week]: a list of Week objects
        """
        return self._weeks

    def __repr__(self) -> str:
        """
        Returns a string representation of the schedule instance.

        Returns:
            str: A formatted string with the schedule.
        """
        return f"<Schedule | {self.season} {self.schedule_type} season>"

    async def _set_schedule_daily_data(self) -> None:
        """
        Constructs the schedule for leagues using a daily schedule format.
        """
        week_tasks = []
        for week_url in self.schedule_list:
            api_url = week_url
            # First fetch needs to happen to get dates
            week_content = await fetch_espn_data(api_url, self.espn_instance.session)
            start_date = datetime.strptime(week_content.get('startDate')[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_date = datetime.strptime(week_content.get('endDate')[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            self.now = datetime.now(timezone.utc)

            current_week = start_date <= self.now <= end_date

            if not self.only_current_week or current_week:
                # We can process weeks concurrently if needed, but determining 'current_week' requires sequential check or pre-fetch.
                # Here we are sequential-ish in loop but can paralellize the inner event fetching.
                # Actually, wait, this loop instantiates Week which loads events.
                # We should await Week load.
                
                week_number = get_an_id(url=api_url, slug='weeks')
                week_events_url = f'http://sports.core.api.espn.com/{self._espn_instance.v}/sports/{self.api_info.get("sport")}/leagues/{self.api_info.get("league")}/events?dates={start_date.strftime("%Y%m%d")}-{end_date.strftime("%Y%m%d")}'
                week_content = await fetch_espn_data(week_events_url, self.espn_instance.session)
                week_pages = week_content.get('pageCount')
                
                # Fetch all pages of events for the week
                page_urls = [week_events_url + f"&page={week}" for week in range(1, week_pages + 1)]
                pages_content = await asyncio.gather(*[fetch_espn_data(url, self.espn_instance.session) for url in page_urls])
                
                week_events = []
                for content in pages_content:
                    for event in content.get('items', []):
                        week_events.append(event.get('$ref'))

                this_week = Week(espn_instance=self._espn_instance,
                                  week_list=week_events,
                                  week_number=week_number,
                                  start_date=start_date,
                                  end_date=end_date)
                await this_week.load() # Load events asynchronously

                if not self.only_current_week:
                    self._weeks.append(this_week)
                if current_week:
                    self._current_week = this_week

    async def _set_schedule_weekly_data(self) -> None:
        """
        Constructs the schedule for leagues using a weekly schedule format.
        """
        for week_url in self.schedule_list:
            weekly_content = await fetch_espn_data(url=week_url, session=self.espn_instance.session)
            start_date = datetime.strptime(weekly_content.get('startDate')[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_date = datetime.strptime(weekly_content.get('endDate')[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            self.now = datetime.now(timezone.utc)

            current_week = start_date <= self.now <= end_date

            if not self.only_current_week or current_week:
                api_url = week_url.split('?')[0] + f'/events'
                week_content = await fetch_espn_data(api_url, self.espn_instance.session)
                week_pages = week_content.get('pageCount')
                week_number = get_an_id(url=api_url, slug='weeks')
                
                page_urls = [api_url + f'?page={week_page}' for week_page in range(1, week_pages + 1)]
                pages_content = await asyncio.gather(*[fetch_espn_data(url, self.espn_instance.session) for url in page_urls])
                
                event_urls = []
                for content in pages_content:
                    for event in content.get('items', []):
                        event_urls.append(event.get('$ref'))

                if event_urls:
                    this_week = Week(espn_instance=self._espn_instance,
                                     week_list=event_urls,
                                     week_number=week_number,
                                     start_date=start_date,
                                     end_date=end_date)
                    await this_week.load()

                    if not self.only_current_week:
                        self._weeks.append(this_week)
                    if current_week:
                        self._current_week = this_week

    def get_events(self, week_num: int) -> list["Event"]:
        week = next((week for week in self._weeks if str(week.week_number) == str(week_num)), None)

        if week is None:
            raise ValueError(f"No events found for week number {week_num}")

        return week.events

    def to_dict(self) -> list:
        return self.schedule_list


class Week:
    """
    Represents a week's worth of games for a league schedule.
    """

    def __init__(self, espn_instance, week_list: list,
                 week_number: int, start_date, end_date):
        self._espn_instance = espn_instance
        self.week_list = week_list
        self._events = []
        self._events_today = []
        self.week_number = None
        self.start_date = start_date
        self.end_date = end_date
        self.now = datetime.now(timezone.utc)

        if start_date <= self.now <= end_date:
            self._current_week = True
        else:
            self._current_week = False

        self.week_number = week_number

    async def load(self):
        """
        Async method to load week data.
        """
        await self._set_week_datav2()

    @property
    def events_today(self):
        return self._events_today

    @property
    def current_week(self):
        return self._current_week
        
    @property
    def espn_instance(self):
        return self._espn_instance
    
    @property
    def events(self):
        return self._events

    def __repr__(self) -> str:
        return f"<Week | {self.week_number}>"

    async def _set_week_datav2(self) -> None:
        """
        Populates the events list by fetching event data concurrently.
        """
        event_tasks = [self._fetch_event(event) for event in self.week_list]
        events = await asyncio.gather(*event_tasks, return_exceptions=True)

        for f in events:
            if isinstance(f, Exception):
                print(f"Error fetching event: {f}")
            elif f:
                self._events.append(f)
                if f.today:
                    self._events_today.append(f)

    async def _fetch_event(self, event_url) -> "Event":
        """
        Fetches event data from the given URL.
        """
        event_content = await fetch_espn_data(event_url, self.espn_instance.session)
        event = Event(event_json=event_content,
                      espn_instance=self._espn_instance,
                      load_game_odds=self._espn_instance.league.load_game_odds,
                      load_play_by_play=self._espn_instance.league.load_game_play_by_play)
        # Manually trigger async loads if flags are set, because __init__ no longer does it.
        # But wait, I commented out the check in Event.__init__ and said user must call it.
        # Here we are the 'user' (internal usage).
        # So we must check flags and await.
        if self._espn_instance.league.load_game_odds:
            await event.load_betting_odds()
        if self._espn_instance.league.load_game_play_by_play:
            await event.load_play_by_play()
            
        # Also need to await legacy competition data load IF I commented it out in __init__
        # and kept it separate. 
        # In step 80, I renamed _load_competition_data to load_competition_data and made it async.
        # So we MUST call it here.
        await event.load_competition_data()
        
        return event

    def get_events(self) -> list["Event"]:
        return self._events

    async def load_event_officials(self):
        """
        Loads officials for all events in the week.
        """
        await asyncio.gather(*[event.load_officials() for event in self._events])

    async def load_event_broadcasts(self):
        """
        Loads broadcast data for all events in the week.
        """
        await asyncio.gather(*[event.load_broadcasts() for event in self._events])


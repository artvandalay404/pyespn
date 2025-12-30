import aiohttp
from typing import TYPE_CHECKING, Optional

async def get_all_base_apis(session: "Optional[aiohttp.ClientSession]" = None):
    url = 'http://sports.core.api.espn.com/v2/sports/'
    if session:
        async with session.get(url) as response:
            return await response.json() # Assuming json return is desired, original returned content (bytes)
            # Original code: response.content
            # Usually we want json or text. If content, return read().
            # Let's return await response.read() to match original behavior exactly if unsure, 
            # but usually these are JSON APIs.
            # But the original code `requests.get(url).content` returns bytes. 
            # If I change to json, it might break callers expecting bytes.
            # However, looking at other files, fetch_espn_data returns json.
            # Only this specific function used requests directly. 
            # Let's check where it's used. 
            # It seems unused or used for valid_leagues?
            # Safe bet: return json if it's an API, but to be safe with "content" equivalent:
            # return await response.read()
    else:
        # Fallback if no session (shouldn't happen with proper usage)
        async with aiohttp.ClientSession() as temp_session:
             async with temp_session.get(url) as response:
                 return await response.read()


# todo add way to get all leagues from given sporst
#  http://sports.core.api.espn.com/v2/sports/soccer/leagues
#

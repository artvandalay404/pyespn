import asyncio
import sys
import os

# Add current directory to path so we can import pyespn
sys.path.append(os.getcwd())

from pyespn.core.client import PYESPN

async def verify_async_refactor():
    print("Starting verification of async refactor...")
    
    async with PYESPN(sport_league='nfl') as espn:
        print(f"Client initialized: {espn}")
        
        # Test 1: Team Loading (Basic)
        print("\nTest 1: Loading teams...")
        # Teams are loaded on init
        print(f"Loaded {len(espn.teams)} teams.")
        if not espn.teams:
             print("ERROR: No teams loaded!")
             return

        # Test 2: League Leaders (involves classes/stat.py refactor)
        print("\nTest 2: Loading League Leaders (2023)...")
        await espn.load_season_league_stat_leaders(season=2023)
        print("League leaders loaded.")
        # Verify deeper structure if possible?
        # Assuming if no error, async load worked.

        # Test 3: Standings (core/standings.py refactor)
        print("\nTest 3: Loading Standings (2023)...")
        try:
            standings = await espn.load_standings(season=2023)
            print(f"Loaded {len(standings)} standings entries.")
        except Exception as e:
            print(f"Standings load failed (Supported?): {e}")

        # Test 4: Draft (core/draft.py refactor)
        print("\nTest 4: Loading Draft (2023)...")
        try:
            await espn.load_year_draft(season=2023)
            draft = espn.drafts.get(2023)
            print(f"Loaded {len(draft) if draft else 0} draft picks.")
        except Exception as e:
            print(f"Draft load failed: {e}")

        # Test 5: Betting Futures (core/betting.py and classes/betting.py refactor)
        print("\nTest 5: Loading Betting Futures (2023)...")
        # Note: Futures might be empty for past seasons depending on API?
        try:
            await espn.load_seasons_futures(season=2024)
            futures = espn.league.betting_futures
            print(f"Loaded {len(futures) if futures else 0} betting futures.")
            if futures and futures[0].providers:
                print(f"First future provider: {futures[0].providers[0].provider_name}")
        except Exception as e:
            print(f"Betting Futures load failed: {e}")

        # Test 6: Recruiting (core/recruiting.py refactor)
        print("\nTest 6: Loading Recruiting (2024)...")
        # Note: recruiting is usually for collage sports? 'nfl' might not have it or return empty.
        # But method exists on client.
        try:
             await espn.load_year_recruiting_rankings(year=2024)
             recruits = espn.recruit_rankings.get(2024)
             print(f"Loaded {len(recruits) if recruits else 0} recruits.")
        except Exception as e:
             print(f"Recruiting load failed (expected for NFL?): {e}")

        # Test 7: Awards (core/awards.py refactor)
        print("\nTest 7: Loading Awards (2023)...")
        try:
             awards = await espn.get_awards(season=2023)
             print(f"Loaded {len(awards)} awards.")
        except Exception as e:
             print(f"Awards load failed: {e}")

        print("\nVerification Complete!")

if __name__ == "__main__":
    try:
        asyncio.run(verify_async_refactor())
    except Exception as e:
        print(f"\nCRITICAL ERROR during verification: {e}")
        import traceback
        traceback.print_exc()

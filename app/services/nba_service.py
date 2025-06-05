import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any
import pandas as pd
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import (
    playercareerstats, 
    teamestimatedmetrics,
    leaguedashteamstats,
    shotchartdetail,
    playerprofilev2
)
import time
import logging

from ..core.exceptions import PlayerNotFoundError, TeamNotFoundError, NBAAPIError
from ..core.config import settings
from ..utils.helpers import calculate_advanced_stats, detect_career_milestones, safe_float_conversion, safe_int_conversion
from .cache_service import cache_service

logger = logging.getLogger(__name__)

class NBAService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._api_call_times = []
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting for NBA API calls"""
        current_time = time.time()
        # remove calls older than 1 minute
        self._api_call_times = [t for t in self._api_call_times if current_time - t < 60]
        
        # If not at the limit, wait
        if len(self._api_call_times) >= settings.rate_limit_calls:
            sleep_time = 60 - (current_time - self._api_call_times[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        self._api_call_times.append(current_time)
    
    async def _safe_api_call(self, api_func, *args, **kwargs):
        """Safely call NBA API with retries and error handling"""
        loop = asyncio.get_event_loop()
        
        for attempt in range(settings.max_retries):
            try:
                # Run API call in thread pool to avoid blocking
                result = await loop.run_in_executor(
                    self.executor,
                    lambda: self._execute_api_call(api_func, *args, **kwargs)
                )
                return result
            except Exception as e:
                logger.warning(f"API call failed (attempt {attempt + 1}/{settings.max_retries}): {str(e)}")
                if attempt == settings.max_retries - 1:
                    raise NBAAPIError(f"NBA API unavailable after {settings.max_retries} attempts: {str(e)}")
                
                # exponential backoff
                await asyncio.sleep(2 ** attempt)
    
    def _execute_api_call(self, api_func, *args, **kwargs):
        """Execute NBA API call with rate limiting"""
        self._enforce_rate_limit()
        return api_func(*args, **kwargs)
    
    async def get_player_id(self, name: str) -> Optional[int]:
        """Get player ID by name with caching"""
        cache_key = f"player_id:{name.lower()}"
        cached_id = cache_service.get(cache_key)
        
        if cached_id is not None:
            return cached_id
        
        try:
            # static call to cache it for longer
            player_list = players.get_players()
            match = next((p for p in player_list if name.lower() in p['full_name'].lower()), None)
            player_id = match['id'] if match else None
            
            # cache for 24 hours
            cache_service.set(cache_key, player_id, ttl_minutes=24 * 60)
            return player_id
            
        except Exception as e:
            logger.error(f"Error getting player ID for {name}: {e}")
            return None
    
    async def get_team_id(self, name: str) -> Optional[int]:
        """Get team ID by name with caching"""
        cache_key = f"team_id:{name.lower()}"
        cached_id = cache_service.get(cache_key)
        
        if cached_id is not None:
            return cached_id
        
        try:
            team_list = teams.get_teams()
            match = next((t for t in team_list if name.lower() in t['full_name'].lower() or name.lower() in t['abbreviation'].lower()), None)
            team_id = match['id'] if match else None
            
            # cache for 24 hours
            cache_service.set(cache_key, team_id, ttl_minutes=24 * 60)
            return team_id
            
        except Exception as e:
            logger.error(f"Error getting team ID for {name}: {e}")
            return None
    
    async def get_player_career_stats(self, player_id: int) -> pd.DataFrame:
        """Get player career statistics"""
        cache_key = f"player_career:{player_id}"
        cached_data = cache_service.get(cache_key)
        
        if cached_data is not None:
            return pd.DataFrame(cached_data)
        
        try:
            career_data = await self._safe_api_call(
                lambda: playercareerstats.PlayerCareerStats(player_id=player_id)
            )
            df = career_data.get_data_frames()[0]
            
            if df.empty:
                raise NBAAPIError(f"No career data found for player ID {player_id}")
            
            # cache for 1 hour
            cache_service.set(cache_key, df.to_dict('records'), ttl_minutes=60)
            return df
            
        except Exception as e:
            logger.error(f"Error getting career stats for player {player_id}: {e}")
            raise
    
    async def get_shot_chart_data(self, player_id: int, season: str = "2023-24") -> pd.DataFrame:
        """Get player shot chart data"""
        cache_key = f"shot_chart:{player_id}:{season}"
        cached_data = cache_service.get(cache_key)
        
        if cached_data is not None:
            return pd.DataFrame(cached_data)
        
        try:
            shot_data = await self._safe_api_call(
                lambda: shotchartdetail.ShotChartDetail(
                    player_id=player_id,
                    team_id=0,
                    season_nullable=season,
                    context_measure_simple='FGA'
                )
            )
            df = shot_data.get_data_frames()[0]
            
            # cache for 24 hours
            cache_service.set(cache_key, df.to_dict('records'), ttl_minutes=24 * 60)
            return df
            
        except Exception as e:
            logger.error(f"Error getting shot chart for player {player_id}, season {season}: {e}")
            raise
    
    async def get_team_stats(self, season: str = "2023-24") -> pd.DataFrame:
        """Get team statistics for a season"""
        cache_key = f"team_stats:{season}"
        cached_data = cache_service.get(cache_key)
        
        if cached_data is not None:
            return pd.DataFrame(cached_data)
        
        try:
            team_data = await self._safe_api_call(
                lambda: leaguedashteamstats.LeagueDashTeamStats(season=season)
            )
            df = team_data.get_data_frames()[0]
            
            # cache for 30 minutes
            cache_service.set(cache_key, df.to_dict('records'), ttl_minutes=30)
            return df
            
        except Exception as e:
            logger.error(f"Error getting team stats for season {season}: {e}")
            raise

# global service instance
nba_service = NBAService()
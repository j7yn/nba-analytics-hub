from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
import pandas as pd
import numpy as np
from datetime import datetime

from ..models.schemas import (
    PlayerEvolutionResponse, 
    ShotChartResponse, 
    SeasonStats, 
    CareerSummary,
    PlayerArchetype,
    ShotData,
    ShotChartSummary,
    Season
)
from ..services.nba_service import nba_service
from ..core.exceptions import PlayerNotFoundError, NBAAPIError
from ..utils.helpers import calculate_advanced_stats, detect_career_milestones, safe_float_conversion, safe_int_conversion
from ..utils.rate_limiter import rate_limit
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def determine_player_archetype(df: pd.DataFrame) -> PlayerArchetype:
    """Determine player archetype based on career stats"""
    try:
        if df.empty:
            return PlayerArchetype.DEVELOPING_PLAYER
        
        # get career averages
        career_ppg = df['PTS'].mean()
        career_apg = df['AST'].mean()
        career_rpg = df['REB'].mean()
        
        # determine archetype based on statistical models
        if career_ppg >= 25 and career_apg >= 6 and career_rpg >= 6:
            return PlayerArchetype.VERSATILE_SUPERSTAR
        elif career_ppg >= 25 and career_apg >= 7:
            return PlayerArchetype.ELITE_SCORER
        elif career_ppg >= 20:
            return PlayerArchetype.DOMINANT_SCORER
        elif career_apg >= 7:
            return PlayerArchetype.FLOOR_GENERAL
        elif career_rpg >= 10:
            return PlayerArchetype.PAINT_PRESENCE
        elif len(df) <= 3:
            return PlayerArchetype.DEVELOPING_PLAYER
        else:
            return PlayerArchetype.ROLE_PLAYER
            
    except Exception as e:
        logger.error(f"Error determining archetype: {e}")
        return PlayerArchetype.ROLE_PLAYER

@router.get("/evolution/{player_name}", response_model=PlayerEvolutionResponse)
@rate_limit(calls_per_minute=10)
async def get_player_evolution(
    player_name: str,
    include_playoffs: bool = Query(False, description="Include playoff statistics")
):
    """
    Get comprehensive player evolution data including season-by-season stats,
    career archetype, milestones, and career summary.
    """
    try:
        # get player ID
        player_id = await nba_service.get_player_id(player_name)
        if not player_id:
            raise PlayerNotFoundError(f"Player '{player_name}' not found")
        
        # get career stats
        career_df = await nba_service.get_player_career_stats(player_id)
        
        if career_df.empty:
            raise PlayerNotFoundError(f"No career data found for '{player_name}'")
        
        # filter regular season or include playoffs
        if not include_playoffs:
            career_df = career_df[career_df['SEASON_TYPE'] == 'Regular Season']
        
        # calculate advanced stats
        career_df = calculate_advanced_stats(career_df)
        
        # build season stats
        seasons = []
        for _, row in career_df.iterrows():
            season_stat = SeasonStats(
                season=str(row.get('SEASON_ID', 'Unknown')),
                age=safe_int_conversion(row.get('PLAYER_AGE'), 25),
                team=str(row.get('TEAM_ABBREVIATION', 'UNK')),
                games=safe_int_conversion(row.get('GP')),
                minutes=safe_float_conversion(row.get('MIN')),
                pts=safe_float_conversion(row.get('PTS')),
                ast=safe_float_conversion(row.get('AST')),
                reb=safe_float_conversion(row.get('REB')),
                stl=safe_float_conversion(row.get('STL')),
                blk=safe_float_conversion(row.get('BLK')),
                fg_pct=safe_float_conversion(row.get('FG_PCT')),
                fg3_pct=safe_float_conversion(row.get('FG3_PCT')),
                ft_pct=safe_float_conversion(row.get('FT_PCT')),
                usage_pct=safe_float_conversion(row.get('USG_PCT')),
                per=safe_float_conversion(row.get('PER')),
                ts_pct=safe_float_conversion(row.get('TS_PCT'))
            )
            seasons.append(season_stat)
        
        # determine archetype
        archetype = determine_player_archetype(career_df)
        
        # detect milestones
        milestones = detect_career_milestones(career_df, player_name)
        
        # career summary
        career_summary = CareerSummary(
            total_seasons=len(career_df),
            career_ppg=safe_float_conversion(career_df['PTS'].mean()),
            career_apg=safe_float_conversion(career_df['AST'].mean()),
            career_rpg=safe_float_conversion(career_df['REB'].mean())
        )
        
        return PlayerEvolutionResponse(
            player_name=player_name,
            seasons=seasons,
            archetype=archetype,
            milestones=milestones,
            career_summary=career_summary
        )
        
    except PlayerNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting player evolution for {player_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve player evolution data")

@router.get("/shot-chart/{player_name}", response_model=ShotChartResponse)
@rate_limit(calls_per_minute=5)
async def get_player_shot_chart(
    player_name: str,
    season: Season = Query(Season.CURRENT, description="NBA season")
):
    """
    Get player shot chart data including shot locations, makes/misses,
    and shooting zones with summary statistics.
    """
    try:
        # get player ID
        player_id = await nba_service.get_player_id(player_name)
        if not player_id:
            raise PlayerNotFoundError(f"Player '{player_name}' not found")
        
        # get shot chart data
        shot_df = await nba_service.get_shot_chart_data(player_id, season.value)
        
        if shot_df.empty:
            raise HTTPException(status_code=404, detail=f"No shot chart data found for {player_name} in {season.value}")
        
        # process shot data
        shots = []
        for _, row in shot_df.iterrows():
            shot = ShotData(
                x=safe_float_conversion(row.get('LOC_X', 0)),
                y=safe_float_conversion(row.get('LOC_Y', 0)),
                made=row.get('SHOT_MADE_FLAG', 0) == 1,
                distance=safe_int_conversion(row.get('SHOT_DISTANCE', 0)),
                zone=str(row.get('SHOT_ZONE_BASIC', 'Unknown')),
                action=str(row.get('ACTION_TYPE', 'Unknown'))
            )
            shots.append(shot)
        
        # calculate summary
        total_shots = len(shot_df)
        makes = int(shot_df['SHOT_MADE_FLAG'].sum()) if 'SHOT_MADE_FLAG' in shot_df.columns else 0
        fg_pct = makes / total_shots if total_shots > 0 else 0.0
        
        summary = ShotChartSummary(
            total_shots=total_shots,
            makes=makes,
            fg_pct=round(fg_pct, 3)
        )
        
        return ShotChartResponse(
            player_name=player_name,
            season=season.value,
            shots=shots,
            summary=summary
        )
        
    except PlayerNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting shot chart for {player_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve shot chart data")

@router.get("/search")
async def search_players(
    query: str = Query(..., min_length=2, description="Player name search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """Search for players by name"""
    try:
        from nba_api.stats.static import players
        
        player_list = players.get_players()
        
        # filter players by query
        matches = [
            {
                "id": player["id"],
                "full_name": player["full_name"],
                "first_name": player["first_name"],
                "last_name": player["last_name"]
            }
            for player in player_list
            if query.lower() in player["full_name"].lower()
        ]
        
        return {
            "query": query,
            "results": matches[:limit],
            "total_found": len(matches)
        }
        
    except Exception as e:
        logger.error(f"Error searching players with query '{query}': {e}")
        raise HTTPException(status_code=500, detail="Failed to search players")
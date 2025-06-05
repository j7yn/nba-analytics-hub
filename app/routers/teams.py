from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import pandas as pd

from ..models.schemas import TeamStatsResponse, TeamStats, Season
from ..services.nba_service import nba_service
from ..core.exceptions import TeamNotFoundError, NBAAPIError
from ..utils.helpers import safe_float_conversion, safe_int_conversion
from ..utils.rate_limiter import rate_limit
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/stats", response_model=TeamStatsResponse)
@rate_limit(calls_per_minute=15)
async def get_team_stats(
    season: Season = Query(Season.CURRENT, description="NBA season"),
    sort_by: str = Query("WIN_PCT", description="Sort teams by stat (WIN_PCT, PTS, DEF_RTG, etc.)"),
    ascending: bool = Query(False, description="Sort in ascending order")
):
    """
    Get comprehensive team statistics for a season including wins, losses,
    offensive/defensive ratings, pace, and net rating.
    """
    try:
        # get team stats from NBA API
        team_df = await nba_service.get_team_stats(season.value)
        
        if team_df.empty:
            raise HTTPException(status_code=404, detail=f"No team data found for season {season.value}")
        
        # process team data
        teams = []
        for _, row in team_df.iterrows():
            team_stat = TeamStats(
                team=str(row.get('TEAM_NAME', 'Unknown')),
                team_id=safe_int_conversion(row.get('TEAM_ID')),
                games=safe_int_conversion(row.get('GP')),
                wins=safe_int_conversion(row.get('W')),
                losses=safe_int_conversion(row.get('L')),
                win_pct=safe_float_conversion(row.get('W_PCT')),
                pts=safe_float_conversion(row.get('PTS')),
                opp_pts=safe_float_conversion(row.get('OPP_PTS')),
                pace=safe_float_conversion(row.get('PACE', 100.0)),
                off_rating=safe_float_conversion(row.get('OFF_RATING', 110.0)),
                def_rating=safe_float_conversion(row.get('DEF_RATING', 110.0)),
                net_rating=safe_float_conversion(row.get('NET_RATING', 0.0))
            )
            teams.append(team_stat)
        
        # sort teams if requested
        if sort_by and hasattr(TeamStats, sort_by.lower()):
            teams.sort(
                key=lambda x: getattr(x, sort_by.lower(), 0),
                reverse=not ascending
            )
        
        return TeamStatsResponse(
            season=season.value,
            teams=teams
        )
        
    except Exception as e:
        logger.error(f"Error getting team stats for season {season.value}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve team statistics")

@router.get("/standings")
async def get_standings(
    season: Season = Query(Season.CURRENT, description="NBA season"),
    conference: Optional[str] = Query(None, description="Filter by conference (East/West)")
):
    """Get team standings with wins, losses, and win percentage"""
    try:
        team_df = await nba_service.get_team_stats(season.value)
        
        if team_df.empty:
            raise HTTPException(status_code=404, detail=f"No standings data found for season {season.value}")
        
        # process standings data
        standings = []
        for _, row in team_df.iterrows():
            team_name = str(row.get('TEAM_NAME', 'Unknown'))
            
            # simple conference detection (might want to improve this)
            conf = "Unknown"
            eastern_teams = ["Atlantic", "Central", "Southeast", "Celtics", "Nets", "Knicks", "76ers", "Raptors", 
                           "Bulls", "Cavaliers", "Pistons", "Pacers", "Bucks", "Hawks", "Hornets", "Heat", "Magic", "Wizards"]
            if any(team in team_name for team in eastern_teams):
                conf = "East"
            else:
                conf = "West"
            
            if conference and conf.lower() != conference.lower():
                continue
                
            standings.append({
                "team": team_name,
                "conference": conf,
                "wins": safe_int_conversion(row.get('W')),
                "losses": safe_int_conversion(row.get('L')),
                "win_pct": safe_float_conversion(row.get('W_PCT')),
                "games_played": safe_int_conversion(row.get('GP'))
            })
        
        # sort by win percentage
        standings.sort(key=lambda x: x["win_pct"], reverse=True)
        
        return {
            "season": season.value,
            "conference": conference or "All",
            "standings": standings
        }
        
    except Exception as e:
        logger.error(f"Error getting standings for season {season.value}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve standings")

@router.get("/search")
async def search_teams(
    query: str = Query(..., min_length=2, description="Team name search query"),
    limit: int = Query(10, ge=1, le=30, description="Maximum number of results")
):
    """Search for teams by name or abbreviation"""
    try:
        from nba_api.stats.static import teams
        
        team_list = teams.get_teams()
        
        # filter teams by query
        matches = [
            {
                "id": team["id"],
                "full_name": team["full_name"],
                "abbreviation": team["abbreviation"],
                "nickname": team["nickname"],
                "city": team["city"],
                "state": team["state"]
            }
            for team in team_list
            if (query.lower() in team["full_name"].lower() or 
                query.lower() in team["abbreviation"].lower() or
                query.lower() in team["nickname"].lower())
        ]
        
        return {
            "query": query,
            "results": matches[:limit],
            "total_found": len(matches)
        }
        
    except Exception as e:
        logger.error(f"Error searching teams with query '{query}': {e}")
        raise HTTPException(status_code=500, detail="Failed to search teams")
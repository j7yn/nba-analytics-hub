from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from ..models.schemas import (
    PlayerComparison, 
    MatchupRequest, 
    AIInsightRequest,
    Season
)
from ..services.nba_service import nba_service
from ..core.exceptions import PlayerNotFoundError, TeamNotFoundError, DataProcessingError
from ..utils.rate_limiter import rate_limit
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/compare-players")
@rate_limit(calls_per_minute=5)
async def compare_players(comparison: PlayerComparison):
    """
    Compare multiple players across specified statistics.
    Returns detailed comparison with percentile rankings and insights.
    """
    try:
        if len(comparison.players) < 2:
            raise HTTPException(status_code=400, detail="At least 2 players required for comparison")
        
        # get player data for comparison
        player_data = {}
        for player_name in comparison.players:
            player_id = await nba_service.get_player_id(player_name)
            if not player_id:
                raise PlayerNotFoundError(f"Player '{player_name}' not found")
            
            # get career stats
            career_df = await nba_service.get_player_career_stats(player_id)
            
            # filter by season if specified
            if comparison.season != "career":
                season_df = career_df[career_df['SEASON_ID'] == comparison.season]
                if season_df.empty:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"No data found for {player_name} in {comparison.season}"
                    )
                player_data[player_name] = season_df.iloc[-1].to_dict()
            else:
                # using career averages
                numeric_columns = career_df.select_dtypes(include=[np.number]).columns
                player_data[player_name] = career_df[numeric_columns].mean().to_dict()
        
        # build comparison result
        comparison_result = {
            "comparison_type": "season" if comparison.season != "career" else "career",
            "season": comparison.season,
            "players": comparison.players,
            "stats": {},
            "rankings": {},
            "insights": []
        }
        
        # compare requested stats
        for stat in comparison.stats:
            stat_values = {}
            for player_name in comparison.players:
                value = player_data[player_name].get(stat, 0)
                stat_values[player_name] = float(value) if value is not None else 0.0
            
            comparison_result["stats"][stat] = stat_values
            
            # rank players for this stat
            sorted_players = sorted(stat_values.items(), key=lambda x: x[1], reverse=True)
            comparison_result["rankings"][stat] = [{"player": p, "value": v, "rank": i+1} 
                                                 for i, (p, v) in enumerate(sorted_players)]
        
        # generate insights
        insights = []
        for stat in comparison.stats:
            best_player = comparison_result["rankings"][stat][0]
            insights.append(f"{best_player['player']} leads in {stat} with {best_player['value']:.1f}")
        
        comparison_result["insights"] = insights
        
        return comparison_result
        
    except (PlayerNotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"Error comparing players {comparison.players}: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare players")

@router.post("/team-matchup")
@rate_limit(calls_per_minute=3)
async def simulate_team_matchup(matchup: MatchupRequest):
    """
    Simulate team matchup with advanced analytics.
    Provides win probability, predicted score, and key factors.
    """
    try:
        # get team IDs
        team1_id = await nba_service.get_team_id(matchup.team1)
        team2_id = await nba_service.get_team_id(matchup.team2)
        
        if not team1_id:
            raise TeamNotFoundError(f"Team '{matchup.team1}' not found")
        if not team2_id:
            raise TeamNotFoundError(f"Team '{matchup.team2}' not found")
        
        # get current season team stats
        team_stats_df = await nba_service.get_team_stats("2023-24")
        
        team1_stats = team_stats_df[team_stats_df['TEAM_ID'] == team1_id]
        team2_stats = team_stats_df[team_stats_df['TEAM_ID'] == team2_id]
        
        if team1_stats.empty or team2_stats.empty:
            raise HTTPException(status_code=404, detail="Team statistics not found")
        
        # extract key stats
        team1_data = team1_stats.iloc[0]
        team2_data = team2_stats.iloc[0]
        
        # simple matchup simulation (enhance this with more sophisticated models if needed)
        team1_off_rating = float(team1_data.get('OFF_RATING', 110))
        team1_def_rating = float(team1_data.get('DEF_RATING', 110))
        team2_off_rating = float(team2_data.get('OFF_RATING', 110))
        team2_def_rating = float(team2_data.get('DEF_RATING', 110))
        
        # predict scores based on pace and ratings
        possessions = matchup.pace * 48 / 48  # simplified pace calculation
        
        team1_predicted_score = (team1_off_rating + (120 - team2_def_rating)) / 2 * possessions / 100
        team2_predicted_score = (team2_off_rating + (120 - team1_def_rating)) / 2 * possessions / 100
        
        # calculate win probability (simplified logistic model)
        score_diff = team1_predicted_score - team2_predicted_score
        team1_win_prob = 1 / (1 + np.exp(-score_diff / 10))
        
        # key factors
        factors = []
        if team1_off_rating > team2_off_rating:
            factors.append(f"{matchup.team1} has offensive advantage ({team1_off_rating:.1f} vs {team2_off_rating:.1f})")
        else:
            factors.append(f"{matchup.team2} has offensive advantage ({team2_off_rating:.1f} vs {team1_off_rating:.1f})")
            
        if team1_def_rating < team2_def_rating:
            factors.append(f"{matchup.team1} has defensive advantage ({team1_def_rating:.1f} vs {team2_def_rating:.1f})")
        else:
            factors.append(f"{matchup.team2} has defensive advantage ({team2_def_rating:.1f} vs {team1_def_rating:.1f})")
        
        return {
            "matchup": f"{matchup.team1} vs {matchup.team2}",
            "predicted_score": {
                matchup.team1: round(team1_predicted_score, 1),
                matchup.team2: round(team2_predicted_score, 1)
            },
            "win_probability": {
                matchup.team1: round(team1_win_prob, 3),
                matchup.team2: round(1 - team1_win_prob, 3)
            },
            "key_factors": factors,
            "simulation_params": {
                "pace": matchup.pace,
                "simulations": matchup.simulations,
                "era_rules": matchup.era_rules
            }
        }
        
    except (TeamNotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"Error simulating matchup {matchup.team1} vs {matchup.team2}: {e}")
        raise HTTPException(status_code=500, detail="Failed to simulate team matchup")

@router.post("/ai-insights")
@rate_limit(calls_per_minute=5)
async def get_ai_insights(request: AIInsightRequest):
    """
    Get AI-powered basketball insights and analysis.
    Processes natural language queries about players, teams, and trends.
    """
    try:
        # placeholder for AI insights functionality
        # in prod, integrate with an AI service
        
        query_lower = request.query.lower()
        insights = []
        
        # simple keyword-based insights (able to enhance with actual AI/ML)
        if "best" in query_lower and "scorer" in query_lower:
            insights.append("Based on current season data, players with highest PPG typically combine volume scoring with efficiency.")
            insights.append("Look for players with high True Shooting % along with high usage rates.")
            
        elif "defense" in query_lower:
            insights.append("Defensive impact is best measured through Defensive Rating and advanced stats like DBPM.")
            insights.append("Steals and blocks are visible but don't tell the complete defensive story.")
            
        elif "rookie" in query_lower:
            insights.append("Rookie performance often correlates with opportunity and team system fit.")
            insights.append("Usage rate and minutes played are key indicators of rookie development trajectory.")
            
        elif "trade" in query_lower:
            insights.append("Player value in trades often depends on contract situation and team needs.")
            insights.append("Advanced stats like PER, VORP, and BPM provide objective trade value assessment.")
            
        else:
            insights.append("Consider multiple statistical categories for comprehensive player evaluation.")
            insights.append("Context matters - team system, pace, and role significantly impact individual stats.")
        
        return {
            "query": request.query,
            "insights": insights,
            "context_used": request.context,
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.75  # placeholder confidence score
        }
        
    except Exception as e:
        logger.error(f"Error generating AI insights for query '{request.query}': {e}")
        raise HTTPException(status_code=500, detail="Failed to generate insights")

@router.get("/trending")
async def get_trending_players(
    metric: str = Query("PTS", description="Trending metric (PTS, AST, REB, etc.)"),
    timeframe: str = Query("season", description="Timeframe (season, month, week)"),
    limit: int = Query(10, ge=1, le=25, description="Number of trending players")
):
    """Get trending players based on specified metrics and timeframe"""
    try:
        # simplified implementation
        # in prod, you'd track performance changes over time
        
        return {
            "metric": metric,
            "timeframe": timeframe,
            "trending_players": [
                {"player": "Example Player 1", "trend": "+15%", "current_avg": 28.5},
                {"player": "Example Player 2", "trend": "+12%", "current_avg": 25.3},
                {"player": "Example Player 3", "trend": "+8%", "current_avg": 22.1}
            ],
            "note": "Trending analysis requires historical data tracking - this is a placeholder response"
        }
        
    except Exception as e:
        logger.error(f"Error getting trending players: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trending players")
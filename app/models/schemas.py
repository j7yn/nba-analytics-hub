from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class Season(str, Enum):
    CURRENT = "2023-24"
    PREVIOUS = "2022-23"

class PlayerArchetype(str, Enum):
    VERSATILE_SUPERSTAR = "Versatile Superstar"
    ELITE_SCORER = "Elite Scorer"
    DOMINANT_SCORER = "Dominant Scorer"
    FLOOR_GENERAL = "Floor General"
    PAINT_PRESENCE = "Paint Presence"
    ROLE_PLAYER = "Role Player"
    DEVELOPING_PLAYER = "Developing Player"

class SeasonStats(BaseModel):
    season: str
    age: int = Field(ge=18, le=50)
    team: str
    games: int = Field(ge=0, le=82)
    minutes: float = Field(ge=0, le=48)
    pts: float = Field(ge=0, le=50)
    ast: float = Field(ge=0, le=20)
    reb: float = Field(ge=0, le=30)
    stl: float = Field(ge=0, le=5)
    blk: float = Field(ge=0, le=5)
    fg_pct: float = Field(ge=0, le=1)
    fg3_pct: Optional[float] = Field(ge=0, le=1)
    ft_pct: Optional[float] = Field(ge=0, le=1)
    usage_pct: Optional[float] = Field(ge=0, le=50)
    per: Optional[float] = Field(ge=0, le=50)
    ts_pct: Optional[float] = Field(ge=0, le=1)
    
    @validator('pts', 'ast', 'reb', 'stl', 'blk', 'minutes')
    def round_stats(cls, v):
        return round(v, 1) if v is not None else v
    
    @validator('fg_pct', 'fg3_pct', 'ft_pct', 'ts_pct')
    def round_percentages(cls, v):
        return round(v, 3) if v is not None else v

class CareerSummary(BaseModel):
    total_seasons: int = Field(ge=0)
    career_ppg: float = Field(ge=0)
    career_apg: float = Field(ge=0)
    career_rpg: float = Field(ge=0)

class PlayerEvolutionResponse(BaseModel):
    player_name: str
    seasons: List[SeasonStats]
    archetype: PlayerArchetype
    milestones: List[str]
    career_summary: CareerSummary

class ShotData(BaseModel):
    x: float
    y: float
    made: bool
    distance: int = Field(ge=0, le=100)
    zone: str
    action: str

class ShotChartSummary(BaseModel):
    total_shots: int = Field(ge=0)
    makes: int = Field(ge=0)
    fg_pct: float = Field(ge=0, le=1)

class ShotChartResponse(BaseModel):
    player_name: str
    season: str
    shots: List[ShotData]
    summary: ShotChartSummary

class TeamStats(BaseModel):
    team: str
    team_id: int
    games: int = Field(ge=0, le=82)
    wins: int = Field(ge=0, le=82)
    losses: int = Field(ge=0, le=82)
    win_pct: float = Field(ge=0, le=1)
    pts: float = Field(ge=0, le=200)
    opp_pts: float = Field(ge=0, le=200)
    pace: float = Field(ge=80, le=120)
    off_rating: float = Field(ge=90, le=130)
    def_rating: float = Field(ge=90, le=130)
    net_rating: float = Field(ge=-30, le=30)

class TeamStatsResponse(BaseModel):
    season: str
    teams: List[TeamStats]

class MatchupRequest(BaseModel):
    team1: str
    team2: str
    pace: float = Field(default=100.0, ge=80, le=120)
    simulations: int = Field(default=1000, ge=100, le=10000)
    era_rules: str = Field(default="modern")

class PlayerComparison(BaseModel):
    players: List[str] = Field(min_items=2, max_items=10)
    season: str = "2023-24"
    stats: List[str] = ["PTS", "AST", "REB", "PER", "TS_PCT"]

class AIInsightRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    context: Dict[str, Any] = {}
import pandas as pd
import numpy as np
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

def calculate_advanced_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate additional advanced statistics"""
    df = df.copy()
    
    try:
        # usage rate calculation (simplified)
        if all(col in df.columns for col in ['FGA', 'FTA', 'TOV', 'MIN']):
            df['USG_PCT'] = ((df['FGA'] + 0.44 * df['FTA'] + df['TOV']) * 40 * 5) / (df['MIN'] * 2)
        
        # true shooting percentage calculation
        if all(col in df.columns for col in ['PTS', 'FGA', 'FTA']):
            denominators = 2 * (df['FGA'] + 0.44 * df['FTA'])
            df['TS_PCT'] = np.where(denominators > 0, df['PTS'] / denominators, 0)
        
        # player efficiency rating (PER) calculation (simplified)
        required_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGM', 'FGA', 'FTM', 'FTA', 'TOV', 'MIN']
        if all(col in df.columns for col in required_cols):
            df['PER'] = np.where(
                df['MIN'] > 0,
                (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK'] - 
                (df['FGA'] - df['FGM']) - (df['FTA'] - df['FTM']) - df['TOV']) / df['MIN'] * 36,
                0
            )
        
        # fill NaN values with 0
        df = df.fillna(0)
        
    except Exception as e:
        logger.error(f"Error calculating advanced stats: {e}")
    
    return df

def detect_career_milestones(df: pd.DataFrame, player_name: str) -> List[str]:
    """Detect significant career milestones"""
    milestones = []
    
    try:
        if 'PTS' in df.columns and len(df) > 0:
            # scoring milestones
            max_pts_idx = df['PTS'].idxmax()
            if pd.notna(max_pts_idx):
                career_high_season = df.loc[max_pts_idx, 'SEASON_ID']
                career_high_pts = df.loc[max_pts_idx, 'PTS']
                milestones.append(f"{career_high_season}: Career-high {career_high_pts:.1f} PPG")
        
        # age-related milestones
        if 'PLAYER_AGE' in df.columns and 'PTS' in df.columns:
            peak_idx = df['PTS'].idxmax()
            if pd.notna(peak_idx):
                peak_age = df.loc[peak_idx, 'PLAYER_AGE']
                if pd.notna(peak_age) and peak_age >= 30:
                    milestones.append(f"Age {int(peak_age)}: Late-career scoring peak")
        
        # career longevity
        if len(df) >= 15:
            milestones.append(f"Career longevity: {len(df)} seasons played")
        
    except Exception as e:
        logger.error(f"Error detecting milestones for {player_name}: {e}")
    
    return milestones

def safe_float_conversion(value, default=0.0) -> float:
    """Safely convert value to float"""
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int_conversion(value, default=0) -> int:
    """Safely convert value to int"""
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default
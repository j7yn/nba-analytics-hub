from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys

# import routers
from .routers import players, teams, analytics
from .core.config import settings
from .core.exceptions import PlayerNotFoundError, TeamNotFoundError, RateLimitExceededError, NBAAPIError

# configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('nba_api.log')
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    description="Advanced NBA Analytics API with comprehensive player and team statistics"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# exception handlers
@app.exception_handler(PlayerNotFoundError)
async def player_not_found_handler(request: Request, exc: PlayerNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": f"Player not found: {str(exc)}"}
    )

@app.exception_handler(TeamNotFoundError)
async def team_not_found_handler(request: Request, exc: TeamNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": f"Team not found: {str(exc)}"}
    )

@app.exception_handler(RateLimitExceededError)
async def rate_limit_handler(request: Request, exc: RateLimitExceededError):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )

@app.exception_handler(NBAAPIError)
async def nba_api_error_handler(request: Request, exc: NBAAPIError):
    return JSONResponse(
        status_code=503,
        content={"detail": f"NBA API service unavailable: {str(exc)}"}
    )

# include routers
app.include_router(players.router, prefix="/players", tags=["players"])
app.include_router(teams.router, prefix="/teams", tags=["teams"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

@app.get("/")
async def root():
    return {
        "message": "NBA Edge API - Advanced Basketball Analytics",
        "version": settings.app_version,
        "endpoints": {
            "players": "/players",
            "teams": "/teams", 
            "analytics": "/analytics",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        workers=1 if settings.debug else 4
    )
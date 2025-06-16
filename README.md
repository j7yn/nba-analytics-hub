# NBA Analytics Hub

A comprehensive basketball analytics platform that transforms raw NBA data into actionable insights. Built with FastAPI, this API provides advanced player statistics, career progression tracking, shot chart analysis, team performance metrics, and AI-powered basketball intelligence.
This API serves as a basketball data backend - integrate it with any frontend framework, mobile app, or data visualization tool.

## Features 🏀

* Player Evolution: Season-by-season statistical progression
* Career Archetypes: Automatic player classification (Versatile Superstar, Elite Scorer, etc.)
* Shot Charts: Detailed shooting location and efficiency data
* Advanced Metrics: PER, True Shooting %, Usage Rate, and more
* Team Statistics: Comprehensive team performance metrics
* Standings: Real-time league standings
* Matchup Simulation: AI-powered game predictions
* Player Comparisons: Multi-player statistical analysis
* Trending Players: Performance trend tracking
* AI Insights: Natural language basketball analysis


## Tech Stack 🛠️ 

* FastAPI
* Python 3.9+: Core programming language
* SQLite/PostgreSQL: Database options
* Redis: Optional caching layer
* Pydantic: Data validation and serialization


## Installation Steps 

### 1. Clone the Repository and Install Required Dependencies

```
git clone https://github.com/j7yn/nba-analytics-hub.git
cd nba-analytics-hub
pip install -r requirements.txt
```


### 2. Create a .env file

Sample:

```
# App Configuration
APP_NAME="NBA Analytics Hub API"
DEBUG=true
SECRET_KEY="your-secret-key-here"

# Database
DATABASE_URL="sqlite:///./nba_data.db"

# Redis (optional)
REDIS_URL="redis://localhost:6379"
REDIS_ENABLED=false

# Rate Limiting
RATE_LIMIT_CALLS=30
RATE_LIMIT_PERIOD=60
```

### 3. Run the Application 

```
uvicorn app.main:app --reload

http://localhost:8000 
```


## API Endpoints ⛓️

### Player Endpoints

* `GET /players/evolution/{player_name}` - Player career progression
* `GET /players/shot-chart/{player_name}` - Shot chart data
* `GET /players/search` - Search players by name

### Team Endpoints

* `GET /teams/stats` - Team statistics
* `GET /teams/standings` - League standings
* `GET /teams/search` - Search teams

### Analytics Endpoints

* `POST /analytics/compare-players` - Compare multiple players
* `POST /analytics/team-matchup` - Simulate team matchups
* `POST /analytics/ai-insights` - AI-powered analysis
* `GET /analytics/trending` - Trending players


## Configuration Notes ‼️

The `SECRET_KEY` in the example is for demonstration only - generate your own for production. `DATABASE_URL` can be adapted for any of (PostgreSQL, MySQL, SQLite).

### Database Setup
SQLite (Default)

`DATABASE_URL="sqlite:///./nba_data.db"`


PostgreSQL

`DATABASE_URL="postgresql://username:password@localhost/nba_analytics"`

### Redis Configuration
Enable Redis for improved performance:
```
REDIS_URL="redis://localhost:6379"
REDIS_ENABLED=true
```

### Rate Limiting
Configure API rate limits:
```
RATE_LIMIT_CALLS=100  # requests per period
RATE_LIMIT_PERIOD=60  # seconds
```







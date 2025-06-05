class NBAAPIError(Exception):
    """ Base exception for NBA API errors """
    pass

class PlayerNotFoundError(NBAAPIError):
    """ Raised when player is not found """
    pass

class TeamNotFoundError(NBAAPIError):
    """ Raised when team is not found """
    pass

class RateLimitExceededError(NBAAPIError):
    """ Raised when rate limit is exceeded """
    pass

class DataProcessingError(NBAAPIError):
    """ Raised when data processing fails """
    pass
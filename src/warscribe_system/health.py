import time

def check_health() -> dict:
    """Returns the health status of the service."""
    return {'status': 'ok', 'realm': 'warscribe-system', 'timestamp': time.time()}

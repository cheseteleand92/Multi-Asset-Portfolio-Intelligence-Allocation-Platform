"""Dependency injection for backend services."""
from functools import lru_cache
from dashboard.backend.services.data_service import DashboardDataService

@lru_cache()
def get_data_service() -> DashboardDataService:
    """Return a singleton instance of the data service."""
    return DashboardDataService()

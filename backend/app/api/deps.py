"""Re-exported common dependencies for route modules."""
from app.auth.dependencies import get_current_user, require_admin
from app.database import get_db

__all__ = ["get_current_user", "require_admin", "get_db"]

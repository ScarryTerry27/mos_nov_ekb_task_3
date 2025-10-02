from typing import Literal

from services.db import schema


def get_current_user(role: Literal["admin", "inspector", "contractor"] = "admin") -> schema.User:
    """Return the current authenticated user.

    This is a temporary stub that always returns an admin user. It should be
    replaced with real authentication that extracts the user information from
    Keycloak tokens.
    """
    dicti = {
        "admin": schema.User(user_id=1, name="Admin", role=schema.RoleEnum.ADMIN),
        "inspector": schema.User(user_id=2, name="Inspector", role=schema.RoleEnum.INSPECTOR),
        "contractor": schema.User(user_id=3, name="Contractor", role=schema.RoleEnum.CONTRACTOR),
    }
    return dicti[role]

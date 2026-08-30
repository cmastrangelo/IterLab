from iterlab.auth.base import AuthProvider, Credentials
from iterlab.auth.local import LocalAuthProvider

__all__ = ["AuthProvider", "Credentials", "LocalAuthProvider", "get_auth_provider"]

_PROVIDERS = {"local": LocalAuthProvider}


def get_auth_provider(name: str = "local") -> AuthProvider:
    """Resolve an auth provider by name.

    Only ``local`` (email + password) exists today. SSO/OIDC providers register
    here later without the API layer changing.
    """
    try:
        return _PROVIDERS[name]()
    except KeyError:
        raise ValueError(f"unknown auth provider: {name!r}") from None

"""Arcade Cloud client through exe.dev's provider-side HTTP proxy.

The real Arcade project API key is held by exe.dev and injected at the edge.
No Arcade credential is stored or read by this module.
"""
from arcadepy import Arcade

ARCADE_PROXY_BASE_URL = "https://arcade-api.int.exe.xyz"


def client() -> Arcade:
    # arcadepy requires a non-empty api_key client option. The one-character
    # placeholder below is not a credential; exe.dev replaces/injects the
    # real provider-side Authorization header at its HTTP proxy edge.
    return Arcade(api_key="x", base_url=ARCADE_PROXY_BASE_URL)

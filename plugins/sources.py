"""Registry of available metadata sources (AniList for adult anime / manga)."""
from plugins.anilist import AniListSource

anilist = AniListSource()
SOURCES = {"anilist": anilist}
__all__ = ["SOURCES", "anilist"]

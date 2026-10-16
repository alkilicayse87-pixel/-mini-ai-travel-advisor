from functools import lru_cache

from openai import OpenAI

from app.config import get_api_key


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    return OpenAI(api_key=get_api_key())

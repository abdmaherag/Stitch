import os
from dotenv import load_dotenv

load_dotenv()

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Add it to resume-tailor/.env"
            )
        from anthropic import Anthropic
        _client = Anthropic(api_key=api_key)
    return _client

if not os.environ.get("API_ID"):
    raise RuntimeError("API_ID is not configured")

if not os.environ.get("API_HASH"):
    raise RuntimeError("API_HASH is not configured")

if not os.environ.get("SESSION_STR"):
    raise RuntimeError("SESSION_STR is not configured")

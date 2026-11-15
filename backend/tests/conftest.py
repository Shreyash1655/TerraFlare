import os

# Tests must never inherit the shell's real-data settings.
os.environ.pop("TERRAFLARE_OBS_SOURCE", None)
os.environ["TERRAFLARE_DATA_MODE"] = "fixture"
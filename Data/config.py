import os

# Environment configuration
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

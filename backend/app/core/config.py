"""Novel Polish Backend - Core Configuration"""

import os

# Port locked to 57621 for local Electron app
PORT = int(os.getenv("PORT", "57621"))
HOST = os.getenv("HOST", "localhost")

# CORS settings for local Electron renderer
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
    "http://localhost:18978",  # Electron default
    "http://127.0.0.1:18978",
]

# Logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

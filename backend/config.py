# backend/config.py
# Put your API keys here. DO NOT commit to git.
# Example:
# MARKETSTACK_KEY = "YOUR_MARKETSTACK_KEY"
# MARKETSTACK_BASE = "http://api.marketstack.com/v2"
# MONGO_URL = "mongodb://localhost:27017"
# DB_NAME = "stock_research_db"

import os

MARKETSTACK_KEY = os.getenv("MARKETSTACK_KEY", "9cd1acba011a05346c87a470bc2a4c19")
MARKETSTACK_BASE = os.getenv("MARKETSTACK_BASE", "http://api.marketstack.com/v1")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "stock_research_db")

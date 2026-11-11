"""
api/index.py
Vercel Serverless Function entrypoint for EcoPredict AI.
Bridges FastAPI app to Vercel Python Runtime.
"""

import os
import sys
import shutil

API_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(API_DIR)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

# Prime /tmp/electronic_fleet.db from local pre-populated database
tmp_db = "/tmp/electronic_fleet.db"
if not os.path.exists(tmp_db) or os.path.getsize(tmp_db) == 0:
    for candidate in [os.path.join(API_DIR, "electronic_fleet.db"), os.path.join(ROOT_DIR, "electronic_fleet.db")]:
        if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
            try:
                shutil.copy2(candidate, tmp_db)
                break
            except Exception:
                pass

from main import app

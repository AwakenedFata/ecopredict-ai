"""
api/index.py
Vercel Serverless Function entrypoint for EcoPredict AI.
Bridges FastAPI app to Vercel Python Runtime.
"""

import os
import sys
import shutil

# Add project root to sys.path so modules (ai, core, api, etc.) resolve
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Ensure database is primed in /tmp on Vercel
if os.environ.get("VERCEL"):
    tmp_db = "/tmp/electronic_fleet.db"
    src_db = os.path.join(ROOT_DIR, "electronic_fleet.db")
    if not os.path.exists(tmp_db) and os.path.exists(src_db):
        shutil.copy2(src_db, tmp_db)

from main import app

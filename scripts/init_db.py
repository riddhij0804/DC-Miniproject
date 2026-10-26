#!/usr/bin/env python3
"""
CLI utility to initialize schema and seed demo data.
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.seed_data import seed_database
from scripts.create_art_assets import generate_assets

def main():
    print("Generating artwork vector assets...")
    generate_assets()
    print("Initializing SQLite database with schema and seed data...")
    seed_database()
    print("Database initialization complete.")

if __name__ == "__main__":
    main()

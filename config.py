from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

POSTGRES_URL = "postgresql+psycopg2://postgres:30032006@localhost:5432/weather_db"

MYSQL_URL = "mysql+pymysql://root:root123@localhost/weather_db"

DATABASE_URL = POSTGRES_URL

CSV_PATH = str(BASE_DIR / "GlobalWeatherRepository.csv")

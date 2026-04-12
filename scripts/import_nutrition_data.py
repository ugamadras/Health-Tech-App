#!/usr/bin/env python3
"""Import USDA and FDA seed data into a local SQLite database."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
USDA_PATH = ROOT / "data" / "usda" / "foods.json"
FDA_PATH = ROOT / "data" / "fda" / "daily_values.json"


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def init_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS data_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            published_at TEXT NOT NULL,
            imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, version)
        );

        CREATE TABLE IF NOT EXISTS foods (
            food_code TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            portion_grams REAL NOT NULL,
            calories REAL NOT NULL,
            protein_g REAL NOT NULL,
            carbs_g REAL NOT NULL,
            fat_g REAL NOT NULL,
            fiber_g REAL NOT NULL,
            sodium_mg REAL NOT NULL,
            potassium_mg REAL NOT NULL,
            vitamin_c_mg REAL NOT NULL,
            iron_mg REAL NOT NULL,
            source_name TEXT NOT NULL,
            source_version TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daily_values (
            nutrient_key TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            amount REAL NOT NULL,
            unit TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_version TEXT NOT NULL
        );
        """
    )
    connection.commit()


def upsert_sources(connection: sqlite3.Connection, sources: Iterable[dict]) -> None:
    connection.executemany(
        """
        INSERT OR IGNORE INTO data_sources (name, version, published_at)
        VALUES (:name, :version, :published_at)
        """,
        sources,
    )
    connection.commit()


def upsert_foods(connection: sqlite3.Connection, foods: Iterable[dict], source: dict) -> None:
    payload = []
    for food in foods:
        row = dict(food)
        row["source_name"] = source["name"]
        row["source_version"] = source["version"]
        payload.append(row)

    connection.executemany(
        """
        INSERT INTO foods (
            food_code, description, portion_grams, calories,
            protein_g, carbs_g, fat_g, fiber_g, sodium_mg,
            potassium_mg, vitamin_c_mg, iron_mg, source_name, source_version
        ) VALUES (
            :food_code, :description, :portion_grams, :calories,
            :protein_g, :carbs_g, :fat_g, :fiber_g, :sodium_mg,
            :potassium_mg, :vitamin_c_mg, :iron_mg, :source_name, :source_version
        )
        ON CONFLICT(food_code) DO UPDATE SET
            description=excluded.description,
            portion_grams=excluded.portion_grams,
            calories=excluded.calories,
            protein_g=excluded.protein_g,
            carbs_g=excluded.carbs_g,
            fat_g=excluded.fat_g,
            fiber_g=excluded.fiber_g,
            sodium_mg=excluded.sodium_mg,
            potassium_mg=excluded.potassium_mg,
            vitamin_c_mg=excluded.vitamin_c_mg,
            iron_mg=excluded.iron_mg,
            source_name=excluded.source_name,
            source_version=excluded.source_version
        """,
        payload,
    )
    connection.commit()


def upsert_daily_values(connection: sqlite3.Connection, daily_values: Iterable[dict], source: dict) -> None:
    payload = []
    for value in daily_values:
        row = dict(value)
        row["source_name"] = source["name"]
        row["source_version"] = source["version"]
        payload.append(row)

    connection.executemany(
        """
        INSERT INTO daily_values (
            nutrient_key, label, amount, unit, source_name, source_version
        ) VALUES (
            :nutrient_key, :label, :amount, :unit, :source_name, :source_version
        )
        ON CONFLICT(nutrient_key) DO UPDATE SET
            label=excluded.label,
            amount=excluded.amount,
            unit=excluded.unit,
            source_name=excluded.source_name,
            source_version=excluded.source_version
        """,
        payload,
    )
    connection.commit()


def import_data(db_path: Path) -> None:
    usda = load_json(USDA_PATH)
    fda = load_json(FDA_PATH)
    connection = sqlite3.connect(db_path)

    init_schema(connection)
    upsert_sources(connection, [usda[0], fda[0]])
    upsert_foods(connection, usda[1]["foods"], usda[0])
    upsert_daily_values(connection, fda[1]["daily_values"], fda[0])
    connection.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default=str(ROOT / "data" / "nutrition.sqlite3"))
    args = parser.parse_args()
    import_data(Path(args.db_path))


if __name__ == "__main__":
    main()


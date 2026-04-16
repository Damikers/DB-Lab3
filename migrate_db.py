from __future__ import annotations

from typing import Iterable

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import SQLAlchemyError

from config import MYSQL_URL, POSTGRES_URL
from models.weather import Base, Weather
from models.air_quality import AirQuality


def _chunks(items: Iterable[dict], size: int) -> Iterable[list[dict]]:
    batch: list[dict] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def migrate_postgres_to_mysql(*, batch_size: int = 5000) -> None:
    """
    Copy data from PostgreSQL (source) to MySQL (destination).

    Expects both databases to have the same schema as the current ORM models
    (weather + air_quality).
    """
    src_engine = create_engine(POSTGRES_URL)
    dst_engine = create_engine(MYSQL_URL)

    try:
        with src_engine.connect() as src_conn:
            src_conn.execute(select(1))
    except SQLAlchemyError as e:
        raise RuntimeError(
            "Не вдалося підключитися до PostgreSQL. "
            "Перевірте, що сервер запущено і POSTGRES_URL правильний."
        ) from e

    try:
        with dst_engine.connect() as dst_conn:
            dst_conn.execute(select(1))
    except SQLAlchemyError as e:
        raise RuntimeError(
            "Не вдалося підключитися до MySQL. "
            "Перевірте, що сервер запущено і MYSQL_URL правильний."
        ) from e

    dst_inspector = inspect(dst_engine)
    if not dst_inspector.has_table("weather") or not dst_inspector.has_table("air_quality"):
        Base.metadata.create_all(dst_engine)

    with src_engine.connect() as src_conn, dst_engine.begin() as dst_conn:
        try:
            dst_conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        except Exception:
            pass

        dst_conn.exec_driver_sql("DELETE FROM air_quality")
        dst_conn.exec_driver_sql("DELETE FROM weather")

        weather_rows = (
            src_conn.execute(
                select(
                    Weather.id,
                    Weather.country,
                    Weather.wind_degree,
                    Weather.wind_kph,
                    Weather.wind_dir,
                    Weather.last_updated,
                    Weather.sunrise,
                )
            )
            .mappings()
            .all()
        )

        for batch in _chunks(weather_rows, batch_size):
            dst_conn.execute(Weather.__table__.insert(), batch)

        aq_rows = (
            src_conn.execute(
                select(
                    AirQuality.id,
                    AirQuality.weather_id,
                    AirQuality.air_co,
                    AirQuality.air_no2,
                    AirQuality.air_ozone,
                    AirQuality.air_so2,
                    AirQuality.air_pm25,
                    AirQuality.air_pm10,
                    AirQuality.air_epa_index,
                    AirQuality.air_defra_index,
                    AirQuality.go_outside,
                )
            )
            .mappings()
            .all()
        )

        for batch in _chunks(aq_rows, batch_size):
            dst_conn.execute(AirQuality.__table__.insert(), batch)

        try:
            dst_conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")
        except Exception:
            pass

    print("Міграція Postgres -> MySQL завершена успішно.")

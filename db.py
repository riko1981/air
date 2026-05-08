import os
import re
import sqlite3
from pathlib import Path

import pandas as pd
import pyodbc
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
BACKEND = os.getenv("AIR_DB_BACKEND", "sqlite").lower()
SQLITE_PATH = Path(os.getenv("AIR_SQLITE_PATH", BASE_DIR / "data" / "air_monitoring.db"))


def _default_driver():
    installed_drivers = set(pyodbc.drivers())
    for driver in (
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server",
    ):
        if driver in installed_drivers:
            return driver
    return "ODBC Driver 18 for SQL Server"


SERVER = os.getenv(
    "AIR_DB_SERVER",
    rf"{os.getenv('COMPUTERNAME', 'localhost')}\SQLEXPRESS",
)
DATABASE = os.getenv("AIR_DB_NAME", "AirMonitoringDB")
DRIVER = os.getenv("AIR_DB_DRIVER", _default_driver())
TRUSTED_CONNECTION = os.getenv("AIR_DB_TRUSTED_CONNECTION", "yes")
TRUST_SERVER_CERTIFICATE = os.getenv("AIR_DB_TRUST_SERVER_CERTIFICATE", "yes")
CREATE_DATABASE = os.getenv("AIR_DB_CREATE_DATABASE", "true").lower() == "true"


def _validate_database_name(database):
    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
        raise ValueError("AIR_DB_NAME может содержать только латинские буквы, цифры и знак _")


def _connection_string(database):
    return (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={database};"
        f"Trusted_Connection={TRUSTED_CONNECTION};"
        f"TrustServerCertificate={TRUST_SERVER_CERTIFICATE};"
    )


def ensure_database_exists():
    if not CREATE_DATABASE:
        return

    _validate_database_name(DATABASE)
    query = f"""
    IF DB_ID(N'{DATABASE}') IS NULL
    BEGIN
        CREATE DATABASE [{DATABASE}]
    END
    """
    conn = pyodbc.connect(_connection_string("master"), autocommit=True)
    try:
        conn.execute(query)
    finally:
        conn.close()


def get_connection():
    if BACKEND == "sqlite":
        SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(SQLITE_PATH)

    ensure_database_exists()
    return pyodbc.connect(_connection_string(DATABASE))


def normalize_limit(limit, default=500, maximum=1000):
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        return default
    return max(1, min(limit, maximum))

class AirQualityDB:
    def __init__(self):
        self.conn = get_connection()
        self._create_table()
        if BACKEND == "sqlite":
            print(f"Connected to SQLite: {SQLITE_PATH}")
        else:
            print(f"Connected to SQL Server: {SERVER}/{DATABASE}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
    
    def _create_table(self):
        if BACKEND == "sqlite":
            query = """
            CREATE TABLE IF NOT EXISTS AirQualityMeasurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                city TEXT,
                latitude REAL,
                longitude REAL,
                altitude REAL,
                co2_ppm REAL,
                co_ppm REAL,
                pm25 REAL,
                pm10 REAL,
                temperature_celsius REAL,
                humidity_percent REAL,
                battery_level REAL,
                drone_status TEXT
            )
            """
        else:
            query = """
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='AirQualityMeasurements' AND xtype='U')
            CREATE TABLE AirQualityMeasurements (
                id INT IDENTITY(1,1) PRIMARY KEY,
                timestamp DATETIME2 DEFAULT GETDATE(),
                city NVARCHAR(100),
                latitude DECIMAL(10, 7),
                longitude DECIMAL(10, 7),
                altitude DECIMAL(8, 2),
                co2_ppm DECIMAL(10, 2),
                co_ppm DECIMAL(10, 2),
                pm25 DECIMAL(10, 2),
                pm10 DECIMAL(10, 2),
                temperature_celsius DECIMAL(5, 2),
                humidity_percent DECIMAL(5, 2),
                battery_level DECIMAL(5, 2),
                drone_status VARCHAR(50)
            )
            """
        self.conn.execute(query)
        self.conn.commit()
        self._ensure_city_column()

    def _ensure_city_column(self):
        if BACKEND == "sqlite":
            columns = pd.read_sql("PRAGMA table_info(AirQualityMeasurements)", self.conn)
            if "city" not in columns["name"].tolist():
                self.conn.execute("ALTER TABLE AirQualityMeasurements ADD COLUMN city TEXT")
                self.conn.execute("UPDATE AirQualityMeasurements SET city = 'Неизвестно' WHERE city IS NULL")
                self.conn.commit()
            return

        query = """
        IF COL_LENGTH('AirQualityMeasurements', 'city') IS NULL
        BEGIN
            ALTER TABLE AirQualityMeasurements ADD city NVARCHAR(100) NULL
            UPDATE AirQualityMeasurements SET city = N'Неизвестно' WHERE city IS NULL
        END
        """
        self.conn.execute(query)
        self.conn.commit()
    
    def insert_measurement(self, data):
        timestamp = data.get('timestamp')
        if timestamp is not None:
            query = """
            INSERT INTO AirQualityMeasurements (
                timestamp, city, latitude, longitude, altitude, co2_ppm, co_ppm,
                pm25, pm10, temperature_celsius, humidity_percent,
                battery_level, drone_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            values = (
                timestamp,
                data.get('city', 'Неизвестно'),
                data.get('latitude'),
                data.get('longitude'),
                data.get('altitude', 0),
                data.get('co2_ppm'),
                data.get('co_ppm'),
                data.get('pm25'),
                data.get('pm10'),
                data.get('temperature_celsius'),
                data.get('humidity_percent'),
                data.get('battery_level', 100),
                data.get('drone_status', 'active')
            )
            cursor = self.conn.cursor()
            cursor.execute(query, values)
            self.conn.commit()
            return True

        query = """
        INSERT INTO AirQualityMeasurements (
            city, latitude, longitude, altitude, co2_ppm, co_ppm,
            pm25, pm10, temperature_celsius, humidity_percent,
            battery_level, drone_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            data.get('city', 'Неизвестно'),
            data.get('latitude'),
            data.get('longitude'),
            data.get('altitude', 0),
            data.get('co2_ppm'),
            data.get('co_ppm'),
            data.get('pm25'),
            data.get('pm10'),
            data.get('temperature_celsius'),
            data.get('humidity_percent'),
            data.get('battery_level', 100),
            data.get('drone_status', 'active')
        )
        cursor = self.conn.cursor()
        cursor.execute(query, values)
        self.conn.commit()
        return True
    
    def get_all_measurements(self, limit=500):
        limit = normalize_limit(limit)
        if BACKEND == "sqlite":
            query = f"SELECT * FROM AirQualityMeasurements ORDER BY timestamp DESC, id DESC LIMIT {limit}"
        else:
            query = f"SELECT TOP {limit} * FROM AirQualityMeasurements ORDER BY timestamp DESC, id DESC"
        return pd.read_sql(query, self.conn)
    
    def get_latest_measurement(self):
        if BACKEND == "sqlite":
            query = "SELECT * FROM AirQualityMeasurements ORDER BY timestamp DESC, id DESC LIMIT 1"
        else:
            query = "SELECT TOP 1 * FROM AirQualityMeasurements ORDER BY timestamp DESC, id DESC"
        df = pd.read_sql(query, self.conn)
        return df.iloc[0].to_dict() if not df.empty else None
    
    def get_statistics(self):
        query = """
        SELECT 
            COUNT(*) as total_measurements,
            AVG(co2_ppm) as avg_co2,
            AVG(pm25) as avg_pm25,
            AVG(temperature_celsius) as avg_temperature,
            AVG(humidity_percent) as avg_humidity,
            MIN(timestamp) as first_measurement,
            MAX(timestamp) as last_measurement
        FROM AirQualityMeasurements
        """
        return pd.read_sql(query, self.conn)
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            print("Connection closed")

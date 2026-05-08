import math
import random
from datetime import datetime, timedelta

from db import AirQualityDB
from drone_simulator import CITIES, generate_sensors


MIN_DEMO_ROWS = 120
POINTS_PER_CITY = 36


def generate_demo_measurements():
    random.seed(42)
    start_time = datetime.utcnow() - timedelta(hours=6)

    for city_name, city in CITIES.items():
        for index in range(POINTS_PER_CITY):
            timestamp = start_time + timedelta(minutes=index * 10)
            day_wave = math.sin(index / 5)
            lat = city["lat"] + random.uniform(-0.012, 0.012)
            lon = city["lon"] + random.uniform(-0.012, 0.012)
            sensors = generate_sensors(city["co2_base"], city["pm25_base"])

            sensors["co2_ppm"] += day_wave * 18
            sensors["pm25"] = max(0, sensors["pm25"] + day_wave * 6)
            sensors["pm10"] = max(0, sensors["pm10"] + day_wave * 10)

            yield {
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "city": city_name,
                "latitude": lat,
                "longitude": lon,
                "altitude": random.uniform(35, 115),
                **sensors,
                "drone_status": "demo",
            }


def seed_demo_data(force=False):
    with AirQualityDB() as db:
        df = db.get_all_measurements(limit=1000)
        known_city_rows = len(df[df["city"].isin(CITIES.keys())]) if not df.empty else 0

        if not force and known_city_rows >= MIN_DEMO_ROWS:
            print(f"Demo data skipped: database already has {known_city_rows} city rows.")
            return 0

        count = 0
        for measurement in generate_demo_measurements():
            db.insert_measurement(measurement)
            count += 1

    print(f"Inserted {count} demo measurements.")
    return count


if __name__ == "__main__":
    seed_demo_data()

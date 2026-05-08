import os
import requests
import random
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

API_HOST = os.getenv("AIR_API_HOST", "127.0.0.1")
API_PORT = os.getenv("AIR_API_PORT", "8000")
API_BASE_URL = os.getenv("AIR_API_BASE_URL", f"http://{API_HOST}:{API_PORT}")
API_URL = f"{API_BASE_URL.rstrip('/')}/api/measurements"

# Города Казахстана для мониторинга
CITIES = {
    "Алматы": {"lat": 43.222014, "lon": 76.851248, "co2_base": 420, "pm25_base": 45},
    "Астана": {"lat": 51.169392, "lon": 71.449074, "co2_base": 400, "pm25_base": 35},
    "Шымкент": {"lat": 42.341685, "lon": 69.590103, "co2_base": 410, "pm25_base": 40},
    "Караганда": {"lat": 49.801973, "lon": 73.102276, "co2_base": 430, "pm25_base": 50},
    "Актобе": {"lat": 50.283014, "lon": 57.167171, "co2_base": 390, "pm25_base": 30},
}

def generate_coordinates():
    """Генерация GPS координат в Казахстане"""
    city_name = random.choice(list(CITIES.keys()))
    city = CITIES[city_name]
    lat = city["lat"] + random.uniform(-0.01, 0.01)
    lon = city["lon"] + random.uniform(-0.01, 0.01)
    return lat, lon, city_name, city["co2_base"], city["pm25_base"]

def generate_sensors(co2_base, pm25_base):
    """Генерация данных с датчиков на основе базовых значений города"""
    return {
        "co2_ppm": co2_base + random.uniform(-20, 40),
        "co_ppm": random.uniform(1, 6),
        "pm25": max(0, pm25_base + random.uniform(-10, 20)),
        "pm10": max(0, (pm25_base * 2) + random.uniform(-15, 30)),
        "temperature_celsius": random.uniform(15, 35),
        "humidity_percent": random.uniform(25, 65),
        "battery_level": random.uniform(70, 100),
        "drone_status": random.choice(["active", "measuring", "returning"])
    }

def send_measurement():
    """Отправка данных на сервер"""
    lat, lon, city_name, co2_base, pm25_base = generate_coordinates()
    sensors = generate_sensors(co2_base, pm25_base)
    
    payload = {
        "city": city_name,
        "latitude": lat,
        "longitude": lon,
        "altitude": random.uniform(30, 120),
        **sensors
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🇰🇿 {city_name} | CO₂={payload['co2_ppm']:.0f}ppm | PM2.5={payload['pm25']:.0f} | T={payload['temperature_celsius']:.0f}°C | ✅")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Ошибка: {response.status_code}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Нет соединения: {e}")

if __name__ == "__main__":
    print("="*60)
    print("🚁 КВАДРОКОПТЕР - МОНИТОРИНГ ВОЗДУХА")
    print("🇰🇿 РЕСПУБЛИКА КАЗАХСТАН")
    print("="*60)
    print(f"📡 Отправка данных на {API_URL}")
    print("📍 Города: Алматы, Астана, Шымкент, Караганда, Актобе")
    print("🛑 Нажмите Ctrl+C для остановки\n")
    
    try:
        while True:
            send_measurement()
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n🛑 Симулятор остановлен")

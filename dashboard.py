import hmac
import os
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

from db import AirQualityDB, BACKEND, DATABASE, SERVER, SQLITE_PATH

load_dotenv()

AUTH_USERNAME = os.getenv("AIR_DASHBOARD_USERNAME", "airvision_admin")
AUTH_PASSWORD = os.getenv("AIR_DASHBOARD_PASSWORD", "change-me")

WHO_STANDARDS = {
    "CO2": {"value": 400, "unit": "ppm", "desc": "Рекомендуемый уровень"},
    "PM2.5": {"value": 25, "unit": "µg/m³", "desc": "Суточная норма ВОЗ"},
    "PM10": {"value": 45, "unit": "µg/m³", "desc": "Суточная норма ВОЗ"},
    "Температура": {"value": 22, "unit": "°C", "desc": "Комфортная температура"},
    "Влажность": {"value": 50, "unit": "%", "desc": "Оптимальная влажность"}
}

CITY_VIEW = {
    "Алматы": {"lat": 43.222014, "lon": 76.851248, "zoom": 11},
    "Астана": {"lat": 51.169392, "lon": 71.449074, "zoom": 11},
    "Шымкент": {"lat": 42.341685, "lon": 69.590103, "zoom": 11},
    "Караганда": {"lat": 49.801973, "lon": 73.102276, "zoom": 11},
    "Актобе": {"lat": 50.283014, "lon": 57.167171, "zoom": 11},
}

COUNTRY_VIEW = {"lat": 48.0, "lon": 68.0, "zoom": 5}

# ========== КОНФИГУРАЦИЯ СТРАНИЦЫ ==========
st.set_page_config(
    page_title="AirVision | Мониторинг воздуха",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== СВЕТЛЫЙ CSS ==========
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
    }
    
    /* Карточки */
    .glass-card {
        background: white;
        border-radius: 20px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
        border: 1px solid rgba(0,0,0,0.05);
    }
    
    .glass-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }
    
    /* Заголовок */
    .hero {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border-radius: 30px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 2rem;
        animation: fadeIn 1s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .hero h1 {
        color: white !important;
        margin: 0;
    }
    
    .hero p {
        color: rgba(255,255,255,0.9);
    }
    
    /* Метрики */
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e3c72;
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .metric-unit {
        font-size: 0.7rem;
        color: #999;
    }
    
    /* Текст */
    h1, h2, h3 {
        color: #1e3c72 !important;
    }
    
    p, div {
        color: #333;
    }
    
    /* Кнопки */
    .stButton > button {
        background: linear-gradient(135deg, #1e3c72, #2a5298);
        color: white;
        border-radius: 25px;
        border: none;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: scale(1.02);
        background: linear-gradient(135deg, #2a5298, #1e3c72);
    }
    
    /* Боковая панель */
    .css-1d391kg {
        background: white;
        border-right: 1px solid rgba(0,0,0,0.05);
    }
    
    /* Таблица */
    .stDataFrame {
        background: white;
        border-radius: 15px;
        padding: 1rem;
    }
    
    /* Badges */
    .exceed-badge {
        background: #fee2e2;
        border-left: 4px solid #dc2626;
        padding: 0.8rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        color: #991b1b;
    }
    
    .normal-badge {
        background: #dcfce7;
        border-left: 4px solid #22c55e;
        padding: 0.8rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        color: #166534;
    }
    
    /* Футер */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #666;
        font-size: 0.8rem;
        margin-top: 2rem;
        border-top: 1px solid rgba(0,0,0,0.1);
    }
    
    /* Селекторы */
    .stSelectbox > div {
        background: white;
        border-radius: 10px;
    }
    
    /* Информация */
    .stAlert {
        background: white;
        border-radius: 15px;
    }
</style>
""", unsafe_allow_html=True)


def check_credentials(username, password):
    return hmac.compare_digest(username, AUTH_USERNAME) and hmac.compare_digest(password, AUTH_PASSWORD)


def render_login():
    st.markdown("""
    <div class='hero' style='max-width: 720px; margin: 3rem auto 1.5rem auto;'>
        <div style='font-size: 3rem;'>🌿</div>
        <h1 style='font-size: 2.3rem;'>AirVision</h1>
        <p style='font-size: 1rem;'>Вход в систему мониторинга качества воздуха</p>
    </div>
    """, unsafe_allow_html=True)

    _, center, _ = st.columns([1, 1.15, 1])
    with center:
        st.markdown("""
        <div class='glass-card' style='margin-bottom: 1rem;'>
            <div style='font-size: 1.15rem; font-weight: 700; color: #1e3c72; margin-bottom: 0.25rem;'>Авторизация</div>
            <div style='font-size: 0.9rem; color: #666;'>Введите логин и пароль для доступа к панели.</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Логин")
            password = st.text_input("Пароль", type="password")
            submitted = st.form_submit_button("Войти", use_container_width=True)

        if submitted:
            if check_credentials(username, password):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Неверный логин или пароль")


if not st.session_state.get("authenticated", False):
    render_login()
    st.stop()

# ========== ЗАГРУЗКА ДАННЫХ ==========
@st.cache_data(ttl=5)
def load_data():
    db = None
    try:
        db = AirQualityDB()
        df = db.get_all_measurements(limit=500)
        return df, None
    except Exception as error:
        return pd.DataFrame(), str(error)
    finally:
        if db is not None:
            db.close()

df, load_error = load_data()

if not df.empty:
    if "city" not in df.columns:
        df["city"] = "Неизвестно"
    df["city"] = df["city"].fillna("Неизвестно").replace("", "Неизвестно")

city_options = ["Вся страна", *CITY_VIEW.keys()]
if not df.empty:
    extra_cities = sorted(
        city for city in df["city"].unique()
        if city not in CITY_VIEW and city != "Неизвестно"
    )
    city_options.extend(extra_cities)
    if "Неизвестно" in df["city"].unique():
        city_options.append("Неизвестно")

# ========== ХЕДЕР ==========
st.markdown("""
<div class='hero'>
    <div style='font-size: 3rem;'>🌿</div>
    <h1 style='font-size: 2.5rem;'>AirVision</h1>
    <p style='font-size: 1.1rem;'>Система мониторинга качества воздуха с квадрокоптера</p>
    <div style='margin-top: 1rem;'>
        <span style='background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; font-size: 0.8rem;'>
            🚁 Реальное время
        </span>
        <span style='background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; margin-left: 10px; font-size: 0.8rem;'>
            📡 Обновление: 3 сек
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ========== БОКОВАЯ ПАНЕЛЬ ==========
with st.sidebar:
    st.markdown("<div style='text-align: center; font-size: 3rem; margin-bottom: 1rem;'>🎛️</div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; font-weight: 600; font-size: 1.2rem;'>Управление</div>", unsafe_allow_html=True)
    st.markdown("---")
    if st.button("Выйти", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()
    st.markdown("---")

    selected_city = st.selectbox("📍 Регион анализа", city_options)
    st.caption("Выберите всю страну или отдельный город.")
    st.markdown("---")
    
    show_heatmap = st.toggle("🔥 Тепловая карта", value=True)
    show_compare = st.toggle("📊 Сравнение с ВОЗ", value=True)
    show_map = st.toggle("🗺️ Карта", value=True)
    show_charts = st.toggle("📈 Графики", value=True)
    
    st.markdown("---")
    
    # Информация о системе (кратко)
    st.markdown("""
    <div style='background: #f0f2f6; border-radius: 15px; padding: 1rem;'>
        <div style='font-weight: 600; margin-bottom: 0.5rem;'>📡 Система</div>
        <div style='font-size: 0.8rem; color: #555;'>
            Мониторинг воздуха с помощью квадрокоптера. Данные в реальном времени.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if BACKEND == "sqlite":
        st.caption(f"База данных: SQLite")
        st.caption(f"Файл: {SQLITE_PATH}")
    else:
        st.caption(f"SQL Server: {SERVER}")
        st.caption(f"База данных: {DATABASE}")

if load_error:
    st.error(f"Не удалось загрузить данные из базы: {load_error}")

if not df.empty and selected_city != "Вся страна":
    df = df[df["city"] == selected_city].copy()

view = CITY_VIEW.get(selected_city, COUNTRY_VIEW)
map_center = {"lat": view["lat"], "lon": view["lon"]}
map_zoom = view["zoom"]
region_title = selected_city if selected_city != "Вся страна" else "Вся страна"

# ========== ОСНОВНОЙ КОНТЕНТ ==========
if not df.empty:
    latest = df.iloc[0]

    st.markdown(f"<h2>📍 Регион: {region_title}</h2>", unsafe_allow_html=True)
    
    # ========== МЕТРИКИ ==========
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>🌫️ Углекислый газ (CO₂)</div>
            <div class='metric-value'>{latest['co2_ppm']:.0f}</div>
            <div class='metric-unit'>ppm</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>💨 Твердые частицы (PM2.5)</div>
            <div class='metric-value'>{latest['pm25']:.1f}</div>
            <div class='metric-unit'>µg/m³</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>🌡️ Температура</div>
            <div class='metric-value'>{latest['temperature_celsius']:.1f}°</div>
            <div class='metric-unit'>Celsius</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>💧 Влажность</div>
            <div class='metric-value'>{latest['humidity_percent']:.0f}%</div>
            <div class='metric-unit'>RH</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========== КАЧЕСТВО ВОЗДУХА ==========
    co2 = latest['co2_ppm']
    pm25 = latest['pm25']
    
    if co2 < 400 and pm25 < 35:
        aqi_level = "Отличное"
        aqi_color = "#22c55e"
        aqi_icon = "🌟"
        recommendation = "✅ Воздух чистый. Идеально для прогулок!"
    elif co2 < 600 and pm25 < 55:
        aqi_level = "Хорошее"
        aqi_color = "#3b82f6"
        aqi_icon = "😊"
        recommendation = "😊 Воздух в норме. Хорошее время для активности."
    elif co2 < 800 and pm25 < 150:
        aqi_level = "Умеренное"
        aqi_color = "#f59e0b"
        aqi_icon = "⚠️"
        recommendation = "⚠️ Чувствительным людям нужна осторожность."
    elif co2 < 1000 and pm25 < 250:
        aqi_level = "Плохое"
        aqi_color = "#ef4444"
        aqi_icon = "😷"
        recommendation = "😷 Ограничьте время на улице, используйте маску."
    else:
        aqi_level = "Опасное"
        aqi_color = "#7f1d1d"
        aqi_icon = "🚨"
        recommendation = "🚨 ОПАСНО! Избегайте длительного пребывания на улице!"
    
    st.markdown(f"""
    <div class='glass-card'>
        <div style='text-align: center;'>
            <div style='font-size: 2rem;'>{aqi_icon}</div>
            <div style='font-size: 1.3rem; font-weight: 600; color: {aqi_color};'>Качество воздуха: {aqi_level}</div>
            <div style='margin: 0.5rem 0;'>
                <span style='background: {aqi_color}; padding: 5px 20px; border-radius: 20px; font-weight: 600; color: white;'>
                    Индекс AQI
                </span>
            </div>
            <div style='font-size: 0.95rem; color: #555;'>{recommendation}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========== 📊 СРАВНЕНИЕ С НОРМАТИВАМИ ВОЗ ==========
    if show_compare:
        st.markdown("<h2>📊 Сравнение с нормативами ВОЗ</h2>", unsafe_allow_html=True)
        
        current_values = {
            "CO2": latest['co2_ppm'],
            "PM2.5": latest['pm25'],
            "PM10": latest['pm10'],
            "Температура": latest['temperature_celsius'],
            "Влажность": latest['humidity_percent']
        }
        
        comparison_data = []
        for param in ["CO2", "PM2.5", "PM10", "Температура", "Влажность"]:
            current = current_values[param]
            standard = WHO_STANDARDS[param]["value"]
            unit = WHO_STANDARDS[param]["unit"]
            
            if param in ["Температура", "Влажность"]:
                if param == "Температура":
                    if 18 <= current <= 24:
                        status = "✅ В норме"
                    elif current < 18:
                        status = "⚠️ Ниже нормы"
                    else:
                        status = "⚠️ Выше нормы"
                else:
                    if 40 <= current <= 60:
                        status = "✅ В норме"
                    elif current < 40:
                        status = "⚠️ Ниже нормы"
                    else:
                        status = "⚠️ Выше нормы"
            else:
                if current <= standard:
                    percent = ((standard - current) / standard) * 100
                    status = f"✅ Норма (ниже на {percent:.0f}%)"
                else:
                    percent = ((current - standard) / standard) * 100
                    status = f"🔴 ПРЕВЫШЕНИЕ на {percent:.0f}%"
            
            comparison_data.append({
                "Параметр": "CO₂" if param == "CO2" else param,
                "Текущее значение": f"{current:.1f} {unit}",
                "Норма ВОЗ": f"{standard} {unit}",
                "Статус": status
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        
        fig_compare = go.Figure()
        
        params = ["CO2", "PM2.5", "PM10"]
        current_vals = [current_values[p] for p in params]
        standard_vals = [WHO_STANDARDS[p]["value"] for p in params]
        chart_params = ["CO₂", "PM2.5", "PM10"]
        
        fig_compare.add_trace(go.Bar(
            name="Текущее значение",
            x=chart_params,
            y=current_vals,
            marker_color='#3b82f6'
        ))
        
        fig_compare.add_trace(go.Bar(
            name="Норма ВОЗ",
            x=chart_params,
            y=standard_vals,
            marker_color='#22c55e'
        ))
        
        fig_compare.update_layout(
            title="Сравнение: Текущие показатели vs Нормативы ВОЗ",
            yaxis_title="Значение",
            height=400,
            barmode='group',
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig_compare, use_container_width=True)
        
        st.markdown("#### ⚠️ Рекомендации")
        
        warnings = []
        if current_values["PM2.5"] > WHO_STANDARDS["PM2.5"]["value"]:
            warnings.append("🔴 **PM2.5 превышает норму ВОЗ!** Рекомендуется использовать маски на улице.")
        if current_values["PM10"] > WHO_STANDARDS["PM10"]["value"]:
            warnings.append("🔴 **PM10 превышает норму ВОЗ!** Избегайте длительного пребывания на улице.")
        if current_values["CO2"] > WHO_STANDARDS["CO2"]["value"]:
            warnings.append("🟡 **CO₂ повышен!** Рекомендуется проветрить помещение.")
        
        if warnings:
            for w in warnings:
                st.markdown(f"<div class='exceed-badge'>{w}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='normal-badge'>✅ Все показатели в норме! Качество воздуха хорошее.</div>", unsafe_allow_html=True)
        
        st.markdown("---")
    
    # ========== 🔥 ТЕПЛОВАЯ КАРТА ==========
    if show_heatmap:
        st.markdown("<h2>🔥 Тепловая карта загрязнения CO₂</h2>", unsafe_allow_html=True)
        
        fig_heatmap = px.density_mapbox(
            df,
            lat='latitude',
            lon='longitude',
            z='co2_ppm',
            radius=15,
            center=map_center,
            zoom=map_zoom,
            mapbox_style="open-street-map",
            title="Концентрация CO₂ по зонам",
            color_continuous_scale="RdYlGn_r",
            labels={'co2_ppm': 'CO₂ (ppm)'}
        )
        
        fig_heatmap.update_layout(height=500, paper_bgcolor='white')
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        st.markdown("<h2>🔥 Тепловая карта загрязнения PM2.5</h2>", unsafe_allow_html=True)
        
        fig_heatmap_pm = px.density_mapbox(
            df,
            lat='latitude',
            lon='longitude',
            z='pm25',
            radius=15,
            center=map_center,
            zoom=map_zoom,
            mapbox_style="open-street-map",
            title="Концентрация PM2.5 по зонам",
            color_continuous_scale="RdYlGn_r",
            labels={'pm25': 'PM2.5 (µg/m³)'}
        )
        
        fig_heatmap_pm.update_layout(height=500, paper_bgcolor='white')
        st.plotly_chart(fig_heatmap_pm, use_container_width=True)
        
        # Статистика по зонам
        low_zones = df[df['co2_ppm'] < 400]
        medium_zones = df[(df['co2_ppm'] >= 400) & (df['co2_ppm'] < 600)]
        high_zones = df[df['co2_ppm'] >= 600]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class='glass-card' style='text-align: center; border-left: 4px solid #22c55e;'>
                <div style='font-size: 1rem; font-weight: 600;'>🟢 Чистые зоны</div>
                <div style='font-size: 1.8rem; font-weight: 700; color: #22c55e;'>{len(low_zones)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class='glass-card' style='text-align: center; border-left: 4px solid #f59e0b;'>
                <div style='font-size: 1rem; font-weight: 600;'>🟡 Зоны внимания</div>
                <div style='font-size: 1.8rem; font-weight: 700; color: #f59e0b;'>{len(medium_zones)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class='glass-card' style='text-align: center; border-left: 4px solid #ef4444;'>
                <div style='font-size: 1rem; font-weight: 600;'>🔴 Опасные зоны</div>
                <div style='font-size: 1.8rem; font-weight: 700; color: #ef4444;'>{len(high_zones)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
    
    # ========== 🗺️ КАРТА ==========
    if show_map:
        st.markdown("<h2>🗺️ Карта измерений</h2>", unsafe_allow_html=True)
        
        fig_map = px.scatter_mapbox(
            df,
            lat="latitude",
            lon="longitude",
            color="co2_ppm",
            size="pm25",
            hover_data={
                "city": True,
                "co2_ppm": ":.0f",
                "pm25": ":.1f",
                "temperature_celsius": True,
                "humidity_percent": True
            },
            color_continuous_scale="RdYlGn_r",
            zoom=map_zoom,
            center=map_center,
            title="Концентрация CO₂",
            height=500
        )
        
        fig_map.update_layout(
            mapbox_style="open-street-map",
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig_map, use_container_width=True)
        st.markdown("---")
    
    # ========== ГРАФИКИ ==========
    if show_charts:
        st.markdown("<h2>📈 Аналитика данных</h2>", unsafe_allow_html=True)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df_sorted = df.sort_values('timestamp')
        
        param = st.selectbox(
            "Выберите параметр",
            ["co2_ppm", "pm25", "pm10", "temperature_celsius", "humidity_percent"],
            format_func=lambda x: {
                "co2_ppm": "CO₂ (ppm)",
                "pm25": "PM2.5 (µg/m³)",
                "pm10": "PM10 (µg/m³)",
                "temperature_celsius": "Температура (°C)",
                "humidity_percent": "Влажность (%)"
            }[x]
        )
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_sorted['timestamp'],
            y=df_sorted[param],
            mode='lines+markers',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=6, color='#1e3c72'),
            fill='tozeroy',
            fillcolor='rgba(59,130,246,0.2)'
        ))
        
        fig.update_layout(
            title=f"Динамика изменения {param}",
            xaxis_title="Время",
            yaxis_title="Значение",
            height=400,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
    
    # ========== АРХИВ ==========
    st.markdown("<h2>📚 Архив измерений</h2>", unsafe_allow_html=True)
    
    with st.expander("📋 Показать архив", expanded=False):
        display_cols = ['timestamp', 'city', 'latitude', 'longitude', 'co2_ppm', 'pm25', 'pm10', 'temperature_celsius', 'humidity_percent']
        st.dataframe(
            df[display_cols].head(20),
            use_container_width=True,
            hide_index=True
        )
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Скачать данные (CSV)",
            data=csv,
            file_name=f"air_data_{region_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # ========== ФУТЕР ==========
    st.markdown(f"""
    <div class='footer'>
        Система мониторинга качества воздуха с квадрокоптера<br>
        Данные в реальном времени | Обновление каждые 3 секунды
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style='background: white; border-radius: 20px; text-align: center; padding: 3rem;'>
        <div style='font-size: 4rem;'>🚁</div>
        <h3>Ожидание данных</h3>
        <p>Запустите симулятор дрона для начала мониторинга или выберите другой регион</p>
    </div>
    """, unsafe_allow_html=True)

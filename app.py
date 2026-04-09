import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from deep_translator import GoogleTranslator
import random
import threading
import io
import zipfile
import logging

from config import (
    CURRENCY_API,
    WEATHER_API,
    STOCK_API,
    MUMBAI_LAT,
    MUMBAI_LON,
    CURRENCY_REFRESH,
    WEATHER_REFRESH,
    STOCK_REFRESH,
    DASHBOARD_REFRESH,
    FALLBACK_INR_RATE,
    FALLBACK_TEMP,
    FALLBACK_STOCK,
    SPIKE_THRESHOLD_INR,
    DROP_THRESHOLD_INR,
    LANGUAGES,
)


st.set_page_config(
    page_title="Live Smart Sales Dashboard",
    page_icon="📊",
    layout="wide",
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1rem;
                padding-bottom: 1.5rem;
            }
            .live-badge {
                color: #0f9d58;
                font-weight: 700;
                padding: 4px 10px;
                border-radius: 10px;
                background: #e6f4ea;
                display: inline-block;
                margin-left: 8px;
            }
            .kpi-card {
                border: 1px solid #d7d7d7;
                border-radius: 12px;
                padding: 12px;
                background-color: #ffffff;
                min-height: 145px;
            }
            .kpi-title {
                font-size: 0.95rem;
                color: #2c2c2c;
                font-weight: 700;
            }
            .kpi-value {
                font-size: 1.35rem;
                font-weight: 800;
                margin-top: 4px;
                color: #111111;
            }
            .kpi-sub {
                font-size: 0.85rem;
                color: #4a4a4a;
            }
            .positive { color: #0f9d58; font-weight: 700; }
            .negative { color: #d93025; font-weight: 700; }
            .warning { color: #f9ab00; font-weight: 700; }
            .stButton > button, .stDownloadButton > button {
                min-height: 48px !important;
                font-size: 1rem !important;
                border-radius: 10px !important;
            }
            .helper {
                color: #333333;
                font-size: 0.85rem;
            }
            .simple-box {
                border-left: 6px solid #0f9d58;
                padding: 10px 12px;
                border-radius: 8px;
                background: #f8f9fa;
                margin-bottom: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_dark_mode_styles() -> None:
    st.markdown(
        """
        <style>
            [data-testid="stAppViewContainer"] {
                background: #0f172a;
                color: #f8fafc;
            }
            [data-testid="stSidebar"] {
                background: #111827;
            }
            .kpi-card {
                background-color: #1f2937 !important;
                border: 1px solid #374151 !important;
            }
            .kpi-title, .kpi-sub, .kpi-value {
                color: #f3f4f6 !important;
            }
            .simple-box {
                background: #1f2937 !important;
                border-left: 6px solid #60a5fa !important;
                color: #e5e7eb !important;
            }
            .helper {
                color: #e5e7eb !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def cached_translate(text: str, target_lang: str) -> str:
    if not text or target_lang == "en":
        return text
    try:
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception:
        return text


def tr(text: str, lang_code: str) -> str:
    return cached_translate(text, lang_code)


@st.cache_data(ttl=CURRENCY_REFRESH, show_spinner=False)
def get_currency_rate():
    try:
        response = requests.get(CURRENCY_API, timeout=10)
        response.raise_for_status()
        data = response.json()
        rate = float(data["rates"]["INR"])
        return rate, None
    except Exception as exc:
        logging.exception("Currency API failed: %s", exc)
        return FALLBACK_INR_RATE, "Currency API unavailable. Using fallback rate."


def weather_icon(temp_c: float) -> str:
    if temp_c >= 35:
        return "☀️"
    if temp_c < 24:
        return "🌧️"
    return "🌤️"


@st.cache_data(ttl=WEATHER_REFRESH, show_spinner=False)
def get_weather_mumbai():
    params = {
        "latitude": MUMBAI_LAT,
        "longitude": MUMBAI_LON,
        "current": "temperature_2m",
        "timezone": "Asia/Kolkata",
    }
    try:
        response = requests.get(WEATHER_API, params=params, timeout=12)
        response.raise_for_status()
        data = response.json()
        temp = float(data["current"]["temperature_2m"])
        icon = weather_icon(temp)
        return temp, icon, None
    except Exception as exc:
        logging.exception("Weather API failed: %s", exc)
        return float(FALLBACK_TEMP), "☀️", "Weather API unavailable. Using fallback weather."


@st.cache_data(ttl=STOCK_REFRESH, show_spinner=False)
def get_btc_price():
    params = {"ids": "bitcoin", "vs_currencies": "usd"}
    try:
        response = requests.get(STOCK_API, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        price = float(data["bitcoin"]["usd"])
        return price, None
    except Exception as exc:
        logging.exception("Stock API failed: %s", exc)
        return float(FALLBACK_STOCK), "Crypto API unavailable. Using fallback price."


def ist_now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Kolkata"))


def build_sales_series(now_ist: datetime):
    hours = [(now_ist - timedelta(hours=h)).replace(minute=0, second=0, microsecond=0) for h in range(23, -1, -1)]
    sales = []
    orders = []
    active_customers = []
    for dt in hours:
        h = dt.hour
        if 9 <= h <= 21:
            base = random.uniform(4500, 11000)
            ord_base = random.randint(38, 120)
            cust_base = random.randint(40, 220)
        else:
            base = random.uniform(700, 4200)
            ord_base = random.randint(5, 35)
            cust_base = random.randint(8, 70)
        noise = random.uniform(0.85, 1.18)
        sales.append(round(base * noise, 2))
        orders.append(int(ord_base * random.uniform(0.9, 1.15)))
        active_customers.append(int(cust_base * random.uniform(0.85, 1.2)))
    df = pd.DataFrame(
        {
            "hour": [d.strftime("%H:00") for d in hours],
            "timestamp": hours,
            "sales_usd": sales,
            "orders": orders,
            "active_customers": active_customers,
        }
    )
    return df


def category_split(total_sales: float) -> pd.DataFrame:
    categories = ["Electronics", "Clothing", "Groceries", "Furniture"]
    parts = np.random.dirichlet(np.array([3.4, 2.7, 2.3, 1.8]), size=1)[0]
    values = np.round(parts * total_sales, 2)
    return pd.DataFrame({"category": categories, "sales_usd": values})


def india_state_sales(total_sales_inr: float) -> pd.DataFrame:
    states = ["Maharashtra", "Karnataka", "Delhi", "Tamil Nadu", "Gujarat"]
    parts = np.random.dirichlet(np.array([3.2, 2.4, 2.2, 2.0, 1.8]), size=1)[0]
    values = np.round(parts * total_sales_inr, 2)
    return pd.DataFrame({"state": states, "sales_inr": values})


def weather_recommendation(temp_c: float, lang: str) -> str:
    if temp_c > 35:
        return tr("Hot weather: keep more cold drinks and light products ready.", lang)
    if temp_c < 20:
        return tr("Cool weather: promote warm clothes and hot beverages.", lang)
    return tr("Normal weather: keep regular stock and staff planning.", lang)


def market_sentiment(btc_price: float):
    if btc_price >= 70000:
        return "Positive", "Luxury demand may rise because confidence looks strong."
    if btc_price <= 60000:
        return "Negative", "Luxury demand may slow; buyers can become careful."
    return "Neutral", "Luxury demand may stay stable with balanced spending."


def create_simple_pdf(report_text: str) -> bytes:
    clean = report_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lines = clean.splitlines()
    y = 780
    content = ["BT", "/F1 11 Tf"]
    for line in lines:
        content.append(f"36 {y} Td ({line[:105]}) Tj")
        y -= 15
        content.append("0 0 Td")
        if y < 72:
            break
    content.append("ET")
    stream_data = "\n".join(content).encode("latin-1", errors="replace")

    objs = []
    objs.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj")
    objs.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj")
    objs.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj"
    )
    objs.append(f"4 0 obj << /Length {len(stream_data)} >> stream\n".encode("latin-1") + stream_data + b"\nendstream endobj")
    objs.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(pdf))
        pdf.extend(obj + b"\n")
    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010} 00000 n \n".encode("latin-1"))
    pdf.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode("latin-1")
    )
    return bytes(pdf)


def figure_png_bytes(fig: go.Figure):
    try:
        return fig.to_image(format="png", width=1280, height=720, scale=2), None
    except Exception as exc:
        logging.exception("PNG export failed: %s", exc)
        return None, "Chart image export is unavailable right now."


def toast_once(key: str, message: str, icon: str = "ℹ️") -> None:
    shown = st.session_state.setdefault("shown_toasts", set())
    if key not in shown:
        st.toast(message, icon=icon)
        shown.add(key)


def main():
    inject_styles()

    # Trigger periodic refresh on browser level.
    st.markdown(f"<meta http-equiv='refresh' content='{DASHBOARD_REFRESH}'>", unsafe_allow_html=True)

    if "last_refresh_ts" not in st.session_state:
        st.session_state.last_refresh_ts = int(time.time())
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False

    st.sidebar.title("⚙️ Dashboard Controls")
    language_name = st.sidebar.selectbox("🌐 Select Language", list(LANGUAGES.keys()), index=0)
    lang_code = LANGUAGES[language_name]
    dark_mode = st.sidebar.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
    st.session_state.dark_mode = dark_mode
    if dark_mode:
        inject_dark_mode_styles()
    if st.sidebar.button("🔔 Reset Notifications", use_container_width=True):
        st.session_state["shown_toasts"] = set()
        st.sidebar.success(tr("Notifications reset. Alerts can show again.", lang_code))
    manual_refresh = st.sidebar.button("🔄 Refresh Now", use_container_width=True, help=tr("Refresh all live numbers now", lang_code))
    if manual_refresh:
        st.cache_data.clear()
        st.session_state.last_refresh_ts = int(time.time())
        toast_once("manual_refresh", "🔄 " + tr("Dashboard refreshed with latest live values.", lang_code), icon="✅")
        st.rerun()

    st.sidebar.markdown(f"**{tr('Auto-refresh every 30 seconds', lang_code)}**")
    remaining = max(0, DASHBOARD_REFRESH - ((int(time.time()) - st.session_state.last_refresh_ts) % DASHBOARD_REFRESH))
    st.sidebar.progress((DASHBOARD_REFRESH - remaining) / DASHBOARD_REFRESH)
    st.sidebar.caption(f"⏳ {tr('Next refresh in', lang_code)}: {remaining}s")

    currency_rate, currency_error = get_currency_rate()
    weather_temp, weather_ic, weather_error = get_weather_mumbai()
    btc_price, btc_error = get_btc_price()
    for err in [currency_error, weather_error, btc_error]:
        if err:
            st.sidebar.warning(tr(err, lang_code))

    now = ist_now()
    sales_df = build_sales_series(now)
    current_row = sales_df.iloc[-1]
    prev_row = sales_df.iloc[-2]

    sales_usd = float(current_row["sales_usd"])
    sales_inr = sales_usd * currency_rate
    orders = int(current_row["orders"])
    active_customers = int(current_row["active_customers"])
    delta_sales = ((sales_usd - float(prev_row["sales_usd"])) / max(float(prev_row["sales_usd"]), 1)) * 100
    delta_orders = ((orders - int(prev_row["orders"])) / max(int(prev_row["orders"]), 1)) * 100
    delta_cust = ((active_customers - int(prev_row["active_customers"])) / max(int(prev_row["active_customers"]), 1)) * 100
    delta_inr = delta_sales

    col_h1, col_h2, col_h3 = st.columns([2.1, 1.5, 1.4])
    with col_h1:
        st.title(f"🚀 {tr('LIVE Smart Sales Dashboard', lang_code)}")
    with col_h2:
        st.markdown(f"### ⏰ {tr('IST Time', lang_code)}: `{now.strftime('%H:%M:%S')}`")
    with col_h3:
        st.markdown(
            f"### 🌐 `{language_name}` <span class='live-badge'>🟢 LIVE</span>",
            unsafe_allow_html=True,
        )

    st.caption(tr("This page uses live APIs + smart simulation. Numbers update automatically.", lang_code))
    st.markdown("---")

    weather_text = f"{weather_temp:.1f}°C {weather_ic}"
    weather_tip = weather_recommendation(weather_temp, lang_code)

    k1, k2, k3, k4, k5 = st.columns(5)
    cards = [
        (k1, f"💵 {tr('Live Sales (USD)', lang_code)}", f"${sales_usd:,.2f}", delta_sales, tr("Current hour", lang_code)),
        (k2, f"💰 {tr('Live Sales (INR)', lang_code)}", f"₹{sales_inr:,.2f}", delta_inr, tr("Converted live rate", lang_code)),
        (k3, f"📦 {tr('Live Orders', lang_code)}", f"{orders:,}", delta_orders, tr("Current hour orders", lang_code)),
        (k4, f"👥 {tr('Active Customers', lang_code)}", f"{active_customers:,}", delta_cust, tr("Users shopping now", lang_code)),
        (k5, f"🌤️ {tr('Weather Impact', lang_code)}", weather_text, 0.0, weather_tip),
    ]

    for col, title, value, delta, subtitle in cards:
        with col:
            delta_class = "positive" if delta >= 0 else "negative"
            delta_text = f"{delta:+.1f}%"
            st.markdown(
                f"""
                <div class="kpi-card" aria-label="{title}">
                    <div class="kpi-title">{title}</div>
                    <div class="kpi-value" title="{tr('Live value', lang_code)}">{value}</div>
                    <div class="{delta_class}" title="{tr('Change from previous hour', lang_code)}">{delta_text}</div>
                    <div class="kpi-sub">{subtitle}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("### 📊 " + tr("Live Charts", lang_code))
    left, right = st.columns(2)

    with left:
        with st.spinner(tr("Loading live sales trend...", lang_code)):
            chart_df = sales_df.copy()
            chart_df["hour_label"] = chart_df["timestamp"].dt.strftime("%d-%b %H:00")
            fig_line = px.line(
                chart_df,
                x="hour_label",
                y="sales_usd",
                markers=True,
                title=tr("📈 LIVE Sales Trend (Last 24 Hours)", lang_code),
                labels={
                    "hour_label": tr("Hours (1-24)", lang_code),
                    "sales_usd": tr("Sales in USD", lang_code),
                },
                template="plotly_white",
            )
            fig_line.update_layout(
                transition={"duration": 500},
                hovermode="x unified",
                template="plotly_dark" if dark_mode else "plotly_white",
            )
            fig_line.update_traces(
                hovertemplate=f"{tr('Hour', lang_code)}: %{{x}}<br>{tr('Sales', lang_code)}: $%{{y:,.2f}}<extra></extra>"
            )
            st.plotly_chart(fig_line, use_container_width=True)
            line_png, line_png_err = figure_png_bytes(fig_line)
            if line_png:
                st.download_button(
                    "🖼️ " + tr("Download Trend PNG", lang_code),
                    data=line_png,
                    file_name="live_sales_trend.png",
                    mime="image/png",
                    use_container_width=True,
                )
            elif line_png_err:
                st.info(tr(line_png_err, lang_code))

    with right:
        with st.spinner(tr("Loading category split...", lang_code)):
            cat_df = category_split(sales_usd)
            cat_df["category_t"] = cat_df["category"].map(lambda x: tr(x, lang_code))
            fig_pie = px.pie(
                cat_df,
                names="category_t",
                values="sales_usd",
                title=tr("🥧 LIVE Category Sales", lang_code),
                template="plotly_white",
            )
            fig_pie.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate=f"%{{label}}<br>{tr('Sales', lang_code)}: $%{{value:,.2f}}<extra></extra>",
            )
            fig_pie.update_layout(template="plotly_dark" if dark_mode else "plotly_white")
            st.plotly_chart(fig_pie, use_container_width=True)
            pie_png, pie_png_err = figure_png_bytes(fig_pie)
            if pie_png:
                st.download_button(
                    "🖼️ " + tr("Download Pie PNG", lang_code),
                    data=pie_png,
                    file_name="live_category_sales.png",
                    mime="image/png",
                    use_container_width=True,
                )
            elif pie_png_err:
                st.info(tr(pie_png_err, lang_code))

    st.markdown("### 📍 " + tr("LIVE Sales Heatmap - India", lang_code))
    with st.spinner(tr("Loading state sales...", lang_code)):
        state_df = india_state_sales(sales_inr * random.uniform(4.2, 6.8))
        state_df["state_t"] = state_df["state"].map(lambda x: tr(x, lang_code))
        fig_bar = px.bar(
            state_df,
            x="state_t",
            y="sales_inr",
            color="sales_inr",
            color_continuous_scale="Blues",
            title=tr("📍 LIVE Sales Heatmap - India", lang_code),
            labels={"state_t": tr("State", lang_code), "sales_inr": tr("Sales in INR", lang_code)},
            template="plotly_white",
        )
        fig_bar.update_layout(template="plotly_dark" if dark_mode else "plotly_white")
        fig_bar.update_traces(hovertemplate=f"%{{x}}<br>{tr('Sales', lang_code)}: ₹%{{y:,.0f}}<extra></extra>")
        st.plotly_chart(fig_bar, use_container_width=True)
        bar_png, bar_png_err = figure_png_bytes(fig_bar)
        if bar_png:
            st.download_button(
                "🖼️ " + tr("Download Heatmap PNG", lang_code),
                data=bar_png,
                file_name="live_state_sales.png",
                mime="image/png",
                use_container_width=True,
            )
        elif bar_png_err:
            st.info(tr(bar_png_err, lang_code))

    st.markdown("### 🚨 " + tr("Live Alerts & Insights", lang_code))
    alert_msgs = []
    if sales_inr > SPIKE_THRESHOLD_INR:
        alert_msgs.append(("warning", tr("Sales are very high now. Add more staff and stock quickly.", lang_code)))
    if sales_inr < DROP_THRESHOLD_INR:
        alert_msgs.append(("info", tr("Sales are low now. Try a simple discount or short campaign.", lang_code)))
    if weather_temp > 35 or weather_temp < 20:
        alert_msgs.append(("warning", tr("Weather is extreme. Adjust products and delivery planning.", lang_code)))
    if not alert_msgs:
        alert_msgs.append(("success", tr("All looks stable. Keep current plan.", lang_code)))

    for level, msg in alert_msgs:
        if level == "warning":
            st.warning("⚠️ " + msg)
            toast_once(f"warning::{msg}", "⚠️ " + msg, icon="⚠️")
        elif level == "info":
            st.info("ℹ️ " + msg)
            toast_once(f"info::{msg}", "ℹ️ " + msg, icon="ℹ️")
        else:
            st.success("✅ " + msg)

    st.markdown("### 🔮 " + tr("LIVE Prediction (Next Hour)", lang_code))
    rolling = sales_df["sales_usd"].tail(5).mean()
    confidence = round(random.uniform(75, 95), 1)
    if rolling > sales_usd:
        rec = tr("Expected growth next hour. Keep checkout counters ready.", lang_code)
    else:
        rec = tr("Expected soft hour. Use offers to increase conversions.", lang_code)
    st.markdown(
        f"""
        <div class="simple-box">
            <div><b>{tr('Predicted next-hour sales', lang_code)}:</b> ${rolling:,.2f} / ₹{rolling * currency_rate:,.2f}</div>
            <div><b>{tr('Confidence', lang_code)}:</b> {confidence:.1f}%</div>
            <div><b>{tr('Recommendation', lang_code)}:</b> {rec}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 📈 " + tr("Market Correlation", lang_code))
    mood, expl = market_sentiment(btc_price)
    mood_t = tr(mood, lang_code)
    st.write(f"₿ **{tr('Live Bitcoin Price', lang_code)}:** `${btc_price:,.2f}`")
    mood_color = "positive" if mood == "Positive" else ("negative" if mood == "Negative" else "warning")
    st.markdown(
        f"<span class='{mood_color}'>{tr('Market sentiment', lang_code)}: {mood_t}</span>",
        unsafe_allow_html=True,
    )
    st.caption(tr(expl, lang_code))

    st.markdown("### 📤 " + tr("Data Export", lang_code))
    export_df = sales_df.copy()
    export_df["sales_inr"] = export_df["sales_usd"] * currency_rate
    csv_data = export_df.to_csv(index=False).encode("utf-8")
    report = (
        "Live Smart Sales Dashboard Report\n"
        f"Generated IST: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Language: {language_name}\n"
        f"Current Sales USD: {sales_usd:,.2f}\n"
        f"Current Sales INR: {sales_inr:,.2f}\n"
        f"Orders: {orders}\n"
        f"Active Customers: {active_customers}\n"
        f"Weather: {weather_temp:.1f} C {weather_ic}\n"
        f"Bitcoin: {btc_price:,.2f} USD\n"
        f"Prediction Next Hour USD: {rolling:,.2f}\n"
        f"Confidence: {confidence:.1f}%\n"
    )
    pdf_bytes = create_simple_pdf(report)

    e1, e2, e3 = st.columns(3)
    with e1:
        st.download_button(
            "📥 " + tr("Download CSV", lang_code),
            data=csv_data,
            file_name="live_sales_dashboard.csv",
            mime="text/csv",
            use_container_width=True,
            help=tr("Download all visible sales data as CSV", lang_code),
        )
    with e2:
        st.download_button(
            "🧾 " + tr("Download PDF Report", lang_code),
            data=pdf_bytes,
            file_name="live_sales_report.pdf",
            mime="application/pdf",
            use_container_width=True,
            help=tr("Download a simple PDF report", lang_code),
        )
    with e3:
        if st.button("📧 " + tr("Email Report (Simulated)", lang_code), use_container_width=True):
            st.success("✅ " + tr("Report sent successfully (simulation).", lang_code))
            toast_once("email_report", "📧 " + tr("Email sent successfully (simulation).", lang_code), icon="✅")

    st.markdown("### 🗂️ " + tr("Download All Charts", lang_code))
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        if line_png:
            zf.writestr("live_sales_trend.png", line_png)
        if pie_png:
            zf.writestr("live_category_sales.png", pie_png)
        if bar_png:
            zf.writestr("live_state_sales.png", bar_png)
    zip_data = zip_buffer.getvalue()
    if zip_data:
        st.download_button(
            "🗃️ " + tr("Download All Charts ZIP", lang_code),
            data=zip_data,
            file_name="live_sales_charts.zip",
            mime="application/zip",
            use_container_width=True,
            help=tr("Download all chart images together in one ZIP file.", lang_code),
        )

    st.markdown("### ♿ " + tr("Simple Help Tips", lang_code))
    st.markdown(
        f"""
        <div class="helper">
            • {tr("Green means good, red means attention needed, yellow means caution.", lang_code)}<br>
            • {tr("Tap refresh if you want the latest values immediately.", lang_code)}<br>
            • {tr("Move mouse over charts to see simple explanations for numbers.", lang_code)}<br>
            • {tr("Buttons are large for easy tapping on phone and tablet.", lang_code)}
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    lock = threading.Lock()
    with lock:
        main()

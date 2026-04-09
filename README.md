# Live Smart Sales Dashboard with Multi-Language Support

A production-ready Streamlit dashboard that combines live API data, smart sales simulation, translated UI text, and simple export/reporting tools for business monitoring.

## Features

- Live currency exchange (`USD -> INR`) with fallback and warning handling
- Live Mumbai weather with weather impact guidance
- Live Bitcoin price for market correlation view
- Live IST display and auto-refresh controls
- Smart sales simulation based on business hours (9 AM to 9 PM)
- 5 KPI cards with trend deltas and simple labels
- Interactive charts:
  - 24-hour sales trend (line)
  - category sales split (pie)
  - India state sales heatmap (bar gradient)
- Real-time alerts and plain-language recommendations
- Next-hour sales prediction using moving average
- Data exports:
  - CSV download
  - PDF report download
  - simulated email report action
- Multi-language support (50+ languages) with cached Google translation
- Accessibility-minded UI:
  - larger tap targets
  - emoji-led sections
  - high-contrast text
  - simple helper text and tooltips

## Tech Stack

- Python 3.10
- Streamlit
- Plotly
- Pandas
- NumPy
- Requests
- deep-translator (GoogleTranslator)

## Project Files

- `app.py` - main dashboard app
- `config.py` - endpoints, refresh intervals, fallbacks, language list
- `requirements.txt` - pinned dependencies
- `README.md` - setup and usage guide

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

App URL (default): [http://localhost:8501](http://localhost:8501)

## API Sources

- Currency: [ExchangeRate API](https://api.exchangerate-api.com/v4/latest/USD)
- Weather: [Open-Meteo API](https://api.open-meteo.com/v1/forecast)
- Crypto: [CoinGecko API](https://api.coingecko.com/api/v3/simple/price)

## Supported Languages

Includes 50+ languages, covering all required Indian and international options:

- Indian: हिन्दी, தமிழ், తెలుగు, ಕನ್ನಡ, മലയാളം, বাংলা, मराठी, ગુજરાતી, ਪੰਜਾਬੀ, ଓଡ଼ିଆ
- International: English, Español, Français, Deutsch, 中文, 日本語, العربية, Русский
- Additional languages are included in `config.py` through the `LANGUAGES` dictionary.

## Screenshot Placeholders

- `docs/screenshot-dashboard-main.png` (placeholder)
- `docs/screenshot-charts.png` (placeholder)
- `docs/screenshot-mobile.png` (placeholder)

## Troubleshooting

- **API errors or empty internet connection**
  - The dashboard continues with fallback values and shows warnings in sidebar.
- **Translation is slow for first time**
  - First call per phrase/language may take time, then cache is used.
- **Port 8501 in use**
  - Run: `streamlit run app.py --server.port 8502`
- **Dependency conflict**
  - Recreate virtual environment and reinstall from `requirements.txt`.
- **PDF download not opening**
  - Ensure browser finished download; open with any standard PDF viewer.

## Production Notes

- Replace simulated sales generator with real POS/source-of-truth integration.
- Add authentication and role-based access before public deployment.
- Configure proper logging sink (file or cloud) if running at scale.

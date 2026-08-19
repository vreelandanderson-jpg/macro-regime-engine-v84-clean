# Deploy v9.9

## Standard / cloud

```bash
pip install -r requirements.txt
streamlit run app.py
```

Configure `MASSIVE_API_KEY` and/or `DATABENTO_API_KEY` in Streamlit Secrets or the in-app LIVE DATA CONNECTIONS panel.

## Windows + local MT5 broker feed

```bash
pip install -r requirements-mt5-windows.txt
streamlit run app.py
```

Keep the MT5 terminal open and logged in. The app auto-discovers it. Use `MT5_TERMINAL_PATH` only when more than one terminal is installed or auto-discovery selects the wrong one.

## Important

A provider plan may be delayed even though the connection itself is healthy. v9.9 uses the provider event timestamp; delayed events cannot become LIVE simply because the UI refreshed.

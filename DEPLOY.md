# v9.7 deployment

1. Replace the current repo files with this build.
2. Push to the same GitHub repository used by the Streamlit app.
3. In Streamlit Cloud open **Manage app -> Settings -> Secrets**.
4. Add:

```toml
MASSIVE_API_KEY = "..."
DATABENTO_API_KEY = "..."
```

5. Reboot/redeploy the app after saving secrets.
6. Open **Data Health** in the app.
7. Confirm provider rows show `LIVE` for the channels your plans entitle.
8. Confirm active instruments show a real `provider_ts`, `market_age_sec`, and a direct source such as `Databento · GLBX.MDP3` or `Massive · Stocks/Indices/...`.
9. A provider or symbol that cannot be verified must show `STALE`, `OFFLINE`, `CLOSED`, or fallback status — never a synthetic price.

# Quote Detection Rules

1. A schedule never creates LIVE or EXTENDED.
2. A valid price plus provider timestamp <=25 seconds old is required.
3. Exact symbol quotes win.
4. NDX/SPX/Dow/Russell may use a fresh real futures level after their reference quote stops; it is labeled ECONOMIC EQUIVALENT and the reference price remains visible.
5. If no fresh real quote exists, state is STALE or UNAVAILABLE. No fabricated price is allowed.
6. dxFeed production entitlements determine which overnight U.S. securities actually return quotes.

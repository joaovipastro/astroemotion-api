# Astroemotion Chart API

FastAPI + Kerykeion 6.0.5, Python 3.12.14.

Build: `pip install -r requirements.txt`

Start: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log`

Set PYTHON_VERSION=3.12.14. Health check: /health. Interactive API: /docs. Source download: /source.

POST /natal-chart accepts date, local time, latitude, longitude, IANA timezone, language (EN/ES/PT), houses (P/W), and optional is_dst. Returns SVG and planetary/house data. Supported years: 1850–2149. Nonexistent or unresolved ambiguous clock times are rejected. Polar latitudes require Whole Sign houses.

Example: {"date":"1940-10-09","time":"18:30","latitude":53.4,"longitude":-2.9833,"timezone":"Europe/London"}

Birth inputs are processed in memory without application persistence. Access logging is disabled; the provider may retain infrastructure logs. CORS allows Astroemotion origins but is not authentication. Concurrent calculations receive 429 and can retry. Free hosting sleeps when idle; use paid always-on compute for production.

This service does not yet connect the website form or provide birthplace search.

## License

This service is free software under GNU Affero General Public License version 3. It comes WITHOUT ANY WARRANTY, including MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. License text: https://www.gnu.org/licenses/agpl-3.0.html

Corresponding source is available here and at /source. Dependencies are pinned and installed unchanged from PyPI. Kerykeion source: https://github.com/g-battaglia/kerykeion (v6.0.5). Libephemeris source: https://github.com/g-battaglia/libephemeris (v3.2.2). Upstream notices remain in their installed packages.

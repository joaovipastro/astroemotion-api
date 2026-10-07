"""Astroemotion chart API. Birth inputs are processed in memory, never persisted."""
from datetime import date, datetime, time, timezone
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import os
import zipfile

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from kerykeion import AstrologicalSubjectFactory, ChartDataFactory, ChartDrawer

app = FastAPI(title='Astroemotion Chart API', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv('ALLOWED_ORIGINS', 'https://astroemotion.com,https://www.astroemotion.com,https://astroemotion.joaovip.chatgpt.site').split(','),
    allow_methods=['POST', 'GET'], allow_headers=['Content-Type'],
)
# Ephemeris backends have shared state; serialize calculations within one worker.
calculation_lock = Lock()
POINTS = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto', 'Ascendant', 'Medium_Coeli']

class BirthInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    date: date
    time: time
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    timezone: str = Field(min_length=1, max_length=80)
    language: Literal['EN', 'ES', 'PT'] = 'EN'
    houses: Literal['P', 'W'] = 'P'
    is_dst: bool | None = None

    @model_validator(mode='after')
    def validate_birth(self):
        if not 1850 <= self.date.year < 2150:
            raise ValueError('Supported years are 1850–2149.')
        if self.time.tzinfo is not None:
            raise ValueError('Supply local clock time without a UTC offset.')
        try:
            zone = ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('Use an IANA timezone such as America/Sao_Paulo.')
        wall = datetime.combine(self.date, self.time)
        first, second = (wall.replace(tzinfo=zone, fold=i) for i in (0, 1))
        valid = [dt for dt in (first, second) if dt.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == wall]
        if not valid:
            raise ValueError('This local time did not exist due to a clock change.')
        if first.utcoffset() != second.utcoffset() and self.is_dst is None:
            raise ValueError('This local time occurred twice; specify is_dst to resolve it.')
        if self.houses == 'P' and abs(self.latitude) >= 66:
            raise ValueError('Use Whole Sign houses (W) for polar latitudes.')
        return self

@app.middleware('http')
async def privacy_headers(request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.get('/health')
def health():
    return {'status': 'ok', 'engine': 'kerykeion', 'version': '6.0.5'}

@app.get('/')
def info():
    return {'service': 'Astroemotion Chart API', 'docs': '/docs', 'source': '/source', 'license': 'AGPL-3.0'}

@app.get('/source')
def source():
    """Expose this service's corresponding source without secrets or local files."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in ['main.py', 'requirements.txt', 'requirements.in', 'render.yaml', 'README.md', 'LICENSE', 'test_api.py', '.python-version']:
            path = Path(__file__).parent / name
            if path.is_file():
                archive.write(path, arcname=name)
    return Response(buffer.getvalue(), media_type='application/zip', headers={'Content-Disposition': 'attachment; filename=astroemotion-backend-source.zip'})

@app.post('/natal-chart')
def natal_chart(birth: BirthInput):
    if not calculation_lock.acquire(blocking=False):
        raise HTTPException(429, 'A chart is being calculated. Please retry shortly.', headers={'Retry-After': '3'})
    try:
        subject = AstrologicalSubjectFactory.from_birth_data(
            'Birth chart', birth.date.year, birth.date.month, birth.date.day,
            birth.time.hour, birth.time.minute, seconds=birth.time.second,
            lng=birth.longitude, lat=birth.latitude, tz_str=birth.timezone,
            online=False, suppress_geonames_warning=True, active_points=POINTS,
            houses_system_identifier=birth.houses, is_dst=birth.is_dst,
        )
        chart = ChartDataFactory.create_natal_chart_data(subject)
        svg = ChartDrawer(chart, chart_language=birth.language).generate_svg_string(style='modern')
        return {'svg': svg, 'subject': subject.model_dump(mode='json'), 'engine': 'kerykeion', 'source': '/source'}
    except Exception as exc:
        # Do not log request details or echo internal paths to the caller.
        raise HTTPException(422, 'The chart could not be calculated for these details.') from exc
    finally:
        calculation_lock.release()

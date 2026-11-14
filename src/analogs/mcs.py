"""MRO Mars Climate Sounder (MCS): surface temperature day AND night (for t_mean_K).

The TES retrievals we use for dust and t_max_K are daytime only (~14 h). MCS observes at
~03 h and ~15 h local time, so it gives the night side too.

MCS Derived Data Records (PDS Atmospheres, version 6.2) are huge (~43 MB per Earth day,
~30 GB per Mars year), so we:
  - take one Mars year without a global dust storm: Mars Year 31 (2011-09-13 → 2013-07-30),
  - sample one Earth day every `step_days` and two 4-hour files per day (00 h and 12 h UTC);
    every orbit crosses both the day and the night side, so this still covers all seasons,
  - keep ONLY the surface-temperature columns of each profile, copied as they are
    (no unit change, no filtering), one small CSV per source file.

Output: data/raw/mars/mcs_tsurf_my31/<YYYYMMDDHH>_tsurf.csv  (+ MANIFEST.csv rows with the
original URL and byte size of each source file).
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re
from pathlib import Path

import requests

BASE = "https://atmos.nmsu.edu/PDS/data"
MY31_START = dt.date(2011, 9, 13)   # Ls = 0°, Mars Year 31 (checked: 2011-07-31 is still Ls 337° of MY30)
MY31_END = dt.date(2013, 7, 30)     # day before Ls = 0°, Mars Year 32

# Notes for reading the extract (task 3.5):
#   LTST is a FRACTION OF A SOL (0.0–1.0), not hours: ~0.0–0.1 = night (~03 h), ~0.5–0.6 = day (~15 h).
#   T_surf = -9999 means no retrieval for that profile (common): drop those rows.
#   Surf_lon is −180…180 east; Surf_lat planetocentric.

# Columns kept from the profile records (DDR1) of each file
KEEP = ["Date", "UTC", "L_s", "LTST", "Surf_lat", "Surf_lon", "T_surf", "T_surf_err", "surf_qual"]


def volume_for(day: dt.date) -> str:
    """MCS archive volume: one per Earth month, MROM_2001 = September 2006."""
    months = (day.year - 2006) * 12 + (day.month - 9)
    return f"MROM_{2001 + months}"


def file_url(day: dt.date, hour: int) -> str:
    ymd = day.strftime("%Y%m%d")
    return f"{BASE}/{volume_for(day)}/DATA/{day:%Y}/{day:%Y%m}/{ymd}/{ymd}{hour:02d}_DDR.TAB"


def sample_files(step_days: int = 10, hours: tuple[int, ...] = (0, 12)) -> list[tuple[dt.date, int]]:
    days, d = [], MY31_START
    while d <= MY31_END:
        days.append(d)
        d += dt.timedelta(days=step_days)
    return [(d, h) for d in days for h in hours]


def extract_tsurf(text: str) -> list[dict]:
    """Keep the KEEP columns of every profile record (DDR1) in an MCS DDR file."""
    header = None
    rows = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        fields = [f.strip().strip('"') for f in line.split(",")]
        if header is None:
            if "T_surf" in fields:            # first header line = profile (DDR1) columns
                header = fields
            continue
        if len(fields) == len(header) and fields[0] == "0":   # profile record (DDR1)
            rec = dict(zip(header, fields))
            rows.append({k: rec.get(k, "") for k in KEEP})
    return rows


def _available_hours(s: requests.Session, day: dt.date) -> list[int]:
    """4-hour files that exist for a day (some days have gaps in the archive)."""
    folder = file_url(day, 0).rsplit("/", 1)[0] + "/"
    r = s.get(folder, timeout=60)
    if r.status_code != 200:
        return []
    return sorted({int(h) for h in re.findall(rf"{day:%Y%m%d}(\d\d)_DDR\.TAB", r.text)})


def download_mcs_tsurf(dest: Path, step_days: int = 10, session: requests.Session | None = None,
                       log=print) -> list[dict]:
    """Download the sampled files, keep the T_surf columns, return MANIFEST rows.

    If the planned 4-hour file of a day is missing (gaps in the archive), another file of
    the same day that was not used yet is taken instead.
    """
    dest.mkdir(parents=True, exist_ok=True)
    s = session or requests.Session()
    manifest = []
    jobs = sample_files(step_days)
    used: dict[dt.date, set[int]] = {}
    for i, (day, hour) in enumerate(jobs, 1):
        url = file_url(day, hour)
        if s.head(url, timeout=60).status_code == 404:
            spare = [h for h in _available_hours(s, day) if h not in used.get(day, set())
                     and h not in [hh for (dd, hh) in jobs if dd == day]]
            if spare:
                hour = min(spare, key=lambda h: abs(h - hour))
                url = file_url(day, hour)
                log(f"  [{i:3d}/{len(jobs)}] planned file missing, using {day:%Y%m%d}{hour:02d} instead")
            elif not _available_hours(s, day):
                # Whole day missing: try the next few days, same hour (the archive has gaps,
                # e.g. no MCS data at all from 2012-08-07 to 2012-09-07)
                for shift in range(1, 4):
                    alt = day + dt.timedelta(days=shift)
                    if hour in _available_hours(s, alt):
                        log(f"  [{i:3d}/{len(jobs)}] day {day:%Y%m%d} missing, using {alt:%Y%m%d}{hour:02d} instead")
                        day, url = alt, file_url(alt, hour)
                        break
        used.setdefault(day, set()).add(hour)
        out = dest / f"{day:%Y%m%d}{hour:02d}_tsurf.csv"
        if out.exists() and out.stat().st_size > 0:
            manifest.append({"dataset": dest.name, "file": out.name, "url": url,
                             "bytes": out.stat().st_size, "status": "ya estaba"})
            log(f"  [{i:3d}/{len(jobs)}] {out.name}: skipped (already there)")
            continue
        try:
            r = s.get(url, timeout=300)
            if r.status_code == 404:
                manifest.append({"dataset": dest.name, "file": out.name, "url": url, "bytes": 0,
                                 "status": "no existe (hueco en el archivo)"})
                log(f"  [{i:3d}/{len(jobs)}] {out.name}: not in the archive (404)")
                continue
            r.raise_for_status()
            # Decode explicitly: r.text would run charset detection on 7 MB, which takes minutes
            rows = extract_tsurf(r.content.decode("latin-1"))
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=KEEP)
            w.writeheader()
            w.writerows(rows)
            out.write_text(buf.getvalue(), encoding="utf-8")
            manifest.append({"dataset": dest.name, "file": out.name, "url": url,
                             "bytes": out.stat().st_size, "status": "ok"})
            log(f"  [{i:3d}/{len(jobs)}] {out.name}: {len(rows)} profiles "
                f"(from {len(r.content) / 1e6:.1f} MB)")
        except Exception as e:  # keep going, record the error
            manifest.append({"dataset": dest.name, "file": out.name, "url": url, "bytes": 0,
                             "status": f"ERROR {type(e).__name__}: {str(e)[:100]}"})
            log(f"  [{i:3d}/{len(jobs)}] {out.name}: ERROR {e}")
    return manifest

#!/usr/bin/env python3
"""Edge Finder hosted data pipeline. Stdlib only; fail closed on malformed sources.

Public site: generated historical aggregate datasets only, never credentials or betting journals.
A cache from prior GitHub Actions runs retains last verified bytes during source outages.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / '.cache' / 'feeds'
OUT = ROOT / 'site' / 'data' / 'edge-data.js'
NOW = datetime.now(timezone.utc)
UA = 'EdgeFinder-Historical-Research/4.1 (+GitHub-Pages; historical data only)'
MAX_SOURCE_BYTES = 24 * 1024 * 1024


def header_norm(name):
    return re.sub(r'[^a-z0-9]+', '', str(name).lower().removeprefix('\ufeff'))


def pick(row, *names):
    lookup = {header_norm(k): str(v or '').strip() for k, v in row.items() if k}
    return next((lookup.get(header_norm(n), '') for n in names if lookup.get(header_norm(n), '')), '')


def csv_rows(data):
    if isinstance(data, bytes):
        data = data.decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(data, newline='')))


def check_csv(data, kind):
    if not data or len(data) < 400 or b'\0' in data[:300]:
        return False
    if data.lstrip()[:100].lower().startswith((b'<!doctype html', b'<html', b'{"message"')):
        return False
    try:
        stream = io.StringIO(data.decode('utf-8-sig'))
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(reader.fieldnames) < 3:
            return False
        fields = {header_norm(v) for v in reader.fieldnames}
        if kind == 'nfl' and not {'season', 'week'}.issubset(fields):
            return False
        if kind == 'games' and not {'season', 'week'}.issubset(fields):
            return False
        if kind == 'ufc' and not (('bout' in fields) or {'rfighter','bfighter'}.issubset(fields) or {'fighter1','fighter2'}.issubset(fields)):
            return False
        if kind == 'events' and not any('date' in n for n in fields):
            return False
        return sum(1 for _, row in zip(range(15), reader) if any((v or '').strip() for v in row.values())) >= 5
    except (ValueError, UnicodeError, csv.Error):
        return False


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/csv,application/octet-stream,*/*'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        chunks = []
        length = 0
        while True:
            chunk = response.read(1024 * 128)
            if not chunk:
                break
            length += len(chunk)
            if length > MAX_SOURCE_BYTES:
                raise ValueError('Source exceeded 24MB limit')
            chunks.append(chunk)
    return b''.join(chunks)


def load_source(name, url, kind, issues, meta, timeout=25):
    """Download fresh when possible; only validated and cacheable rows are used."""
    CACHE.mkdir(parents=True, exist_ok=True)
    filename = CACHE / (name + '.csv')
    errors = []
    for n in range(2):
        try:
            data = fetch(url, timeout=timeout)
            if not check_csv(data, kind):
                raise ValueError('unexpected CSV schema or too few records')
            filename.write_bytes(data)
            meta[name] = {'state': 'downloaded', 'checked_utc': NOW.isoformat(timespec='seconds'), 'bytes': len(data), 'origin': url}
            return data.decode('utf-8-sig')
        except (TimeoutError, OSError, ValueError, UnicodeError, urllib.error.URLError) as err:
            errors.append(str(err)[:150])
            if n == 0:
                time.sleep(1)
    if filename.exists():
        data = filename.read_bytes()
        if check_csv(data, kind):
            issues.append(f'{name}: source failed; using previous verified cache')
            meta[name] = {'state': 'cached', 'checked_utc': NOW.isoformat(timespec='seconds'), 'bytes': len(data), 'origin': url}
            return data.decode('utf-8-sig')
    issues.append(f'{name}: unavailable ({errors[-1] if errors else "unknown error"})')
    meta[name] = {'state': 'missing', 'checked_utc': NOW.isoformat(timespec='seconds'), 'bytes': 0, 'origin': url}
    return ''


def parse_date(s):
    s = (s or '').strip()
    if not s:
        return ''
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y'):
        try:
            d = datetime.strptime(s[:35], fmt).date()
            return d.isoformat() if 1993 <= d.year <= NOW.year + 1 else ''
        except ValueError:
            pass
    match = re.match(r'(20\d{2}-\d{2}-\d{2})', s)
    return match.group(1) if match else ''


def event_lookup(raw):
    out = {}
    for r in csv_rows(raw):
        d = parse_date(pick(r, 'event_date', 'date'))
        if not d:
            continue
        for name in ('event_url','event_name','event','event_id'):
            v = pick(r, name)
            if v:
                out[v.lower()] = d
    return out


def normalize_ufc(fight_csv, event_csv):
    """Support Greco1899 BOUT/OUTCOME format and Pavan fighter-name formats."""
    events = event_lookup(event_csv)
    results = {}
    for r in csv_rows(fight_csv):
        a = pick(r,'r_fighter','red_fighter','fighter_1','fighter1','fighter_a','red_name','r_name')
        b = pick(r,'b_fighter','blue_fighter','fighter_2','fighter2','fighter_b','blue_name','b_name')
        bout = pick(r,'bout')
        if not a or not b:
            split = re.split(r'\s+vs\.?\s+', bout, flags=re.I)
            if len(split) == 2:
                a, b = [x.strip() for x in split]
        if not a or not b or a.lower() == b.lower():
            continue
        result = pick(r,'winner','winning_fighter','winner_name','victor','fight_winner','result')
        win = ''
        if result.lower() == a.lower() or result.lower() in ('red','r','fighter1','fighter_1','a','1'):
            win = a
        elif result.lower() == b.lower() or result.lower() in ('blue','b','fighter2','fighter_2','2'):
            win = b
        outcome = pick(r,'outcome')
        if not win and outcome:
            scores = [v.strip().upper() for v in re.split(r'\s*/\s*', outcome)]
            if len(scores) == 2 and scores == ['W','L']:
                win = a
            elif len(scores) == 2 and scores == ['L','W']:
                win = b
        if not win:
            continue  # Draw / NC are not classed as wins.
        ev = pick(r,'event_url','event_name','event','event_id')
        dateval = parse_date(pick(r,'event_date','date','fight_date')) or events.get(ev.lower(),'')
        if not dateval:
            continue  # Never use undated fights for a chronological forecast.
        if dateval > NOW.date().isoformat():
            continue
        method = pick(r,'method','finish','win_method','method_of_victory')
        weight = pick(r,'weight_class','weightclass','division')
        k = (dateval, min(a.lower(),b.lower()), max(a.lower(),b.lower()))
        results[k] = (a,b,win,dateval,method,weight,ev)
    return list(v for k,v in sorted(results.items()))


def normalize_to_csv(items):
    sio = io.StringIO(newline='')
    out = csv.writer(sio)
    out.writerow(('r_fighter','b_fighter','winner','event_date','method','weight_class','event_name'))
    out.writerows(items)
    return sio.getvalue()


def latest_nfl(sources):
    maxkey = None
    total = 0
    for raw in sources:
        for r in csv_rows(raw):
            try:
                key = (int(pick(r,'season')), int(pick(r,'week')))
                if not 2018 <= key[0] <= NOW.year + 1 or not 1 <= key[1] <= 22:
                    continue
                total += 1
                if maxkey is None or key > maxkey:
                    maxkey = key
            except ValueError:
                continue
    return {'latest_season': maxkey[0] if maxkey else None,'latest_week': maxkey[1] if maxkey else None,'player_week_rows': total}


def build_bundle(loader=load_source):
    issues = []
    sources_meta = {}
    data = {'generated': NOW.isoformat(timespec='seconds'), 'nfl': [], 'games': '', 'ufc': '', 'ufcEvents': '', 'issues': issues,'sources': sources_meta, 'health': {}}
    for season in range(2020,NOW.year+1):
        raw = loader(f'nfl_{season}', f'https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{season}.csv','nfl',issues,sources_meta)
        if raw:
            data['nfl'].append({'year':season,'csv':raw})
    data['games'] = loader('nfl_games','https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv','games',issues,sources_meta)
    ufc_feeds = [
        ('greco', 'https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/ufc_fight_results.csv','https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/ufc_event_details.csv'),
        ('pavan', 'https://raw.githubusercontent.com/larissapavan/ufc-historical-fight-dataset/main/fights.csv','https://raw.githubusercontent.com/larissapavan/ufc-historical-fight-dataset/main/events.csv'),
    ]
    candidate_results = []
    for label, fight_url, event_url in ufc_feeds:
        fights = loader(label+'_fights',fight_url,'ufc',issues,sources_meta)
        events = loader(label+'_events',event_url,'events',issues,sources_meta)
        if fights and events:
            try:
                normalized = normalize_ufc(fights,events)
                if len(normalized) >= 100:
                    candidate_results.append((max(x[3] for x in normalized),len(normalized),label,normalized))
                else:
                    issues.append(f'{label} UFC source yielded only {len(normalized)} valid dated decisive fights; ignored')
            except Exception as exc:
                issues.append(f'{label} UFC normalization failed: {str(exc)[:120]}')
    if candidate_results:
        last, n, origin, records = max(candidate_results, key=lambda x: (x[0],x[1]))
        data['ufc'] = normalize_to_csv(records)
        data['health']['ufc_latest_date'] = last
        data['health']['ufc_rows'] = n
        data['health']['ufc_selected_source'] = origin
        stale_days = (NOW.date()-date.fromisoformat(last)).days
        if stale_days > 21:
            issues.append(f'UFC historical results are {stale_days} days old; do not assume recent events included')
    else:
        issues.append('No usable dated UFC dataset: UFC analysis unavailable')
    data['health'].update(latest_nfl([x['csv'] for x in data['nfl']]))
    h=hashlib.sha256()
    for item in data['nfl']:
        h.update(item['csv'].encode())
    h.update(data['games'].encode())
    h.update(data['ufc'].encode())
    data['versionId'] = h.hexdigest()[:20]
    if not data['nfl']:
        issues.append('No validated NFL player stats: NFL prop forecasts unavailable')
    return data


def write_bundle(data, out=OUT):
    out.parent.mkdir(parents=True, exist_ok=True)
    # Compact JSON prevents arbitrary upstream CSV content from executing as JavaScript.
    text = '/* Automated Edge Finder data snapshot. Untrusted feeds serialized as JSON. */\nwindow.EDGE_AUTOFEED='+json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</','<\\/')+';\n'
    p = out.with_suffix('.part')
    p.write_text(text, encoding='utf-8')
    p.replace(out)
    return len(text)


if __name__ == '__main__':
    start=time.monotonic()
    data=build_bundle()
    size=write_bundle(data)
    print(json.dumps({'data_generated_utc':data['generated'],'nfl_years':[x['year'] for x in data['nfl']],'nfl_latest':data['health']['latest_season'],'nfl_week':data['health']['latest_week'],'ufc_rows':data['health'].get('ufc_rows',0),'ufc_latest':data['health'].get('ufc_latest_date'), 'warnings': data['issues'], 'js_bytes':size,'runtime_s':round(time.monotonic()-start,1)},indent=2))

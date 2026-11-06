#!/usr/bin/env python3
"""Fail CI when a tutorial's structure, sources, or assets would mislead readers."""
from __future__ import annotations
import csv
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / 'content'
PROJECTS = json.loads((ROOT / 'data/projects.json').read_text(encoding='utf8'))
ALLOWED = {'planning', 'preparing', 'building', 'verified', 'completed-unwritten', 'archived'}
BLOCKER_STATUSES = {'open', 'asked', 'closed'}
SOURCE_STATUSES = {'active', 'superseded'}
SOURCE_STALE_DAYS = 90
DOWNLOAD_FILES = {'-bom.csv': 'bom.csv', '-blockers.csv': 'blockers.csv', '-sources.csv': 'sources.csv'}
errors: list[str] = []
warnings: list[str] = []


def parse_date(text: str) -> date | None:
    try:
        return datetime.strptime(str(text).strip(), '%Y-%m-%d').date()
    except ValueError:
        return None


def error(message: str):
    errors.append(message)


def path_for_site_url(path: str) -> Path | None:
    path = path.split('#', 1)[0].split('?', 1)[0]
    if not path.startswith('/') or path == '/':
        return CONTENT / 'index.md'
    if path.startswith('/downloads/'):
        item = path[len('/downloads/'):]
        for suffix, filename in DOWNLOAD_FILES.items():
            if item.endswith(suffix):
                return ROOT / 'source-data' / item.removesuffix(suffix) / filename
        error(f'Unknown downloadable resource: {path}')
        return None
    if path.startswith('/media/'):
        return ROOT / 'public' / path.lstrip('/')
    if path.startswith('/assets/'):
        return ROOT / path.lstrip('/')
    inner = path.strip('/')
    if path.endswith('/'):
        target_index = CONTENT / inner / 'index.md'
        return target_index if target_index.exists() else CONTENT / (inner + '.md')
    return CONTENT / (inner + '.md')


def validate():
    slugs = set()
    for project in PROJECTS:
        slug = project.get('slug', '')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
            error('Invalid project slug: ' + slug)
        if slug in slugs:
            error('Duplicate project slug: ' + slug)
        slugs.add(slug)
        if project.get('status') not in ALLOWED:
            error(f'Unknown project state for {slug}')
        for field in ('title', 'subtitle', 'category', 'description', 'date', 'budget', 'steps'):
            if field not in project:
                error(f'{slug}: missing field {field}')
        index = CONTENT / 'projects' / slug / 'index.md'
        if not index.is_file():
            error(f'{slug}: missing project index {index}')
        ids = set()
        for st in project.get('steps', []):
            id_ = st.get('id')
            if not id_ or id_ in ids:
                error(f'{slug}: missing or duplicate step id: {id_}')
            ids.add(id_)
            file = st.get('file', '')
            if not re.fullmatch(r'[\w-]+\.md', file, re.ASCII):
                error(f'{slug}: unsafe step filename {file}')
                continue
            stepfile = index.parent / file
            if not stepfile.exists():
                error(f'{slug}: missing step file {stepfile}')
                continue
            txt = stepfile.read_text(encoding='utf-8')
            for h in ('## 目标', '## 验收', '## 出问题怎么办'):
                if h not in txt:
                    error(f'{stepfile.relative_to(ROOT)}: missing required heading {h}')
            if not re.search(r'^- \[ \]', txt, re.M):
                error(f'{stepfile.relative_to(ROOT)}: no checkable acceptance checklist')
        if project.get('status') == 'verified':
            evidence = CONTENT / 'projects' / slug / 'evidence.md'
            if not evidence.is_file():
                error(f'{slug}: verified status requires evidence.md with real test records')
        if slug == 'hachimodock' and not (ROOT / 'source-data/hachimodock/bom.csv').exists():
            error('HachimoDock: missing BOM CSV')
    for doc in CONTENT.rglob('*.md'):
        txt = doc.read_text(encoding='utf-8')
        if not re.search(r'^#\s+.+$', txt, re.M):
            error(f'{doc.relative_to(ROOT)}: no H1')
        for match in re.finditer(r'\]\((/[^)]+)\)', txt):
            target = path_for_site_url(match.group(1))
            if target and not target.exists():
                error(f'{doc.relative_to(ROOT)}: broken internal link {match.group(1)} -> {target}')
        for match in re.finditer(r'\]\(([^)#:]+\.md)\)', txt):
            error(f'{doc.relative_to(ROOT)}: relative markdown link {match.group(1)}; use an absolute site path like /projects/<slug>/<page>/')
        if re.search(r'(?:sk-[a-zA-Z0-9]{18,}|ghp_[a-zA-Z0-9]{20,})', txt):
            error(f'{doc.relative_to(ROOT)}: possible exposed secret')
    for table in (ROOT / 'source-data').glob('*/bom.csv'):
        with table.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        required = {'id', '类别', '材料', '型号或规格', '数量', '采购状态', '采购链接或来源'}
        if not rows or not required.issubset(rows[0]):
            error(f'{table.relative_to(ROOT)}: BOM is empty or missing columns')
        for r in rows:
            if r.get('采购状态') not in {'HOLD', 'CHECK', 'ORDERED', 'RECEIVED', 'VERIFIED'}:
                error(f'{table.relative_to(ROOT)} row {r.get("id")}: invalid status')
            if not str(r.get('数量', '')).isdigit():
                error(f'{table.relative_to(ROOT)} row {r.get("id")}: non-integer quantity')
    project_status = {p.get('slug'): p.get('status') for p in PROJECTS}
    blockers_by_slug: dict[str, list[dict]] = {}
    for table in sorted((ROOT / 'source-data').glob('*/blockers.csv')):
        slug = table.parent.name
        with table.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        required = {'id', '疑点', '影响', '关闭所需证据', '证据来源', '状态', '核验日期', '结论'}
        if not rows or not required.issubset(rows[0]):
            error(f'{table.relative_to(ROOT)}: blockers register is empty or missing columns')
            continue
        blockers_by_slug[slug] = rows
        for r in rows:
            status = r.get('状态')
            if status not in BLOCKER_STATUSES:
                error(f'{table.relative_to(ROOT)} row {r.get("id")}: invalid blocker status')
                continue
            if status == 'closed':
                if not r.get('证据来源') or not parse_date(r.get('核验日期', '')):
                    error(f'{table.relative_to(ROOT)} row {r.get("id")}: closed blocker needs evidence source and YYYY-MM-DD date')
            else:
                if r.get('结论'):
                    error(f'{table.relative_to(ROOT)} row {r.get("id")}: unresolved blocker must not record a conclusion')
                checked = parse_date(r.get('核验日期', ''))
                if checked and (date.today() - checked).days > SOURCE_STALE_DAYS:
                    warnings.append(f'{table.relative_to(ROOT)} row {r.get("id")}: unresolved for {(date.today() - checked).days} days; follow up with the seller/author')
    for table in sorted((ROOT / 'source-data').glob('*/sources.csv')):
        with table.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        required = {'id', '名称', '类型', '网址', '版本或标识', '查看日期', '用途', '状态'}
        if not rows or not required.issubset(rows[0]):
            error(f'{table.relative_to(ROOT)}: source register is empty or missing columns')
            continue
        for r in rows:
            if r.get('状态') not in SOURCE_STATUSES:
                error(f'{table.relative_to(ROOT)} row {r.get("id")}: invalid source status')
            if not str(r.get('网址', '')).startswith('https://'):
                error(f'{table.relative_to(ROOT)} row {r.get("id")}: source URL must be https')
            checked = parse_date(r.get('查看日期', ''))
            if checked is None:
                error(f'{table.relative_to(ROOT)} row {r.get("id")}: 查看日期 must be YYYY-MM-DD')
            elif (date.today() - checked).days > SOURCE_STALE_DAYS:
                warnings.append(f'{table.relative_to(ROOT)} row {r.get("id")}: checked {(date.today() - checked).days} days ago; re-verify version drift')
    for slug, status in project_status.items():
        if status == 'verified' and slug in blockers_by_slug:
            open_ids = [r.get('id') for r in blockers_by_slug[slug] if r.get('状态') != 'closed']
            if open_ids:
                error(f'{slug}: verified status requires all blockers closed; still open: {", ".join(open_ids)}')
    if 'hachimodock' in project_status and 'hachimodock' not in blockers_by_slug:
        error('HachimoDock: missing blockers.csv doubt register')
    videos_file = ROOT / 'data/videos.json'
    if videos_file.exists():
        for v in json.loads(videos_file.read_text(encoding='utf-8')):
            if v.get('project') not in slugs:
                error('Video points to unknown project')
            if v.get('status') not in {'planned','published'}:
                error('Invalid video status')
            if v.get('status') == 'published' and not v.get('video_url','').startswith('https://'):
                error('Published video missing secure https URL')
            if v.get('embed') not in {'', 'bilibili'}:
                error('Unsupported video embed provider')
    for media in (ROOT / 'public/media').rglob('*'):
        if media.is_file() and media.suffix.lower() in {'.mp4', '.mov', '.mkv'}:
            error(f'{media.relative_to(ROOT)}: original videos should be hosted outside Git')
        if media.is_file() and media.suffix.lower() in {'.png', '.jpeg', '.jpg', '.webp', '.gif'} and media.stat().st_size > 3 * 1024 * 1024:
            error(f'{media.relative_to(ROOT)}: image exceeds 3 MiB; optimize before upload')
    if errors:
        print(f'CONTENT VALIDATION FAILED ({len(errors)} errors):')
        for e in errors:
            print('  -', e)
        return 1
    print(f'Content validation passed: {len(PROJECTS)} projects, {len(list(CONTENT.rglob("*.md")))} pages, BOM/blockers/sources CSV OK.')
    if warnings:
        print(f'{len(warnings)} warning(s) (not failing):')
        for w in warnings:
            print('  -', w)
    return 0

if __name__ == '__main__':
    sys.exit(validate())

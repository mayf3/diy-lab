#!/usr/bin/env python3
"""Check every generated internal HTML/CSS/JS/download link resolves to a real file."""
from __future__ import annotations
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent / 'dist'

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        for field in ('href','src'):
            if field in d and tag in ('a','script','img','link','iframe'):
                self.refs.append((tag,d[field]))


def main():
    if not (ROOT/'index.html').is_file():
        print('Missing dist/index.html; run build.py first')
        return 1
    broken=[]
    count=0
    for page in ROOT.rglob('*.html'):
        parser=LinkParser()
        parser.feed(page.read_text(encoding='utf-8'))
        for tag,link in parser.refs:
            path=urlsplit(link)
            if path.scheme in ('https','http','mailto','data','tel','javascript') or link.startswith('#') or link.startswith('//'):
                continue
            if path.scheme:
                broken.append(f'{page.relative_to(ROOT)}: unsupported URL {link}')
                continue
            relative=unquote(path.path)
            if not relative:
                continue
            target=(ROOT/relative.lstrip('/')) if relative.startswith('/') else (page.parent/relative)
            if not target.exists():
                broken.append(f'{page.relative_to(ROOT)} -> {link}')
            count+=1
    if broken:
        print('Broken links:', *broken,sep='\n - ')
        return 1
    print(f'Generated site links passed: {len(list(ROOT.rglob("*.html")))} HTML pages, {count} local references.')
    return 0

if __name__=='__main__':
    sys.exit(main())

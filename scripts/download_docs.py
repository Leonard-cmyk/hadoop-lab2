#!/usr/bin/env python3
"""Download ten public English pages; extract only the main body, not navigation."""
import hashlib
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

PAGES = [
    ('introduction', 'An Informal Introduction to Python'),
    ('controlflow', 'More Control Flow Tools'),
    ('datastructures', 'Data Structures'),
    ('modules', 'Modules'),
    ('inputoutput', 'Input and Output'),
    ('errors', 'Errors and Exceptions'),
    ('classes', 'Classes'),
    ('stdlib', 'Brief Tour of the Standard Library'),
    ('stdlib2', 'Brief Tour of the Standard Library Part II'),
    ('venv', 'Virtual Environments and Packages'),
]

class MainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div':
            if self.depth: self.depth += 1
            elif 'body' in attrs.get('class', '').split(): self.depth = 1
        if self.depth and tag in ('p', 'li', 'pre', 'h1', 'h2', 'h3', 'br'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if self.depth and tag == 'div': self.depth -= 1
        if self.depth and tag in ('p', 'li', 'pre', 'h1', 'h2', 'h3'): self.parts.append('\n')
    def handle_data(self, data):
        if self.depth: self.parts.append(data)

def main():
    root = Path(__file__).resolve().parents[1] / 'data'
    (root / 'input').mkdir(parents=True, exist_ok=True)
    (root / 'raw').mkdir(exist_ok=True)
    manifest = []
    for i, (slug, title) in enumerate(PAGES, 1):
        url = f'https://docs.python.org/3.11/tutorial/{slug}.html'
        request = Request(url, headers={'User-Agent': 'HadoopLab2Educational/1.0'})
        with urlopen(request, timeout=60) as response:
            raw = response.read()
        parser = MainText(); parser.feed(raw.decode('utf-8'))
        text = '\n'.join(' '.join(line.split()) for line in ''.join(parser.parts).splitlines() if line.strip()) + '\n'
        if len(text) < 1000: raise RuntimeError(f'Extraction too short: {url}')
        name = f'document{i:02d}.txt'
        (root / 'input' / name).write_text(text, encoding='utf-8')
        (root / 'raw' / (slug + '.html')).write_bytes(raw)
        item = dict(document=name, title=title, url=url, bytes=len(text.encode('utf-8')),
                    sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    downloaded_utc=datetime.now(timezone.utc).isoformat())
        manifest.append(item)
        print(name, item['bytes'], url, flush=True)
    (root / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Downloaded and extracted 10 documents.')

if __name__ == '__main__': main()

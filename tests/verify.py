#!/usr/bin/env python3
"""Independent serial reference: compare every posting and every total."""
import collections
import json
import re
import sys
from pathlib import Path

def verify(inputs, output, stopfile):
    stop = set(Path(stopfile).read_text().split())
    expected = collections.defaultdict(collections.Counter)
    raw = kept = 0
    documents = sorted(Path(inputs).glob('*.txt'))
    assert documents, 'No input documents'
    for doc in documents:
        words = re.findall(r'[a-z]+', doc.read_text(encoding='utf-8').lower())
        raw += len(words)
        for word in words:
            if word not in stop:
                expected[word][doc.name] += 1
                kept += 1
    actual = {}
    previous = ''
    for line in Path(output).read_text(encoding='utf-8').splitlines():
        word, postings = line.split('\t', 1)
        assert word > previous, f'Unsorted or duplicate word: {word}'
        previous = word
        assert word not in stop
        assert re.fullmatch(r'(?:<[A-Za-z0-9_.-]+,[1-9][0-9]*>;)+<total,[1-9][0-9]*>\.', postings), line
        entries = re.findall(r'<([^,<>]+),(\d+)>', postings)
        total = int(entries[-1][1])
        pairs = entries[:-1]
        assert [x[0] for x in pairs] == sorted(set(x[0] for x in pairs))
        counts = {name: int(value) for name, value in pairs}
        assert total == sum(counts.values())
        actual[word] = counts
    assert actual == dict(expected), 'Index differs from independent reference'
    summary = dict(passed=True, documents=len(documents), raw_tokens=raw,
                   stop_tokens=raw-kept, kept_tokens=kept, unique_words=len(actual),
                   postings=sum(len(x) for x in actual.values()), stopwords=len(stop))
    print(json.dumps(summary, indent=2))
    return summary

if __name__ == '__main__':
    if len(sys.argv) != 4: raise SystemExit('Usage: verify.py INPUT_DIR RESULT STOPWORDS')
    verify(*sys.argv[1:])

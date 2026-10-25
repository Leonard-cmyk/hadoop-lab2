#!/usr/bin/env python3
"""Real YARN jobs for edge cases, with/without combiner and small input splits."""
import json
import os
from pathlib import Path
import subprocess
import time
from verify import verify

root = Path(__file__).resolve().parents[1]
os.chdir(root)
folder = root / 'results' / ('edge-' + str(time.time_ns()))
inputs = folder / 'input'; inputs.mkdir(parents=True)
cases = {
    'document01.txt': 'Data data, DATA! Hadoop and the index.\nSearch search; data.\n',
    'document02.txt': 'hadoop search index index\nData 123; INDEX; Python-python.\n',
    'document03.txt': '',
    'document04.txt': 'a an the AND or is are\n',
    'document05.txt': "Can't data_data. MapReduce MAPREDUCE\n",
    'document06.txt': ('Repeated data\n' * 100),
}
for name, content in cases.items(): (inputs/name).write_text(content, encoding='utf-8')
base = '/user/' + os.environ['USER'] + '/lab2/' + folder.name
def run(*args, **kw):
    return subprocess.run(args, check=True, text=True, **kw)
run('hdfs','dfs','-mkdir','-p',base+'/input',base+'/config')
run('hdfs','dfs','-put',*[str(p) for p in sorted(inputs.glob('*.txt'))],base+'/input/')
run('hdfs','dfs','-put','stopwords.txt',base+'/config/')
fs = subprocess.check_output(['hdfs','getconf','-confKey','fs.defaultFS'],text=True).strip()
summaries=[]
for mode in ('combiner','no-combiner'):
    # Tiny input splits force repeated terms to cross mapper boundaries.
    command=['hadoop','jar','build/inverted-index.jar','InvertedIndex',base+'/input',base+'/'+mode,fs+base+'/config/stopwords.txt']
    if mode == 'no-combiner': command.append(mode)
    env = os.environ.copy()
    env['HADOOP_CLIENT_OPTS'] = env.get('HADOOP_CLIENT_OPTS','') + ' -Dlab2.test.maxSplit=128'
    with (folder/(mode+'.log')).open('w') as log:
        run(*command,stdout=log,stderr=subprocess.STDOUT,env=env)
    run('hdfs','dfs','-test','-e',base+'/'+mode+'/_SUCCESS')
    output = folder/(mode+'.txt')
    output.write_text(subprocess.check_output(['hdfs','dfs','-cat',base+'/'+mode+'/part-r-*'],text=True))
    summaries.append(verify(inputs,output,'stopwords.txt'))
assert (folder/'combiner.txt').read_bytes() == (folder/'no-combiner.txt').read_bytes()
(folder/'summary.json').write_text(json.dumps(dict(passed=True, modes=2, cases=6, summaries=summaries),indent=2))
print('PASS: six edge-case documents; combiner and no-combiner outputs identical')
print(folder)

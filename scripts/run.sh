#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -f "$HOME/hadoop-lab/env.sh" ]]; then source "$HOME/hadoop-lab/env.sh"; fi
bash build.sh
[[ $(find data/input -maxdepth 1 -name '*.txt' | wc -l) -ge 10 ]] || { echo 'Download at least 10 documents first'; exit 1; }
RUN="$(date -u +%Y%m%dT%H%M%SZ)-$$"
BASE="/user/$(id -un)/lab2/$RUN"
mkdir -p "results/$RUN"
RESULT="results/$RUN"
printf '%s\n' "$RUN" > results/latest.txt
hdfs dfs -mkdir -p "$BASE/input" "$BASE/config"
hdfs dfs -put data/input/*.txt "$BASE/input/"
hdfs dfs -put stopwords.txt "$BASE/config/stopwords.txt"
STOP_URI="$(hdfs getconf -confKey fs.defaultFS)$BASE/config/stopwords.txt"
printf 'HDFS base: %s\nStopwords: %s\n' "$BASE" "$STOP_URI"
hdfs dfs -ls "$BASE/input"
hadoop jar build/inverted-index.jar InvertedIndex "$BASE/input" "$BASE/output" "$STOP_URI" 2>&1 | tee "$RESULT/job.log"
hdfs dfs -test -e "$BASE/output/_SUCCESS"
hdfs dfs -cat "$BASE/output/part-r-*" > "$RESULT/index.txt"
python3 tests/verify.py data/input "$RESULT/index.txt" stopwords.txt | tee "$RESULT/summary.json"
printf '%s\n' "$BASE" > "$RESULT/hdfs-base.txt"
echo "PASS: full corpus; output in $RESULT"

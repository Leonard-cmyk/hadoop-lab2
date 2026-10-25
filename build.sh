#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -f "$HOME/hadoop-lab/env.sh" ]]; then source "$HOME/hadoop-lab/env.sh"; fi
mkdir -p build/classes
# Ignore macOS AppleDouble metadata, which is not a valid JAR.
CP=$(find "${HADOOP_HOME:?Set HADOOP_HOME}/share/hadoop" -name '*.jar' ! -name '._*' -type f | paste -sd: -)
javac -encoding UTF-8 -cp "$CP" -d build/classes src/InvertedIndex.java
jar cf build/inverted-index.jar -C build/classes .
echo 'Built build/inverted-index.jar'

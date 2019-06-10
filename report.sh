#!/bin/bash -x
# show time reports for a specific tag
# ./report.sh '\(content\|delta\)'
tag="$1"
dir="${2:-./logs}/*.yml"
grep -h -e "'20..-..-..'" -e ".*$tag.*: .*" $dir

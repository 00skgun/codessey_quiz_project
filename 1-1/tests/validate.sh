#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mkdir -p "$project/evidence"
{
    date --iso-8601=seconds
    uname -a
    for script in "$project"/*.sh "$project"/tests/*.sh; do
        bash -n "$script"
        printf '[SYNTAX OK] %s\n' "${script#"$project/"}"
    done
    bash "$project/tests/run-tests.sh"
} | tee "$project/evidence/tests.txt"

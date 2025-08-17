#!/bin/bash
set -e
# Convenience wrapper requested by user to invoke tests
DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$DIR/.." && pwd)"
cd "$PROJECT_ROOT"
"$DIR/run_tests.sh" backend

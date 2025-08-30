#!/usr/bin/env bash

# change dir to parent dir of this script's location
cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

# run unittests
uv run pytest test/*

# exit success
exit 0

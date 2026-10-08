#!/usr/bin/env bash
# Laptop: let a USB phone reach the laptop's :4010 (Prism mock) and :8001 (tunnelled dev API) as localhost.
set -euo pipefail
adb reverse tcp:4010 tcp:4010
adb reverse tcp:8001 tcp:8001
adb reverse --list

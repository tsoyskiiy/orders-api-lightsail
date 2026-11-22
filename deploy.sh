#!/usr/bin/env bash
# Бонус: повторное развёртывание одной командой (запускать на сервере, в папке проекта)
set -euo pipefail
cd "$(dirname "$0")"
git pull
docker compose up -d --build
docker compose ps

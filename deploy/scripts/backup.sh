#!/usr/bin/env bash
# Nightly backup of the hosted database. Install with `crontab -e`:
# 15 2 * * * /opt/kharcha/deploy/scripts/backup.sh >> /home/ubuntu/backups/backup.log 2>&1
set -euo pipefail
mkdir -p ~/backups
docker exec kharcha-postgres-1 pg_dump -U kharcha kharcha \
  | gzip > ~/backups/"kharcha_$(date +%F).sql.gz"
find ~/backups -name 'kharcha_*.sql.gz' -mtime +7 -delete

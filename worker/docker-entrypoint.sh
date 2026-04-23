#!/bin/sh
set -eu

export DB_NAME="$(cat /run/secrets/db_name)"
export DB_USER="$(cat /run/secrets/db_user)"
export DB_PASSWORD="$(cat /run/secrets/db_password)"
export API_KEY="$(cat /run/secrets/api_key)"
export API_SECRET="$(cat /run/secrets/api_secret)"

exec python -m worker

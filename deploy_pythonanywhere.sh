#!/usr/bin/env bash
# Set this project up on PythonAnywhere. Run it *there*, in a Bash console:
#
#     bash ~/velingo/deploy_pythonanywhere.sh
#
# It is the half of the deployment that needs a shell. The other half -- uploading the
# files, creating the web app, its static file mappings and the WSGI file -- is done from
# your own machine through PythonAnywhere's API, because their API has no endpoint for
# "run this command on the server".
#
# Safe to run again after pulling new code: an existing virtualenv is reused, pip only
# installs what changed, collectstatic overwrites what it owns and migrate skips
# migrations that are already applied. Nothing here deletes data.
#
# Media (/media/) on this host is served by Django, not by PythonAnywhere's static file
# server: that server ignores the Range header, so audio would play but could never be
# seeked inside. .env sets DJANGO_SERVE_MEDIA=True for that reason, and there is
# deliberately **no** /media/ static file mapping on the web app. /static/ still is mapped,
# and should stay mapped -- it is the traffic that matters.
#
# Two things in this project are decided by environment variables rather than by files on
# this host, so they are set here:
#
#   DJANGO_SETTINGS_MODULE   manage.py defaults to config.settings_mirror, which is a
#                            local-only file (it is not in version control) and does not
#                            exist here. config.settings is the real project.
#   DB_ENGINE / DB_NAME      the database is the SQLite file db.sqlite3 next to manage.py,
#                            in .env. See config/settings.py for both.
#
# Python 3.12 is chosen on purpose: it is the version this project is developed and tested
# against, so the deployment runs the same interpreter as the machine the tests pass on.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

PYTHON=/usr/bin/python3.12
VENV="$HOME/.virtualenvs/velingo"

export DJANGO_SETTINGS_MODULE=config.settings

if [ ! -f .env ]; then
  echo "No .env here, so Django cannot read its SECRET_KEY or its database." >&2
  echo "Upload it first: it is written by the deploying machine." >&2
  exit 1
fi

if [ -x "$VENV/bin/python" ]; then
  echo "Virtualenv already exists: $VENV"
else
  echo "Creating $VENV with $PYTHON ..."
  "$PYTHON" -m venv "$VENV"
fi

echo "Installing requirements.txt ..."
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r requirements.txt

echo "Applying migrations to the SQLite database ..."
"$VENV/bin/python" manage.py migrate --noinput

echo "Collecting static files into staticfiles/ ..."
"$VENV/bin/python" manage.py collectstatic --noinput

echo "Checking the project ..."
"$VENV/bin/python" manage.py check

echo
echo "Done. Reload the web app to pick this up."

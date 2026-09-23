#!/usr/bin/env bash

set -euo pipefail


PREFIX="/opt/atlas"
VENV="$PREFIX/venv"

CONFIG_DIR="/etc/atlas"
ATLAS_ENV="$CONFIG_DIR/atlas.env"
ATLAS_WEB_ENV="$CONFIG_DIR/atlas-web.env"

STATE_DIR="/var/lib/atlas"
BACKUP_ROOT="/var/backups/atlas"

SYSTEMD_DIR="/etc/systemd/system"

COLLECTOR_UNIT="$SYSTEMD_DIR/atlas-collector.service"
WEB_UNIT="$SYSTEMD_DIR/atlas-web.service"

COLLECTOR_DROPIN_DIR="$SYSTEMD_DIR/atlas-collector.service.d"
COLLECTOR_DROPIN="$COLLECTOR_DROPIN_DIR/boot-hardening.conf"

WAIT_DST="/usr/local/sbin/atlas-wait-ready"


SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" \
    && pwd
)"

BUNDLE_ROOT="$(
    cd "$SCRIPT_DIR/.." \
    && pwd
)"


COLLECTOR_SRC="$BUNDLE_ROOT/ops/systemd/atlas-collector.service"
WEB_SRC="$BUNDLE_ROOT/ops/systemd/atlas-web.service"

DROPIN_SRC="$BUNDLE_ROOT/ops/systemd/atlas-collector.service.d/boot-hardening.conf"
WAIT_SRC="$BUNDLE_ROOT/ops/bin/atlas-wait-ready"


WHEEL=""
START_SERVICES=1


usage() {

    cat <<'USAGE'
ATLAS OS v1 installer

Usage:
  scripts/install-atlas.sh --wheel /path/to/atlasctl-VERSION.whl
  scripts/install-atlas.sh --wheel /path/to/atlasctl-VERSION.whl --no-start

Options:

  --wheel PATH
      Install ATLAS from this wheel.

  --no-start
      Install and enable systemd units, but do not start/restart them.

The installer requires:
  - root
  - Debian/systemd-style Linux
  - Python 3.13+
  - python3 venv support

Runtime layout:

  /opt/atlas/venv
      Python runtime and installed ATLAS wheel.

  /etc/atlas
      Runtime configuration and secrets.

  /var/lib/atlas
      Persistent ATLAS state.

  /var/backups/atlas
      Installer and operational backups.

No Git checkout is required after installation.
USAGE
}


fail() {

    echo "ERROR: $*" >&2
    exit 1
}


while [ "$#" -gt 0 ]; do

    case "$1" in

        --wheel)

            shift

            [ "$#" -gt 0 ] \
                || fail "--wheel requires a path"

            WHEEL="$1"
            ;;

        --no-start)

            START_SERVICES=0
            ;;

        -h|--help)

            usage
            exit 0
            ;;

        *)

            fail "unknown argument: $1"
            ;;

    esac

    shift
done


[ "${EUID}" -eq 0 ] \
    || fail "installer must run as root"

[ -n "$WHEEL" ] \
    || fail "--wheel is required"

[ -f "$WHEEL" ] \
    || fail "wheel not found: $WHEEL"


case "$WHEEL" in
    *.whl)
        ;;
    *)
        fail "--wheel must reference a .whl file"
        ;;
esac


for command in \
    python3 \
    systemctl \
    systemd-analyze \
    install \
    sha256sum
do

    command -v "$command" \
        >/dev/null 2>&1 \
        || fail "required command not found: $command"

done


python3 - <<'PY'
import sys

required = (
    3,
    13,
)

if sys.version_info < required:
    raise SystemExit(
        "ATLAS requires Python 3.13+; "
        f"found {sys.version.split()[0]}"
    )

print(
    "Python:",
    sys.version.split()[0],
)
PY


# Never overwrite a source/development installation.
#
# The public installer owns /opt/atlas as a wheel runtime,
# not as a Git working tree.
if [ -e "$PREFIX/.git" ]; then

    fail "/opt/atlas contains a source checkout; public installer refuses to overwrite it"

fi


for asset in \
    "$COLLECTOR_SRC" \
    "$WEB_SRC" \
    "$DROPIN_SRC" \
    "$WAIT_SRC"
do

    [ -f "$asset" ] \
        || fail "release bundle asset missing: $asset"

done


STAMP="$(
    date +%Y%m%d_%H%M%S
)"

BACKUP_DIR="$BACKUP_ROOT/install.$STAMP"


install \
    -d \
    -o root \
    -g root \
    -m 0755 \
    "$PREFIX"

install \
    -d \
    -o root \
    -g root \
    -m 0700 \
    "$CONFIG_DIR"

install \
    -d \
    -o root \
    -g root \
    -m 0700 \
    "$STATE_DIR"

install \
    -d \
    -o root \
    -g root \
    -m 0700 \
    "$BACKUP_ROOT"

install \
    -d \
    -o root \
    -g root \
    -m 0700 \
    "$BACKUP_DIR"


backup_if_present() {

    source_path="$1"
    name="$2"

    if [ -e "$source_path" ]; then

        cp -a \
            "$source_path" \
            "$BACKUP_DIR/$name"

    fi
}


backup_if_present \
    "$ATLAS_ENV" \
    atlas.env

backup_if_present \
    "$ATLAS_WEB_ENV" \
    atlas-web.env

backup_if_present \
    "$COLLECTOR_UNIT" \
    atlas-collector.service

backup_if_present \
    "$WEB_UNIT" \
    atlas-web.service

backup_if_present \
    "$COLLECTOR_DROPIN" \
    boot-hardening.conf

backup_if_present \
    "$WAIT_DST" \
    atlas-wait-ready


if [ ! -f "$ATLAS_ENV" ]; then

    cat > "$ATLAS_ENV" <<'ENV'
ATLAS_DB_PATH=/var/lib/atlas/atlas.db
ATLAS_WEB_HOST=127.0.0.1
ATLAS_WEB_PORT=8091
ENV

fi


# Existing installations keep their administrator-selected values.
# Only missing baseline keys are added.
python3 - "$ATLAS_ENV" <<'PY'
from pathlib import Path
import os
import sys


path = Path(
    sys.argv[1]
)

defaults = {
    "ATLAS_DB_PATH":
        "/var/lib/atlas/atlas.db",

    "ATLAS_WEB_HOST":
        "127.0.0.1",

    "ATLAS_WEB_PORT":
        "8091",
}


lines = path.read_text(
    encoding="utf-8"
).splitlines()

configured = set()


for raw in lines:

    line = raw.strip()

    if (
        not line
        or line.startswith("#")
        or "=" not in line
    ):
        continue

    configured.add(
        line.split(
            "=",
            1,
        )[0].strip()
    )


missing = [
    (
        key,
        value,
    )
    for key, value in defaults.items()
    if key not in configured
]


if missing:

    if (
        lines
        and lines[-1] != ""
    ):
        lines.append(
            ""
        )

    lines.append(
        "# ATLAS installer baseline"
    )

    for key, value in missing:

        lines.append(
            f"{key}={value}"
        )


temporary = path.with_name(
    path.name
    + ".tmp"
)

temporary.write_text(
    "\n".join(
        lines
    )
    + "\n",
    encoding="utf-8",
)

os.chmod(
    temporary,
    0o600,
)

os.replace(
    temporary,
    path,
)
PY


chmod \
    0600 \
    "$ATLAS_ENV"


if [ ! -f "$ATLAS_WEB_ENV" ]; then

    OPERATOR_TOKEN="$(
        python3 - <<'PY'
import secrets

print(
    secrets.token_urlsafe(
        48
    )
)
PY
    )"

    cat > "$ATLAS_WEB_ENV" <<ENV
ATLAS_OPERATOR_TOKEN=$OPERATOR_TOKEN
ATLAS_OPERATOR_SYSTEMD_SERVICES=
ATLAS_OPERATOR_QEMU_VMIDS=
ATLAS_OPERATOR_LXC_VMIDS=
ENV

    unset OPERATOR_TOKEN

fi


chmod \
    0600 \
    "$ATLAS_WEB_ENV"


if [ ! -x "$VENV/bin/python" ]; then

    if ! python3 -m venv "$VENV"; then

        fail "could not create Python venv; install the Debian python3-venv package"

    fi

fi


"$VENV/bin/python" \
    -m pip \
    install \
    --upgrade \
    "$WHEEL"


"$VENV/bin/python" \
    -m pip \
    check


install \
    -o root \
    -g root \
    -m 0755 \
    "$WAIT_SRC" \
    "$WAIT_DST"


install \
    -o root \
    -g root \
    -m 0644 \
    "$COLLECTOR_SRC" \
    "$COLLECTOR_UNIT"


install \
    -o root \
    -g root \
    -m 0644 \
    "$WEB_SRC" \
    "$WEB_UNIT"


install \
    -d \
    -o root \
    -g root \
    -m 0755 \
    "$COLLECTOR_DROPIN_DIR"


install \
    -o root \
    -g root \
    -m 0644 \
    "$DROPIN_SRC" \
    "$COLLECTOR_DROPIN"


read_env_value() {

    key="$1"
    file="$2"
    fallback="${3:-}"

    python3 - \
        "$key" \
        "$file" \
        "$fallback" \
        <<'PY'
from pathlib import Path
import sys


key = sys.argv[1]
path = Path(
    sys.argv[2]
)
fallback = sys.argv[3]


value = None


for raw in path.read_text(
    encoding="utf-8"
).splitlines():

    line = raw.strip()

    if (
        not line
        or line.startswith("#")
        or "=" not in line
    ):
        continue

    name, candidate = line.split(
        "=",
        1,
    )

    if name.strip() != key:
        continue

    value = (
        candidate
        .strip()
        .strip(
            "\"'"
        )
    )

    break


print(
    value
    if value is not None
    else fallback
)
PY
}


DB_PATH="$(
    read_env_value \
        ATLAS_DB_PATH \
        "$ATLAS_ENV" \
        /var/lib/atlas/atlas.db
)"


WEB_HOST="$(
    read_env_value \
        ATLAS_WEB_HOST \
        "$ATLAS_ENV" \
        127.0.0.1
)"


WEB_PORT="$(
    read_env_value \
        ATLAS_WEB_PORT \
        "$ATLAS_ENV" \
        8091
)"


[ -n "$DB_PATH" ] \
    || fail "ATLAS_DB_PATH is empty"

[ -n "$WEB_HOST" ] \
    || fail "ATLAS_WEB_HOST is empty"

[ -n "$WEB_PORT" ] \
    || fail "ATLAS_WEB_PORT is empty"


case "$DB_PATH" in

    /*)
        ;;

    *)
        fail "ATLAS_DB_PATH must be an absolute path"
        ;;

esac


if ! python3 - "$WEB_PORT" <<'PYPORT'
import sys


raw = sys.argv[1]


try:
    port = int(
        raw
    )

except ValueError:
    raise SystemExit(
        1
    )


if not (
    1
    <= port
    <= 65535
):
    raise SystemExit(
        1
    )
PYPORT
then

    fail "ATLAS_WEB_PORT must be an integer between 1 and 65535"

fi


# The service may bind to a wildcard address, but the installer
# must probe a concrete local destination.
HEALTH_HOST="$WEB_HOST"

case "$HEALTH_HOST" in

    0.0.0.0|::|"[::]")
        HEALTH_HOST="127.0.0.1"
        ;;

esac


ATLAS_DB_PATH="$DB_PATH" \
"$VENV/bin/python" - <<'PY'
import os
import sqlite3

from atlas.storage.database import (
    Database,
)


path = os.environ[
    "ATLAS_DB_PATH"
]


with Database(
    path
):
    pass


connection = sqlite3.connect(
    path
)

try:

    result = connection.execute(
        "PRAGMA quick_check;"
    ).fetchone()[0]

finally:

    connection.close()


if result != "ok":
    raise SystemExit(
        f"SQLite quick_check failed: {result}"
    )


print(
    "Database:",
    path,
)

print(
    "SQLite quick_check: ok"
)
PY


systemctl \
    daemon-reload


systemd-analyze \
    verify \
    "$COLLECTOR_UNIT" \
    "$WEB_UNIT"


systemctl \
    enable \
    atlas-collector.service \
    atlas-web.service


if [ "$START_SERVICES" -eq 1 ]; then

    systemctl restart \
        atlas-collector.service

    systemctl restart \
        atlas-web.service


    systemctl is-active \
        --quiet \
        atlas-collector.service \
        || fail "atlas-collector.service did not become active"


    READY=0

    for attempt in $(
        seq 1 30
    ); do

        if "$VENV/bin/python" - \
            "$HEALTH_HOST" \
            "$WEB_PORT" \
            <<'PY'
import sys
import urllib.request


host = str(
    sys.argv[1]
).strip()

port = int(
    sys.argv[2]
)


# urllib requires IPv6 literals to be bracketed.
if (
    ":" in host
    and not host.startswith(
        "["
    )
):

    host = (
        f"[{host}]"
    )


url = (
    f"http://{host}:"
    f"{port}/api/system/health"
)

try:

    with urllib.request.urlopen(
        url,
        timeout=1,
    ) as response:

        if response.status == 200:
            raise SystemExit(
                0
            )

except Exception:
    pass

raise SystemExit(
    1
)
PY
        then

            READY=1
            break

        fi

        sleep 0.5

    done


    [ "$READY" -eq 1 ] \
        || fail "ATLAS web health endpoint did not become ready"

    systemctl is-active \
        --quiet \
        atlas-web.service \
        || fail "atlas-web.service did not become active"

fi


echo
echo "ATLAS package:"
"$VENV/bin/atlasctl" \
    version


echo
echo "Installation layout:"
echo "  runtime : $VENV"
echo "  config  : $CONFIG_DIR"
echo "  state   : $STATE_DIR"
echo "  backups : $BACKUP_ROOT"

echo
echo "Operator:"
echo "  token   : <SET in $ATLAS_WEB_ENV>"
echo "  targets : fail-closed by default"

echo
echo "Backup created:"
echo "  $BACKUP_DIR"

if [ "$START_SERVICES" -eq 1 ]; then

    echo
    echo "Dashboard:"
    echo "  http://127.0.0.1:$WEB_PORT"

else

    echo
    echo "Services installed and enabled but not started."

fi

echo
echo "ATLAS installation: PASS"

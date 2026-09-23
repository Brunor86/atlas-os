#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" \
    && pwd
)"

REPO_ROOT="$(
    cd "$SCRIPT_DIR/.." \
    && pwd
)"

WAIT_SRC="$REPO_ROOT/ops/bin/atlas-wait-ready"
DROPIN_SRC="$REPO_ROOT/ops/systemd/atlas-collector.service.d/boot-hardening.conf"

WAIT_DST="/usr/local/sbin/atlas-wait-ready"
DROPIN_DIR="/etc/systemd/system/atlas-collector.service.d"
DROPIN_DST="$DROPIN_DIR/boot-hardening.conf"

EXPECTED_WAIT_SHA="ca46869196a9b0ec578cd911754d7d6a2b5f5f323e238472a314e588c9a1e9ca"
EXPECTED_DROPIN_SHA="df1763c9def4a8d601e88d7a77c07de40eb0080cd815e4f54f15638bfd0ee0e9"


usage() {

    cat <<'EOF'
Usage:
  scripts/install-boot-hardening.sh --check
  scripts/install-boot-hardening.sh --install

--check
    Validate repository assets and the currently installed boot contract.
    Does not modify the system.

--install
    Install the versioned boot-hardening assets, reload systemd, and verify
    the effective collector contract. Does not restart services or reboot.
EOF
}


sha256() {

    sha256sum "$1" \
      | awk '{print $1}'
}


verify_sources() {

    test -f "$WAIT_SRC"
    test -f "$DROPIN_SRC"

    test "$(
        sha256 "$WAIT_SRC"
    )" = "$EXPECTED_WAIT_SHA"

    test "$(
        sha256 "$DROPIN_SRC"
    )" = "$EXPECTED_DROPIN_SHA"

    python3 - "$WAIT_SRC" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])

compile(
    path.read_text(),
    str(path),
    "exec",
)

print("atlas-wait-ready syntax: PASS")
PY

    echo "Repository asset hashes: PASS"
}


verify_contract() {

    test -x "$WAIT_DST"
    test -f "$DROPIN_DST"

    cmp "$WAIT_SRC" "$WAIT_DST"
    cmp "$DROPIN_SRC" "$DROPIN_DST"

    AFTER="$(
        systemctl show \
          atlas-collector.service \
          -p After \
          --value
    )"

    WANTS="$(
        systemctl show \
          atlas-collector.service \
          -p Wants \
          --value
    )"

    EXEC_PRE="$(
        systemctl show \
          atlas-collector.service \
          -p ExecStartPre \
          --value
    )"

    TIMEOUT="$(
        systemctl show \
          atlas-collector.service \
          -p TimeoutStartUSec \
          --value
    )"

    printf '%s\n' "$AFTER" \
      | grep -qw network-online.target

    printf '%s\n' "$WANTS" \
      | grep -qw network-online.target

    if printf '%s\n' "$AFTER" \
      | grep -qw docker.service
    then
        echo "ERROR: docker.service must not be an After dependency"
        exit 1
    fi

    if printf '%s\n' "$WANTS" \
      | grep -qw docker.service
    then
        echo "ERROR: docker.service must not be a Wants dependency"
        exit 1
    fi

    printf '%s\n' "$EXEC_PRE" \
      | grep -q '/usr/local/sbin/atlas-wait-ready'

    test "$TIMEOUT" = "2min 30s"

    SYSTEMD_PAGER=cat \
      systemd-analyze verify \
      atlas-collector.service

    echo "Installed boot contract: PASS"
}


install_assets() {

    if [ "${EUID}" -ne 0 ]; then
        echo "ERROR: --install requires root"
        exit 1
    fi

    test -f \
      /etc/systemd/system/atlas-collector.service

    test -f \
      /etc/atlas/atlas.env

    STAMP="$(
        date +%Y%m%d_%H%M%S
    )"

    BACKUP_ROOT="${ATLAS_BACKUP_DIR:-/var/backups/atlas}"

    BACKUP_DIR="$BACKUP_ROOT/boot-hardening-install.$STAMP"

    mkdir -p \
      "$BACKUP_DIR"


    if [ -f "$WAIT_DST" ]; then

        cp -a \
          "$WAIT_DST" \
          "$BACKUP_DIR/atlas-wait-ready"

    fi


    if [ -f "$DROPIN_DST" ]; then

        cp -a \
          "$DROPIN_DST" \
          "$BACKUP_DIR/boot-hardening.conf"

    fi


    install \
      -o root \
      -g root \
      -m 0755 \
      "$WAIT_SRC" \
      "$WAIT_DST"

    install \
      -d \
      -o root \
      -g root \
      -m 0755 \
      "$DROPIN_DIR"

    install \
      -o root \
      -g root \
      -m 0644 \
      "$DROPIN_SRC" \
      "$DROPIN_DST"


    systemctl daemon-reload


    echo "Backup: $BACKUP_DIR"

    verify_contract

    "$WAIT_DST"

    echo
    echo "Boot hardening installation: PASS"
    echo "No service restart or reboot was performed."
}


case "${1:-}" in

    --check)

        verify_sources
        verify_contract
        ;;

    --install)

        verify_sources
        install_assets
        ;;

    *)

        usage
        exit 2
        ;;

esac

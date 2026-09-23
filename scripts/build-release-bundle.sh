#!/usr/bin/env bash

set -euo pipefail


SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" \
    && pwd
)"

ROOT="$(
    cd "$SCRIPT_DIR/.." \
    && pwd
)"


PYTHON_BIN="${ATLAS_BUILD_PYTHON:-python3}"
OUTPUT_ROOT="${ATLAS_RELEASE_OUTPUT:-$ROOT/dist-release}"


fail() {

    echo "ERROR: $*" >&2
    exit 1
}


for command in \
    git \
    tar \
    sha256sum \
    find \
    sort
do

    command -v "$command" \
        >/dev/null 2>&1 \
        || fail "required command not found: $command"

done


command -v "$PYTHON_BIN" \
    >/dev/null 2>&1 \
    || fail "build Python not found: $PYTHON_BIN"


if [ -n "$(
    git -C "$ROOT" status --porcelain
)" ]; then

    fail "release bundle requires a clean Git worktree"

fi


# setuptools/pip may create ROOT/build while assembling the wheel.
#
# A release build must never leave the source worktree dirty.
# Refuse to destroy a pre-existing directory, then own and clean
# only the build directory created by this invocation.
if [ -e "$ROOT/build" ]; then

    fail "release bundle requires the source build/ directory to be absent"

fi


cleanup_build_artifact() {

    rm -rf         "$ROOT/build"
}


trap cleanup_build_artifact EXIT


VERSION="$(
    "$PYTHON_BIN" - \
        "$ROOT/pyproject.toml" \
        <<'PY'
from pathlib import Path
import sys
import tomllib


path = Path(
    sys.argv[1]
)

data = tomllib.loads(
    path.read_text(
        encoding="utf-8"
    )
)

print(
    data["project"]["version"]
)
PY
)"


DISPLAY_VERSION="$(
    "$PYTHON_BIN" - \
        "$VERSION" \
        <<'PY'
import re
import sys


value = sys.argv[1]


match = re.fullmatch(
    r"(\d+\.\d+\.\d+)rc(\d+)",
    value,
)

if match:

    print(
        f"v{match.group(1)}-rc{match.group(2)}"
    )

else:

    print(
        value
        if value.startswith("v")
        else f"v{value}"
    )
PY
)"


BUNDLE_NAME="atlas-os-${DISPLAY_VERSION}"
STAGE="$OUTPUT_ROOT/$BUNDLE_NAME"

ARCHIVE="$OUTPUT_ROOT/${BUNDLE_NAME}.tar.gz"
ARCHIVE_SUM="$ARCHIVE.sha256"


rm -rf \
    "$STAGE" \
    "$ARCHIVE" \
    "$ARCHIVE_SUM"

mkdir -p \
    "$STAGE/wheel" \
    "$STAGE/scripts" \
    "$STAGE/ops/bin" \
    "$STAGE/ops/config" \
    "$STAGE/ops/systemd/atlas-collector.service.d" \
    "$STAGE/docs"


"$PYTHON_BIN" \
    -m pip \
    wheel \
    --no-deps \
    --wheel-dir "$STAGE/wheel" \
    "$ROOT"


WHEEL="$(
    find "$STAGE/wheel" \
        -maxdepth 1 \
        -type f \
        -name 'atlasctl-*.whl' \
        -print
)"


WHEEL_COUNT="$(
    printf '%s\n' "$WHEEL" \
        | sed '/^$/d' \
        | wc -l
)"


test "$WHEEL_COUNT" = "1" \
    || fail "expected exactly one atlasctl wheel"


install \
    -m 0755 \
    "$ROOT/scripts/install-atlas.sh" \
    "$STAGE/scripts/install-atlas.sh"


install \
    -m 0755 \
    "$ROOT/ops/bin/atlas-wait-ready" \
    "$STAGE/ops/bin/atlas-wait-ready"


install \
    -m 0644 \
    "$ROOT/ops/config/atlas.env.example" \
    "$STAGE/ops/config/atlas.env.example"


install \
    -m 0644 \
    "$ROOT/ops/config/atlas-web.env.example" \
    "$STAGE/ops/config/atlas-web.env.example"


install \
    -m 0644 \
    "$ROOT/ops/systemd/atlas-collector.service" \
    "$STAGE/ops/systemd/atlas-collector.service"


install \
    -m 0644 \
    "$ROOT/ops/systemd/atlas-web.service" \
    "$STAGE/ops/systemd/atlas-web.service"


install \
    -m 0644 \
    "$ROOT/ops/systemd/atlas-collector.service.d/boot-hardening.conf" \
    "$STAGE/ops/systemd/atlas-collector.service.d/boot-hardening.conf"


install \
    -m 0644 \
    "$ROOT/docs/INSTALL_V1.md" \
    "$STAGE/docs/INSTALL_V1.md"


install \
    -m 0644 \
    "$ROOT/LICENSE" \
    "$STAGE/LICENSE"


WHEEL_BASENAME="$(
    basename "$WHEEL"
)"


cat > "$STAGE/RELEASE_MANIFEST.txt" <<MANIFEST
ATLAS OS Release Bundle

Display-Version: $DISPLAY_VERSION
Package-Version: $VERSION
Wheel: wheel/$WHEEL_BASENAME

Runtime-Git-Required: no
Default-Web-Bind: 127.0.0.1:8091
Default-State: /var/lib/atlas/atlas.db
Operator-Execution-Default: fail-closed
Docker: optional
Proxmox: optional
Ollama: optional
Prometheus: optional
License: Apache-2.0
MANIFEST


# No repository metadata may enter the release bundle.
if find "$STAGE" \
    -name '.git' \
    -o -name '.github' \
    | grep -q .
then

    fail "repository metadata found in release bundle"

fi


# Audit public text assets for private RFC1918 defaults.
if grep -RInE \
    --exclude='*.whl' \
    '(192\.168\.[0-9]+\.[0-9]+|10\.[0-9]+\.[0-9]+\.[0-9]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+\.[0-9]+)' \
    "$STAGE"
then

    fail "private IPv4 found in release bundle"

fi


# Audit textual wheel members as well.
"$PYTHON_BIN" - \
    "$WHEEL" \
    <<'PY'
from pathlib import Path
import re
import sys
import zipfile


wheel = Path(
    sys.argv[1]
)


private_ipv4 = re.compile(
    rb"(?:"
    rb"192\.168\.\d{1,3}\.\d{1,3}"
    rb"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    rb"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    rb")"
)


with zipfile.ZipFile(
    wheel
) as archive:

    matches = []

    for name in archive.namelist():

        if name.endswith(
            (
                ".py",
                ".html",
                ".js",
                ".css",
                ".txt",
                ".md",
            )
        ):

            content = archive.read(
                name
            )

            if private_ipv4.search(
                content
            ):

                matches.append(
                    name
                )


if matches:

    raise SystemExit(
        "private IPv4 found in wheel members: "
        + ", ".join(
            matches
        )
    )


print(
    "Wheel private-network audit: PASS"
)
PY


(
    cd "$STAGE"

    find . \
        -type f \
        ! -name SHA256SUMS \
        -print0 \
        | sort -z \
        | xargs -0 sha256sum \
        > SHA256SUMS
)


(
    cd "$STAGE"

    sha256sum \
        --check \
        SHA256SUMS
)


mkdir -p \
    "$OUTPUT_ROOT"


tar \
    -C "$OUTPUT_ROOT" \
    -czf "$ARCHIVE" \
    "$BUNDLE_NAME"


sha256sum \
    "$ARCHIVE" \
    > "$ARCHIVE_SUM"


echo
echo "ATLAS release bundle: PASS"
echo "Version : $DISPLAY_VERSION"
echo "Bundle  : $STAGE"
echo "Archive : $ARCHIVE"
echo "SHA256  : $ARCHIVE_SUM"

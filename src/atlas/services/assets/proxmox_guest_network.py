from __future__ import annotations

import os
import re
import subprocess


class ProxmoxGuestNetworkService:
    """
    Read-only Proxmox guest identity observer.

    Retrieves:
    - VMID
    - guest name
    - type (VM/LXC)
    - power state
    - configured MAC
    - live IPv4 for running LXC guests

    No guest or host state is modified.
    """

    def snapshot(self):
        target = (
            os.getenv(
                "ATLAS_PROXMOX_HOST",
                ""
            ).strip()
        )

        if not target:
            return {
                "status": "NOT_CONFIGURED",
                "guests": [],
                "error":
                    "ATLAS_PROXMOX_HOST unavailable",
            }

        script = r'''
set -u

for VMID in $(qm list 2>/dev/null | awk 'NR>1 {print $1}'); do

    STATUS="$(
        qm status "$VMID" 2>/dev/null \
        | awk '{print $2}'
    )"

    CONFIG="$(
        qm config "$VMID" 2>/dev/null
    )"

    NAME="$(
        printf '%s\n' "$CONFIG" \
        | sed -n 's/^name: //p' \
        | head -n1
    )"

    NET0="$(
        printf '%s\n' "$CONFIG" \
        | sed -n 's/^net0: //p' \
        | head -n1
    )"

    MAC="$(
        printf '%s\n' "$NET0" \
        | sed -n \
            's/.*=[MmAaCcVvIiRrTtUuOoEe]*=\?\([0-9A-Fa-f:]\{17\}\).*/\1/p'
    )"

    if [ -z "$MAC" ]; then
        MAC="$(
            printf '%s\n' "$NET0" \
            | grep -oEi \
                '([0-9a-f]{2}:){5}[0-9a-f]{2}' \
            | head -n1
        )"
    fi

    printf 'QEMU|%s|%s|%s|%s|\n' \
        "$VMID" \
        "$NAME" \
        "$STATUS" \
        "$MAC"
done


for CTID in $(pct list 2>/dev/null | awk 'NR>1 {print $1}'); do

    STATUS="$(
        pct status "$CTID" 2>/dev/null \
        | awk '{print $2}'
    )"

    CONFIG="$(
        pct config "$CTID" 2>/dev/null
    )"

    NAME="$(
        printf '%s\n' "$CONFIG" \
        | sed -n 's/^hostname: //p' \
        | head -n1
    )"

    NET0="$(
        printf '%s\n' "$CONFIG" \
        | sed -n 's/^net0: //p' \
        | head -n1
    )"

    MAC="$(
        printf '%s\n' "$NET0" \
        | sed -n \
            's/.*hwaddr=\([^,]*\).*/\1/p'
    )"

    IPV4=""

    if [ "$STATUS" = "running" ]; then
        IPV4="$(
            pct exec "$CTID" -- \
                ip -o -4 addr show scope global \
                2>/dev/null \
            | awk \
                '$2 != "tailscale0" {
                    split($4,a,"/");
                    print a[1];
                    exit
                }'
        )"
    fi

    printf 'LXC|%s|%s|%s|%s|%s\n' \
        "$CTID" \
        "$NAME" \
        "$STATUS" \
        "$MAC" \
        "$IPV4"
done
'''

        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=5",
                    target,
                    "bash",
                    "-s",
                ],
                input=script,
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )
        except Exception as exc:
            return {
                "status": "ERROR",
                "guests": [],
                "error": str(exc),
            }

        if result.returncode:
            return {
                "status": "ERROR",
                "guests": [],
                "error":
                    result.stderr.strip()
                    or "Proxmox SSH observer failed",
            }

        guests = []

        for raw in (
            result.stdout
            .splitlines()
        ):
            parts = raw.split("|")

            if len(parts) < 6:
                continue

            guest_type = (
                parts[0].strip()
            )

            vmid = (
                parts[1].strip()
            )

            name = (
                parts[2].strip()
                or f"{guest_type} {vmid}"
            )

            status = (
                parts[3].strip()
                or "unknown"
            )

            mac = (
                parts[4].strip()
                .lower()
                or None
            )

            ip = (
                parts[5].strip()
                or None
            )

            guests.append(
                {
                    "guest_type":
                        guest_type,
                    "vmid":
                        vmid,
                    "name":
                        name,
                    "status":
                        status,
                    "mac":
                        mac,
                    "ip":
                        ip,
                }
            )

        guests.sort(
            key=lambda item:
                int(
                    item["vmid"]
                )
        )

        return {
            "status": "SUCCESS",
            "guests": guests,
            "error": None,
        }

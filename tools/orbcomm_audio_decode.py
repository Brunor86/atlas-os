#!/usr/bin/env python3

import argparse
import csv
import hashlib
import json
import re
import subprocess

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np


HEADERS = {
    0x65: "Sync",
    0x1A: "Message",
    0x1B: "Uplink_info",
    0x1C: "Downlink_info",
    0x1D: "Network",
    0x1E: "Fill",
    0x22: "Orbital",
}

HEADER_VALUES = np.array(
    list(HEADERS),
    dtype=np.uint8,
)

REVERSE_BYTE = np.array(
    [
        int(f"{value:08b}"[::-1], 2)
        for value in range(256)
    ],
    dtype=np.uint8,
)

FLETCHER_WEIGHTS = np.arange(
    12,
    0,
    -1,
    dtype=np.int64,
)


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as source:
        for block in iter(
            lambda: source.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def decode_audio(path, sample_rate):
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "pipe:1",
        ],
        stdout=subprocess.PIPE,
        check=True,
    )

    return np.frombuffer(
        result.stdout,
        dtype=np.float32,
    )


def valid_packet_mask(rows):
    sum1 = (
        np.sum(
            rows,
            dtype=np.int64,
            axis=1,
        )
        & 0xFF
    )

    sum2 = (
        rows.astype(np.int64)
        @ FLETCHER_WEIGHTS
    ) & 0xFF

    return (
        (sum1 == 0)
        & (sum2 == 0)
        & np.isin(
            rows[:, 0],
            HEADER_VALUES,
        )
    )


def decode_chunk(
    samples,
    samples_per_symbol,
):
    best = None

    for phase in range(samples_per_symbol):

        usable = samples[phase:]

        symbol_count = (
            len(usable)
            // samples_per_symbol
        )

        if symbol_count < 96:
            continue

        symbols = (
            usable[
                : symbol_count
                * samples_per_symbol
            ]
            .reshape(
                symbol_count,
                samples_per_symbol,
            )
            .sum(axis=1)
        )

        for polarity in (1, -1):

            bits = (
                polarity * symbols > 0
            ).astype(np.uint8)

            for packet_offset in range(96):

                stream = bits[
                    packet_offset:
                ]

                bit_count = (
                    len(stream)
                    // 96
                    * 96
                )

                if bit_count < 96:
                    continue

                rows = np.packbits(
                    stream[:bit_count]
                    .reshape(-1, 8),
                    axis=1,
                    bitorder="big",
                ).reshape(-1, 12)

                # ORBCOMM bit order inside byte.
                rows = REVERSE_BYTE[rows]

                mask = valid_packet_mask(
                    rows
                )

                score = int(
                    mask.sum()
                )

                if (
                    best is None
                    or score > best["score"]
                ):
                    best = {
                        "score": score,
                        "phase": phase,
                        "polarity": polarity,
                        "packet_offset":
                            packet_offset,
                        "rows": rows,
                        "mask": mask,
                    }

    counts = Counter()

    for header in best["rows"][
        best["mask"],
        0,
    ]:
        counts[
            HEADERS[int(header)]
        ] += 1

    best["counts"] = counts

    return best


def infer_start_time(path):
    match = re.search(
        r"(\d{4}-\d{2}-\d{2})"
        r"T(\d{2})-(\d{2})-(\d{2})",
        path.name,
    )

    if not match:
        return None

    value = (
        f"{match.group(1)} "
        f"{match.group(2)}:"
        f"{match.group(3)}:"
        f"{match.group(4)}"
    )

    return datetime.strptime(
        value,
        "%Y-%m-%d %H:%M:%S",
    ).replace(
        tzinfo=timezone.utc
    )


def self_test():
    # Valid 12-byte Fill packet:
    # Fletcher remainder = 0000.
    packet = np.frombuffer(
        bytes.fromhex(
            "1E000000000000000000B62C"
        ),
        dtype=np.uint8,
    )

    assert bool(
        valid_packet_mask(
            packet.reshape(1, 12)
        )[0]
    )

    # Build artificial received symbol stream.
    transmitted = REVERSE_BYTE[
        packet
    ]

    packet_bits = np.unpackbits(
        transmitted,
        bitorder="big",
    )

    prefix = np.array(
        [
            1, 0, 1, 1, 0, 0, 1,
            0, 1, 0, 1, 1, 1, 0,
            0, 1, 1,
        ],
        dtype=np.uint8,
    )

    bits = np.concatenate(
        [
            prefix,
            np.tile(
                packet_bits,
                100,
            ),
        ]
    )

    audio = np.repeat(
        np.where(
            bits > 0,
            1.0,
            -1.0,
        ),
        10,
    ).astype(np.float32)

    result = decode_chunk(
        audio,
        10,
    )

    assert result["score"] == 100
    assert (
        result["counts"]["Fill"]
        == 100
    )

    print(
        "SELF_TEST=PASS "
        "VALID_PACKETS=100"
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "audio",
        type=Path,
        nargs="?",
    )

    parser.add_argument(
        "--out-dir",
        type=Path,
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        default=48000,
    )

    parser.add_argument(
        "--symbol-rate",
        type=int,
        default=4800,
    )

    parser.add_argument(
        "--chunk-seconds",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--min-valid-per-chunk",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    if args.audio is None:
        parser.error(
            "audio is required"
        )

    if args.out_dir is None:
        parser.error(
            "--out-dir is required"
        )

    if (
        args.sample_rate
        % args.symbol_rate
        != 0
    ):
        raise SystemExit(
            "sample rate must be "
            "an integer multiple "
            "of symbol rate"
        )

    args.out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    samples_per_symbol = (
        args.sample_rate
        // args.symbol_rate
    )

    samples = decode_audio(
        args.audio,
        args.sample_rate,
    )

    chunk_samples = (
        args.chunk_seconds
        * args.sample_rate
    )

    start_time = infer_start_time(
        args.audio
    )

    output_rows = []
    totals = Counter()

    accepted_chunks = 0
    valid_total = 0

    for chunk_index, offset in enumerate(
        range(
            0,
            len(samples),
            chunk_samples,
        )
    ):

        chunk = samples[
            offset:
            offset + chunk_samples
        ]

        if len(chunk) < args.sample_rate:
            continue

        result = decode_chunk(
            chunk,
            samples_per_symbol,
        )

        accepted = (
            result["score"]
            >= args.min_valid_per_chunk
        )

        counts = (
            result["counts"]
            if accepted
            else Counter()
        )

        if accepted:
            accepted_chunks += 1
            valid_total += result["score"]
            totals.update(counts)

        row = {
            "chunk_index": chunk_index,
            "offset_s":
                chunk_index
                * args.chunk_seconds,
            "accepted": accepted,
            "valid_packets":
                result["score"]
                if accepted
                else 0,
            "phase":
                result["phase"],
            "polarity":
                result["polarity"],
            "packet_bit_offset":
                result[
                    "packet_offset"
                ],
        }

        for name in HEADERS.values():
            row[
                f"count_{name}"
            ] = counts.get(
                name,
                0,
            )

        if start_time:
            timestamp = (
                start_time
                + timedelta(
                    seconds=row[
                        "offset_s"
                    ]
                )
            )

            row["utc_start"] = (
                timestamp
                .isoformat()
                .replace(
                    "+00:00",
                    "Z",
                )
            )

        output_rows.append(row)

    summary = {
        "schema":
            "atlas-sky-orbcomm-"
            "audio-decode/v1",
        "input": str(
            args.audio
        ),
        "input_sha256":
            sha256_file(
                args.audio
            ),
        "audio_duration_s":
            len(samples)
            / args.sample_rate,
        "sample_rate_hz":
            args.sample_rate,
        "symbol_rate_baud":
            args.symbol_rate,
        "samples_per_symbol":
            samples_per_symbol,
        "chunk_seconds":
            args.chunk_seconds,
        "acceptance_min_valid_"
        "packets_per_chunk":
            args.min_valid_per_chunk,
        "accepted_chunks":
            accepted_chunks,
        "valid_packets_total":
            valid_total,
        "packet_counts":
            dict(totals),
        "privacy": {
            "message_payloads_exported":
                False,
        },
        "limitations": [
            (
                "Input is lossy "
                "FM-demodulated OGG, "
                "not complex IQ."
            ),
            (
                "24-byte Ephemeris "
                "frames are not "
                "validated in v0.1."
            ),
        ],
    }

    (
        args.out_dir
        / "summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    with (
        args.out_dir
        / "chunks.csv"
    ).open(
        "w",
        newline="",
    ) as output:

        writer = csv.DictWriter(
            output,
            fieldnames=list(
                output_rows[0]
            ),
        )

        writer.writeheader()
        writer.writerows(
            output_rows
        )

    print(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

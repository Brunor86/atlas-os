#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ATLAS_BLUE = "#0071e3"
ATLAS_TEXT = "#1d1d1f"
ATLAS_MUTED = "#86868b"
ATLAS_GRID = "#e5e5ea"
ATLAS_GREEN = "#28a745"


def read_ephemeris(path: Path) -> dict[str, np.ndarray]:
    rows = list(
        csv.DictReader(
            path.open(
                encoding="utf-8"
            )
        )
    )

    if not rows:
        raise SystemExit(
            f"No ephemeris rows in {path}"
        )

    def values(name: str) -> np.ndarray:
        return np.asarray(
            [
                float(row[name])
                for row in rows
            ],
            dtype=float,
        )

    return {
        "offset_s": values("offset_s"),
        "lat": values("latitude_deg"),
        "lon": values("longitude_deg"),
        "alt": values("altitude_km"),
        "tle_lat": values("tle_latitude_deg"),
        "tle_lon": values("tle_longitude_deg"),
        "tle_alt": values("tle_altitude_km"),
        "position_error": values("position_error_km"),
        "velocity_error": values("velocity_error_m_s"),
    }


def style_axis(ax):
    ax.set_facecolor("white")

    for spine in ax.spines.values():
        spine.set_color(ATLAS_GRID)

    ax.tick_params(
        colors=ATLAS_MUTED,
        labelsize=9,
    )

    ax.grid(
        True,
        color=ATLAS_GRID,
        linewidth=.8,
        alpha=.75,
    )

    ax.set_axisbelow(True)


def save(fig, path: Path):
    fig.patch.set_facecolor("white")

    fig.savefig(
        path,
        dpi=180,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(fig)


def trajectory(
    data: dict[str, np.ndarray],
    out: Path,
):
    fig, ax = plt.subplots(
        figsize=(9.2, 6.5)
    )

    style_axis(ax)

    ax.plot(
        data["tle_lon"],
        data["tle_lat"],
        linewidth=2.0,
        linestyle="--",
        color=ATLAS_MUTED,
        label="CelesTrak reference TLE",
        zorder=2,
    )

    ax.plot(
        data["lon"],
        data["lat"],
        linewidth=2.4,
        color=ATLAS_BLUE,
        label="FM116 decoded ephemeris",
        zorder=3,
    )

    ax.scatter(
        [data["lon"][0]],
        [data["lat"][0]],
        s=45,
        color=ATLAS_GREEN,
        label="Start",
        zorder=4,
    )

    ax.scatter(
        [data["lon"][-1]],
        [data["lat"][-1]],
        s=45,
        color=ATLAS_TEXT,
        label="End",
        zorder=4,
    )

    mean_error = float(
        np.mean(
            data["position_error"]
        )
    )

    ax.set_title(
        "Orbital trajectory validation",
        loc="left",
        color=ATLAS_TEXT,
        fontsize=16,
        fontweight="semibold",
        pad=16,
    )

    ax.text(
        0,
        1.015,
        (
            "Decoded spacecraft position vs independent orbital model  ·  "
            f"mean position error {mean_error:.3f} km"
        ),
        transform=ax.transAxes,
        color=ATLAS_MUTED,
        fontsize=9.5,
        va="bottom",
    )

    ax.set_xlabel(
        "Longitude (degrees)",
        color=ATLAS_MUTED,
    )

    ax.set_ylabel(
        "Latitude (degrees)",
        color=ATLAS_MUTED,
    )

    ax.legend(
        frameon=False,
        fontsize=9,
        loc="best",
    )

    save(
        fig,
        out / "trajectory_comparison.png",
    )


def position_error(
    data: dict[str, np.ndarray],
    out: Path,
):
    minutes = (
        data["offset_s"]
        - data["offset_s"][0]
    ) / 60.0

    error = data["position_error"]

    mean = float(
        np.mean(error)
    )

    maximum = float(
        np.max(error)
    )

    fig, ax = plt.subplots(
        figsize=(9.2, 5.3)
    )

    style_axis(ax)

    ax.plot(
        minutes,
        error,
        linewidth=2.4,
        color=ATLAS_BLUE,
        label="Decoded vs TLE",
    )

    ax.axhline(
        mean,
        linewidth=1.4,
        linestyle="--",
        color=ATLAS_GREEN,
        label=f"Mean {mean:.3f} km",
    )

    ax.axhline(
        maximum,
        linewidth=1.1,
        linestyle=":",
        color=ATLAS_MUTED,
        label=f"Maximum {maximum:.3f} km",
    )

    ax.set_title(
        "Position error vs reference orbit",
        loc="left",
        color=ATLAS_TEXT,
        fontsize=16,
        fontweight="semibold",
        pad=16,
    )

    ax.text(
        0,
        1.015,
        "Difference between FM116 transmitted ephemeris and CelesTrak TLE",
        transform=ax.transAxes,
        color=ATLAS_MUTED,
        fontsize=9.5,
        va="bottom",
    )

    ax.set_xlabel(
        "Minutes since first decoded ephemeris",
        color=ATLAS_MUTED,
    )

    ax.set_ylabel(
        "Position difference (km)",
        color=ATLAS_MUTED,
    )

    ax.legend(
        frameon=False,
        fontsize=9,
        loc="best",
    )

    save(
        fig,
        out / "ephemeris_position_error.png",
    )


def altitude(
    data: dict[str, np.ndarray],
    out: Path,
):
    minutes = (
        data["offset_s"]
        - data["offset_s"][0]
    ) / 60.0

    diff = (
        data["alt"]
        - data["tle_alt"]
    )

    mean_abs_diff = float(
        np.mean(
            np.abs(diff)
        )
    )

    fig, ax = plt.subplots(
        figsize=(9.2, 5.3)
    )

    style_axis(ax)

    ax.plot(
        minutes,
        data["tle_alt"],
        linewidth=2.0,
        linestyle="--",
        color=ATLAS_MUTED,
        label="CelesTrak reference TLE",
    )

    ax.plot(
        minutes,
        data["alt"],
        linewidth=2.4,
        color=ATLAS_BLUE,
        label="FM116 decoded ephemeris",
    )

    ax.set_title(
        "Altitude agreement",
        loc="left",
        color=ATLAS_TEXT,
        fontsize=16,
        fontweight="semibold",
        pad=16,
    )

    ax.text(
        0,
        1.015,
        (
            "Altitude received over RF vs orbital reference  ·  "
            f"mean absolute difference {mean_abs_diff:.3f} km"
        ),
        transform=ax.transAxes,
        color=ATLAS_MUTED,
        fontsize=9.5,
        va="bottom",
    )

    ax.set_xlabel(
        "Minutes since first decoded ephemeris",
        color=ATLAS_MUTED,
    )

    ax.set_ylabel(
        "Altitude (km)",
        color=ATLAS_MUTED,
    )

    ax.legend(
        frameon=False,
        fontsize=9,
        loc="best",
    )

    save(
        fig,
        out / "ephemeris_altitude.png",
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate FM116 science figures "
            "using the ATLAS OS visual language."
        )
    )

    parser.add_argument(
        "observation_directory",
        type=Path,
    )

    args = parser.parse_args()

    directory = (
        args.observation_directory
        .expanduser()
        .resolve()
    )

    csv_path = (
        directory
        / "ephemeris.csv"
    )

    if not csv_path.exists():
        raise SystemExit(
            f"Missing {csv_path}"
        )

    data = read_ephemeris(
        csv_path
    )

    trajectory(
        data,
        directory,
    )

    position_error(
        data,
        directory,
    )

    altitude(
        data,
        directory,
    )

    print(
        "ATLAS SKY FM116 FIGURES: REGENERATED"
    )

    for name in (
        "trajectory_comparison.png",
        "ephemeris_position_error.png",
        "ephemeris_altitude.png",
    ):
        path = directory / name

        print(
            f"{name}: {path.stat().st_size:,} bytes"
        )


if __name__ == "__main__":
    main()

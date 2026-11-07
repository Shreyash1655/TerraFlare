
"""Reproducible synthetic datasets for TerraFlare development.

These fixtures are for software testing and UI development only.
They are not NASA observations and must never be presented as real data.
"""

from __future__ import annotations

import hashlib

import h3
import numpy as np
import pandas as pd


def build_fixture() -> dict:
    rng = np.random.default_rng(42)

    # ---------------------------------------------------------
    # 1. Dataset period: 2013–2023 (11 complete calendar years)
    # ---------------------------------------------------------

    dates = pd.date_range("2013-01-01", "2023-12-31", freq="D")
    years = sorted(dates.year.unique())

    # Use genuine H3 cell identifiers at resolution 7.
    # These are synthetic locations around Goa, not NASA detections.
    cells = [
        {
            "id": "persistent",
            "lat": 15.490,
            "lon": 73.820,
        },
        {
            "id": "emerging",
            "lat": 15.510,
            "lon": 73.840,
        },
        {
            "id": "declining",
            "lat": 15.530,
            "lon": 73.860,
        },
        {
            "id": "sporadic",
            "lat": 15.550,
            "lon": 73.880,
        },
        {
            "id": "extra_1",
            "lat": 15.570,
            "lon": 73.900,
        },
        {
            "id": "extra_2",
            "lat": 15.590,
            "lon": 73.920,
        },
    ]

    for cell in cells:
        cell["h3_cell"] = h3.latlng_to_cell(
            cell["lat"],
            cell["lon"],
            7,
        )

    # Ensure every synthetic cell has a distinct H3 identifier.
    h3_ids = [cell["h3_cell"] for cell in cells]

    if len(h3_ids) != len(set(h3_ids)):
        raise RuntimeError(
            "Synthetic cell coordinates produced duplicate H3 cells. "
            "Adjust coordinates or H3 resolution."
        )

    # ---------------------------------------------------------
    # 2. Plant different fire-memory patterns
    # ---------------------------------------------------------

    cell_multipliers = {
        "persistent": {
            y: 1.0 for y in years
        },
        "emerging": {
            y: (
                0.0 if y <= 2018
                else 0.6 + 0.25 * (y - 2019)
            )
            for y in years
        },
        "declining": {
            y: (
                1.0 if y <= 2018
                else 0.08
            )
            for y in years
        },
        "sporadic": {
            y: (
                0.9 if y in [2013, 2016, 2019, 2022]
                else 0.0
            )
            for y in years
        },
        "extra_1": {
            y: 0.8 for y in years
        },
        "extra_2": {
            y: (
                0.7 if y % 2 == 0
                else 0.0
            )
            for y in years
        },
    }

    # ---------------------------------------------------------
    # 3. Generate harmonized daily cell activity
    # ---------------------------------------------------------

    harmonized_rows = []

    for year in years:
        year_dates = pd.date_range(
            f"{year}-01-01",
            f"{year}-12-31",
            freq="D",
        )

        # Earlier seasonal onset over time.
        year_offset = year - 2013
        season_center = 225 - 2.2 * year_offset
        season_width = 43

        day_of_year = year_dates.day_of_year.to_numpy()

        seasonal_curve = np.exp(
            -0.5
            * (
                (day_of_year - season_center)
                / season_width
            ) ** 2
        )

        for cell in cells:
            cell_id = cell["id"]
            multiplier = cell_multipliers[cell_id][year]

            for i, date in enumerate(year_dates):

                base = (
                    1.5
                    + 25.0 * seasonal_curve[i]
                )

                value = (
                    base
                    * multiplier
                    * rng.uniform(0.85, 1.15)
                )

                if multiplier == 0:
                    value = 0.0

                # Planted summer 2023 anomaly.
                if (
                    year == 2023
                    and pd.Timestamp("2023-06-19")
                    <= date
                    <= pd.Timestamp("2023-07-09")
                    and cell_id in [
                        "persistent",
                        "emerging",
                        "extra_1",
                    ]
                ):
                    value += 100.0 * multiplier

                value = max(0.0, float(value))

                uncertainty = value * 0.15

                # Simulated VIIRS outage.
                viirs_available = not (
                    cell_id
                    and date.year == 2022
                    and pd.Timestamp("2022-06-20")
                    <= date
                    <= pd.Timestamp("2022-06-30")
                )

                viirs_value = (
                    value * 0.55
                    if viirs_available
                    else 0.0
                )

                harmonized_rows.append({
                    "acq_date": date,
                    "region_id": "goa",
                    "h3_cell": cell["h3_cell"],
                    "harmonized_value": round(value, 4),
                    "harmonized_lower": round(
                        max(0.0, value - uncertainty),
                        4,
                    ),
                    "harmonized_upper": round(
                        value + uncertainty,
                        4,
                    ),
                    "modis_observed": round(
                        value * 0.45,
                        4,
                    ),
                    "viirs_observed": round(
                        viirs_value,
                        4,
                    ),
                    "interval_level": 0.95,
                    "method_id": "synthetic-demo-v1",
                })

    harmonized = pd.DataFrame(harmonized_rows)

    # ---------------------------------------------------------
    # 4. Generate point-level satellite observations
    # ---------------------------------------------------------

    observation_rows = []

    for date in dates:
        year = date.year

        for sensor in ["MODIS", "VIIRS"]:

            # Deliberately planted VIIRS observation gap.
            if (
                sensor == "VIIRS"
                and pd.Timestamp("2022-06-20")
                <= date
                <= pd.Timestamp("2022-06-30")
            ):
                continue

            for index, cell in enumerate(cells):

                multiplier = cell_multipliers[cell["id"]][year]

                if multiplier <= 0:
                    continue

                season_center = 225 - 2.2 * (year - 2013)

                seasonal = np.exp(
                    -0.5
                    * (
                        (date.day_of_year - season_center)
                        / 43
                    ) ** 2
                )

                probability = min(
                    0.95,
                    0.15 + 0.65 * seasonal,
                )

                if rng.random() > probability:
                    continue

                lat = cell["lat"] + rng.normal(0, 0.003)
                lon = cell["lon"] + rng.normal(0, 0.003)

                # Keep the 2023 activity episode spatially connected.
                is_event_period = (
                    year == 2023
                    and pd.Timestamp("2023-06-15")
                    <= date
                    <= pd.Timestamp("2023-07-15")
                )

                if is_event_period:
                    lat = 15.50 + rng.normal(0, 0.005)
                    lon = 73.84 + rng.normal(0, 0.005)

                observation_rows.append({
                    "acq_date": date,
                    "acq_datetime_utc": (
                        date + pd.Timedelta(hours=12 + index)
                    ),
                    "region_id": "goa",
                    "lat": float(lat),
                    "lon": float(lon),
                    "sensor_family": sensor,
                    "platform": (
                        "Terra"
                        if sensor == "MODIS"
                        else "Suomi-NPP"
                    ),
                    "frp_mw": round(
                        float(rng.uniform(5, 60)),
                        2,
                    ),
                    "is_valid": True,
                    "confidence_raw": (
                        "nominal"
                        if sensor == "MODIS"
                        else "high"
                    ),
                    "confidence_class": (
                        "medium"
                        if rng.random() < 0.5
                        else "high"
                    ),
                })

    observations = pd.DataFrame(observation_rows)

    # ---------------------------------------------------------
    # 5. Generate ingestion provenance
    # ---------------------------------------------------------

    provenance = pd.DataFrame([
        {
            "source_id": "synthetic-modis",
            "product_version": "MODIS-demo",
            "file_name": "synthetic_modis.csv",
            "sha256": hashlib.sha256(
                b"synthetic-modis"
            ).hexdigest(),
            "rows_in": int(
                (
                    observations["sensor_family"] == "MODIS"
                ).sum()
            ),
            "ingested_at": pd.Timestamp("2023-12-31"),
        },
        {
            "source_id": "synthetic-viirs",
            "product_version": "VIIRS-demo",
            "file_name": "synthetic_viirs.csv",
            "sha256": hashlib.sha256(
                b"synthetic-viirs"
            ).hexdigest(),
            "rows_in": int(
                (
                    observations["sensor_family"] == "VIIRS"
                ).sum()
            ),
            "ingested_at": pd.Timestamp("2023-12-31"),
        },
    ])

    # ---------------------------------------------------------
    # 6. Synthetic settlements exposure layer
    # ---------------------------------------------------------

    settlements = pd.DataFrame([
        {"lat": 15.500, "lon": 73.840, "value": 100},
        {"lat": 15.505, "lon": 73.845, "value": 250},
        {"lat": 15.510, "lon": 73.850, "value": 150},
        {"lat": 15.515, "lon": 73.855, "value": 300},
        {"lat": 15.520, "lon": 73.860, "value": 200},
    ])

    layers = {
        "settlements": {
            "df": settlements,
            "source": "TerraFlare synthetic development layer",
            "version": "demo-1",
            "is_synthetic": True,
        }
    }

    # ---------------------------------------------------------
    # 7. Synthetic calibration metadata
    # ---------------------------------------------------------

    calibration_info = {
        "method_id": "synthetic-demo-v1",
        "validation": [],
    }

    return {
        "harmonized_cell_day": harmonized,
        "obs_clean": observations,
        "ingest_log": provenance,
        "calibration_info": calibration_info,
        "layers": layers,
    }

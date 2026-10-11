TARGET_PROFILES = [
    {
        "key": "fm116",
        "name": "ORBCOMM FM116",
        "norad_id": 41189,
        "category": "Commercial communications",
        "primary_frequency_mhz": 137.800,
        "mode": "SDPSK 4800",
        "purpose": (
            "Machine-to-machine satellite communications used for remote "
            "asset tracking, monitoring and control."
        ),
        "atlas_can_read": [
            "Orbital Doppler signature",
            "Network and control frames",
            "Spacecraft identifiers",
            "Orbital-element packets",
            "Ephemeris position, altitude and velocity",
        ],
        "audit_kind": "orbcomm_digital",
    },
    {
        "key": "iss",
        "name": "International Space Station",
        "norad_id": 25544,
        "category": "Crewed orbital laboratory",
        "primary_frequency_mhz": 437.800,
        "secondary_frequency_mhz": 437.825,
        "mode": "FM / APRS",
        "purpose": (
            "Crewed research laboratory. ARISS adds amateur-radio and "
            "educational communications from the station."
        ),
        "atlas_can_read": [
            "Orbital Doppler signature",
            "437.800 MHz repeater downlink",
            "Voice when signal-to-noise is sufficient",
            "437.825 MHz APRS when active and decodable",
        ],
        "audit_kind": "iss_uhf",
    },
    {
        "key": "meteor_m24",
        "name": "METEOR-M2-4",
        "norad_id": 59051,
        "category": "Weather satellite",
        "primary_frequency_mhz": 137.900,
        "mode": "LRPT",
        "purpose": (
            "Operational Earth-observation weather satellite carrying "
            "meteorological imaging instruments."
        ),
        "atlas_can_read": [
            "Orbital Doppler signature",
            "LRPT digital downlink",
            "Weather imagery",
            "Pass quality and image coverage",
        ],
        "audit_kind": "meteor_lrpt",
    },
    {
        "key": "rs44",
        "name": "RS-44",
        "norad_id": 44909,
        "category": "Scientific / amateur radio",
        "primary_frequency_mhz": 435.605,
        "mode": "CW / linear transponder",
        "purpose": (
            "Scientific and amateur-radio spacecraft carrying a linear "
            "transponder and beacon."
        ),
        "atlas_can_read": [
            "Orbital Doppler signature",
            "Beacon carrier",
            "CW telemetry when signal quality permits",
            "Amateur transponder traffic when present",
        ],
        "audit_kind": "narrowband_uhf",
    },
    {
        "key": "ao73",
        "name": "AO-73 / FUNcube-1",
        "norad_id": 39444,
        "category": "Educational CubeSat",
        "primary_frequency_mhz": 145.935,
        "mode": "Telemetry / amateur radio",
        "purpose": (
            "Educational CubeSat designed for STEM outreach, telemetry "
            "reception and amateur-radio experimentation."
        ),
        "atlas_can_read": [
            "Orbital Doppler signature",
            "Telemetry carrier",
            "Digital telemetry when link margin is sufficient",
        ],
        "audit_kind": "funcube_vhf",
    },
]


STATION_CAPABILITIES = [
    {
        "band": "137–146 MHz",
        "rating": "STRONG",
        "title": "Weather & low-VHF satellites",
        "detail": (
            "Best current band with the outdoor ~54 cm-arm dipole. "
            "FM116 already demonstrated thousands of checksum-valid frames."
        ),
        "examples": "ORBCOMM, METEOR LRPT, AO-73",
    },
    {
        "band": "435–438 MHz",
        "rating": "CAPABLE",
        "title": "UHF amateur satellites & ISS",
        "detail": (
            "The RTL-SDR receives this band well, but the present VHF dipole "
            "is mismatched. ISS and RS-44 were still confirmed by Doppler."
        ),
        "examples": "ISS, RS-44",
    },
    {
        "band": "1090 MHz",
        "rating": "LIMITED",
        "title": "Aircraft ADS-B",
        "detail": (
            "Inside RTL-SDR coverage, but the current antenna is very poorly "
            "matched. A dedicated ~1090 MHz antenna is the meaningful upgrade."
        ),
        "examples": "ADS-B / Mode-S",
    },
    {
        "band": "HF / ~20 MHz",
        "rating": "FUTURE",
        "title": "Solar & Jupiter radio",
        "detail": (
            "Possible with RTL-SDR Blog V3 direct sampling and a suitable "
            "long-wire or dedicated HF antenna."
        ),
        "examples": "Radio JOVE-style experiments",
    },
    {
        "band": "1420.406 MHz",
        "rating": "FUTURE",
        "title": "Neutral hydrogen astronomy",
        "detail": (
            "Receiver coverage is possible, but useful observations require "
            "a dish/feed plus low-noise amplification and filtering."
        ),
        "examples": "Galactic H I line",
    },
]

TARGET_PROFILES = [
    {
        "key": "fm116",
        "name": "ORBCOMM FM116",
        "norad_id": 41189,
        "category": "Comunicaciones comerciales",
        "primary_frequency_mhz": 137.800,
        "mode": "SDPSK 4800",
        "purpose": (
            "Satélite de comunicaciones máquina a máquina utilizado para "
            "seguimiento de activos, monitoreo y control remoto."
        ),
        "atlas_can_read": [
            "Firma Doppler orbital",
            "Tramas de red y control",
            "Identificadores de la nave",
            "Paquetes de elementos orbitales",
            "Efemérides: posición, altitud y velocidad",
        ],
        "audit_kind": "orbcomm_digital",
    },
    {
        "key": "iss",
        "name": "Estación Espacial Internacional",
        "norad_id": 25544,
        "category": "Laboratorio orbital tripulado",
        "primary_frequency_mhz": 437.800,
        "secondary_frequency_mhz": 437.825,
        "mode": "FM / APRS",
        "purpose": (
            "Laboratorio de investigación tripulado. ARISS agrega "
            "comunicaciones educativas y de radioaficionados desde la estación."
        ),
        "atlas_can_read": [
            "Firma Doppler orbital",
            "Bajada del repetidor en 437.800 MHz",
            "Voz cuando la relación señal/ruido es suficiente",
            "APRS en 437.825 MHz cuando está activo y es decodificable",
        ],
        "audit_kind": "iss_uhf",
    },
    {
        "key": "meteor_m24",
        "name": "METEOR-M2-4",
        "norad_id": 59051,
        "category": "Satélite meteorológico",
        "primary_frequency_mhz": 137.900,
        "mode": "LRPT",
        "purpose": (
            "Satélite operativo de observación terrestre con instrumentos "
            "meteorológicos y transmisión directa de imágenes."
        ),
        "atlas_can_read": [
            "Firma Doppler orbital",
            "Bajada digital LRPT",
            "Imágenes meteorológicas",
            "Calidad del pase y cobertura de imagen",
        ],
        "audit_kind": "meteor_lrpt",
    },
    {
        "key": "rs44",
        "name": "RS-44",
        "norad_id": 44909,
        "category": "Científico / radioaficionados",
        "primary_frequency_mhz": 435.605,
        "mode": "CW / transpondedor lineal",
        "purpose": (
            "Nave científica y de radioaficionados con baliza y "
            "transpondedor lineal."
        ),
        "atlas_can_read": [
            "Firma Doppler orbital",
            "Portadora de baliza",
            "Telemetría CW si la señal lo permite",
            "Tráfico del transpondedor cuando existe",
        ],
        "audit_kind": "narrowband_uhf",
    },
    {
        "key": "ao73",
        "name": "AO-73 / FUNcube-1",
        "norad_id": 39444,
        "category": "CubeSat educativo",
        "primary_frequency_mhz": 145.935,
        "mode": "Telemetría / radioaficionados",
        "purpose": (
            "CubeSat educativo diseñado para divulgación STEM, recepción "
            "de telemetría y experimentación de radioaficionados."
        ),
        "atlas_can_read": [
            "Firma Doppler orbital",
            "Portadora de telemetría",
            "Telemetría digital si el margen del enlace es suficiente",
        ],
        "audit_kind": "funcube_vhf",
    },
]


STATION_CAPABILITIES = [
    {
        "band": "137–146 MHz",
        "rating": "FUERTE",
        "title": "Satélites meteorológicos y VHF",
        "detail": (
            "Es la mejor zona actual con el dipolo exterior de ~54 cm por brazo. "
            "FM116 ya demostró miles de tramas válidas por checksum."
        ),
        "examples": "ORBCOMM, METEOR LRPT, AO-73",
    },
    {
        "band": "435–438 MHz",
        "rating": "CAPAZ",
        "title": "UHF, ISS y radioaficionados",
        "detail": (
            "El RTL-SDR recibe bien esta banda, pero el dipolo actual no está "
            "adaptado. Aun así ISS y RS-44 fueron confirmados por Doppler."
        ),
        "examples": "ISS, RS-44",
    },
    {
        "band": "1090 MHz",
        "rating": "LIMITADO",
        "title": "Aeronaves ADS-B",
        "detail": (
            "Está dentro del rango del receptor, pero la antena actual está muy "
            "desadaptada. Una antena dedicada a 1090 MHz sería la mejora clave."
        ),
        "examples": "ADS-B / Mode-S",
    },
    {
        "band": "HF / ~20 MHz",
        "rating": "FUTURO",
        "title": "Radio solar y Júpiter",
        "detail": (
            "Posible con el RTL-SDR Blog V3 en muestreo directo y una antena "
            "HF adecuada, por ejemplo un hilo largo."
        ),
        "examples": "Experimentos tipo Radio JOVE",
    },
    {
        "band": "1420.406 MHz",
        "rating": "FUTURO",
        "title": "Radioastronomía de hidrógeno neutro",
        "detail": (
            "La frecuencia está dentro de la cobertura del receptor, pero para "
            "observarla de forma útil harán falta plato/alimentador, LNA y filtro."
        ),
        "examples": "Línea galáctica H I",
    },
]

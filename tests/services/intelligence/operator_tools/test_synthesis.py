from atlas.services.intelligence.operator_tools.synthesis import (
    synthesize_verified_tool_results,
)


def test_smart_synthesis_supports_multiple_disks():

    results = [
        {
            "name": "telemetry_smart",
            "result": {
                "tool": "telemetry_smart",
                "success": True,
                "error": None,
                "data": [
                    {
                        "device": "/dev/sda",
                        "model": "Virtual Disk",
                        "smart_available": False,
                        "temperature_c": None,
                        "health": "",
                    },
                    {
                        "device": "/dev/sdb",
                        "model": "Physical Disk",
                        "smart_available": True,
                        "temperature_c": 52,
                        "health": "PASSED",
                    },
                ],
            },
        },
    ]

    answer = synthesize_verified_tool_results(
        "¿Cuál es la temperatura del disco?",
        results,
    )

    assert answer is not None

    assert "Physical Disk" in answer
    assert "/dev/sdb" in answer
    assert "52.00 °C" in answer
    assert "PASSED" in answer

    assert "Virtual Disk" in answer
    assert "SMART no disponible" in answer


def test_smart_synthesis_supports_single_record():

    results = [
        {
            "name": "telemetry_smart",
            "result": {
                "tool": "telemetry_smart",
                "success": True,
                "error": None,
                "data": {
                    "device": "/dev/test",
                    "model": "Test Disk",
                    "smart_available": True,
                    "temperature_c": 40,
                    "health": "PASSED",
                },
            },
        },
    ]

    answer = synthesize_verified_tool_results(
        "temperatura del disco",
        results,
    )

    assert answer is not None
    assert "40.00 °C" in answer
    assert "PASSED" in answer

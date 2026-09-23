from dataclasses import dataclass


@dataclass(slots=True)
class CheckResult:

    name: str
    status: str
    message: str


@dataclass(slots=True)
class DoctorReport:

    checks: list[CheckResult]

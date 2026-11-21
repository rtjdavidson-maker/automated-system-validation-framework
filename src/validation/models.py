"""Typed contracts for the validation framework."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceReading:
    device_id: str
    voltage_v: float
    temperature_c: float
    latency_ms: float
    firmware_version: str
    responds: bool


@dataclass(frozen=True)
class TestCase:
    case_id: str
    description: str
    field: str
    rule: str
    expected: object


@dataclass(frozen=True)
class TestResult:
    device_id: str
    case_id: str
    status: str
    observed: object
    expected: object
    detail: str

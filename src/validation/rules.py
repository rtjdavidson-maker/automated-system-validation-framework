"""Configuration validation and strict, allowlisted test rules."""
import json
import math
from pathlib import Path
from .models import TestCase, TestResult, DeviceReading

FIELDS = {'voltage_v', 'temperature_c', 'latency_ms', 'firmware_version', 'responds'}
RULES = {'between', 'max', 'min_version', 'equals'}


def version_tuple(value: str) -> tuple[int, ...]:
    if not isinstance(value, str) or not value or not all(part.isdigit() for part in value.split('.')):
        raise ValueError('Version must have dot-separated numeric components')
    return tuple(int(part) for part in value.split('.'))


def load_cases(path: Path) -> list[TestCase]:
    """Load JSON cases, reject unsafe/unsupported rules and malformed values."""
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('cases'), list) or not data['cases']:
        raise ValueError('Configuration must contain a non-empty cases array')
    cases = []
    seen = set()
    for item in data['cases']:
        if not isinstance(item, dict) or not all(k in item for k in ('id', 'description', 'field', 'rule', 'expected')):
            raise ValueError('Each case needs id, description, field, rule and expected')
        case_id, field, rule, value = item['id'], item['field'], item['rule'], item['expected']
        if not isinstance(case_id, str) or not case_id.strip() or case_id in seen:
            raise ValueError('Case ids must be non-empty and unique')
        if not isinstance(item['description'], str) or not item['description'].strip():
            raise ValueError('Case descriptions must be non-empty')
        if field not in FIELDS or rule not in RULES:
            raise ValueError(f'Unsupported rule or field in case {case_id}')
        if rule == 'between':
            if (field not in {'voltage_v', 'temperature_c', 'latency_ms'}
                    or not isinstance(value, list) or len(value) != 2
                    or any(type(x) not in (int, float) or not math.isfinite(x) for x in value)
                    or value[0] > value[1]):
                raise ValueError('between expects ordered numeric [min,max]')
        elif rule == 'max':
            if field not in {'voltage_v', 'temperature_c', 'latency_ms'} or type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError('max requires a numeric measurement and limit')
        elif rule == 'min_version':
            if field != 'firmware_version':
                raise ValueError('min_version requires firmware_version')
            version_tuple(value)
        elif rule == 'equals':
            if field != 'responds' or type(value) is not bool:
                raise ValueError('equals is only supported for a boolean responds field')
        seen.add(case_id)
        cases.append(TestCase(case_id, item['description'], field, rule, value))
    return cases


def evaluate(device: DeviceReading, case: TestCase) -> TestResult:
    observed = getattr(device, case.field)
    if not device.responds and case.field != 'responds':
        return TestResult(device.device_id, case.case_id, 'ERROR', None, case.expected,
                          'Simulated device unavailable; measurement not collected')
    if case.rule == 'between':
        passed = case.expected[0] <= observed <= case.expected[1]
    elif case.rule == 'max':
        passed = observed <= case.expected
    elif case.rule == 'min_version':
        passed = version_tuple(observed) >= version_tuple(case.expected)
    elif case.rule == 'equals':
        passed = observed is case.expected
    else:
        raise ValueError('Unrecognized test rule')
    return TestResult(device.device_id, case.case_id, 'PASS' if passed else 'FAIL',
                      observed, case.expected, 'Within specification' if passed else 'Out of specification')


def evaluate_all(devices: list[DeviceReading], cases: list[TestCase]) -> list[TestResult]:
    return [evaluate(device, case) for device in devices for case in cases]

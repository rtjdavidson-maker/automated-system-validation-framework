"""Deterministic, simulated device adapter; no physical hardware."""
from .models import DeviceReading

BASELINE = (
    DeviceReading('UNIT-A', 3.30, 28.0, 22.0, '1.2.0', True),
    DeviceReading('UNIT-B', 2.90, 32.0, 145.0, '1.2.0', True),
    DeviceReading('UNIT-C', 3.35, 78.0, 35.0, '1.0.0', True),
)


def get_devices(profile: str = 'baseline') -> list[DeviceReading]:
    """Return fixture devices; profiles illustrate faults and recovery."""
    if profile == 'baseline':
        return list(BASELINE)
    if profile == 'recovered':
        return [DeviceReading(d.device_id, 3.3, 25.0, 20.0, '1.2.0', True)
                for d in BASELINE]
    if profile == 'outage':
        return [DeviceReading('UNIT-A', 3.3, 25.0, 20.0, '1.2.0', False),
                *list(BASELINE[1:])]
    raise ValueError(f'Unknown simulated profile: {profile}')

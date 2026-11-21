# Automated System Validation Framework

**Python · pytest · SQLite · JSON configurations · HTML reporting · GitHub Actions**

A reusable, data-driven system validation framework for **simulated electronic devices**. The software checks voltage, temperature, response latency, firmware version and device availability against configurable specifications, saves results to SQLite, generates an HTML dashboard and identifies regressions and improvements between runs.

> **Engineering scope:** All readings are synthetic. This project does **not** connect to or validate physical hardware. Baseline failures are intentionally injected device conditions, not software defects.

## Features

- Five configurable acceptance tests in `config/validation_cases.json`, applied to three virtual devices
- Allowlisted validation rules: numeric ranges, maximum thresholds, minimum firmware version and boolean status
- Three repeatable simulation profiles: `baseline`, `recovered`, `outage`
- SQLite history with run IDs and device-level outcomes
- Regression and recovery comparisons
- Offline JSON reports and HTML dashboard
- **34 automated pytest checks** and GitHub Actions continuous integration

## Windows quick start

Download the GitHub ZIP and select **Extract All**. Open the folder containing `run.py` and `requirements.txt`. Click File Explorer's address bar, type `cmd`, press Enter, and run:

```cmd
python -m pip install -r requirements.txt
python run.py --profile baseline
start "" "output\dashboard.html"
python run.py --profile recovered
python run.py --history
python -m pytest -v
```

Expected baseline: **15 checks, 11 PASS, 4 FAIL, 0 ERROR**. Expected recovered profile: **15 PASS, 0 FAIL, 0 ERROR**, with **four improvements** if it directly follows baseline in the same database. Expected pytest run: **34 passed**.

Optional outage experiment:

```cmd
python run.py --profile outage
```

## Screenshots: Windows validation and test evidence

These seven screenshots document the simulator running locally on Windows, including the baseline, recovery, SQLite history, automated tests and HTML dashboard.

### 1. Python test dependencies installed

The Windows console shows pytest installed successfully. A PATH warning for standalone executables is not a failing installation when running `python -m pytest`.

![Python pytest installation in Windows Command Prompt](Screenshot%202026-11-21%20153135.png)

### 2. Baseline: intentionally injected device faults

Three simulated devices undergo 15 checks. The baseline catches four intentionally out-of-specification values: UNIT-B voltage and response latency; UNIT-C temperature and firmware version.

![Baseline simulated device validation, eleven passes and four intentional failures](Screenshot%202026-11-21%20153222.png)

### 3. Recovery: all device checks pass

The recovered profile produces **15 passing checks**, **zero regressions** and **four improvements** relative to the previous baseline.

![Recovered simulated device validation with all 15 checks passing](Screenshot%202026-11-21%20153359.png)

### 4. Stored history and pytest execution

The framework retrieves baseline/recovery run summaries and starts the automated validation test suite.

![SQLite run history and start of pytest automated checks](Screenshot%202026-11-21%20153517.png)

### 5. All 34 automated pytest checks passed

The terminal confirms `34 passed`, covering configuration validation, rule boundaries, offline-device behavior, database persistence, regression detection, and report generation.

![Terminal displaying all 34 passing pytest unit tests](Screenshot%202026-11-21%20153542.png)

### 6. HTML validation dashboard overview

A browser report summarizes the first baseline run: **15 checks, 11 passed, 4 failed, 0 execution errors**.

![HTML automated system validation dashboard summary](Screenshot%202026-11-21%20153606.png)

### 7. Per-device failures and expected thresholds

Detailed report rows display observed values, specification thresholds and explanations for each validation result.

![Detailed per-device automated test results with highlighted failures](Screenshot%202026-11-21%20153627.png)

## Validation specification

| Check | Acceptance rule |
|---|---|
| Supply voltage | Between 3.0 and 3.5 V |
| Operating temperature | Between 0 and 70 °C |
| Response latency | 100 ms or less |
| Firmware | Version 1.2.0 or newer |
| Connectivity | Device responds |

Configuration is stored separately from the Python engine, which makes testing other simulated device requirements straightforward.

## Repository structure

```text
run.py
config/validation_cases.json
src/validation/models.py
src/validation/device.py
src/validation/rules.py
src/validation/database.py
src/validation/reports.py
tests/test_framework.py
.github/workflows/tests.yml
requirements.txt
pytest.ini
README.md
```

## Technical skills and next steps

This project demonstrates Python test architecture, pytest, JSON configuration, validation design, software QA, SQLite, regression tracking, HTML reporting, and CI/CD.

**Next integration milestone:** Replace the synthetic fixture adapter with telemetry from an ESP32 over a tested serial connection. Preserve the existing validation rules and reporting interface, then document hardware measurements separately.

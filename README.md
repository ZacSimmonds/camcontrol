# camcontrol

Windows-first Python CLI + library for communicating with Camlock USB serial devices (CH340), including PICO Hub-style line commands.

## Install

```powershell
pip install camcontrol
```

## CLI usage

```powershell
camcontrol list
camcontrol connect
camcontrol send STATE
camcontrol send UNLOCK
camcontrol send TEMP
camcontrol temp
camcontrol interactive
```

Optional multi-channel flag (reserved for ACS200-style devices):

```powershell
camcontrol send STATE --port 3
```

## Python usage

```python
from camcontrol import SerialManager
from camcontrol.serial_manager import SerialConfig

with SerialManager(SerialConfig(port="COM15")) as mgr:
    print(mgr.send_and_read_response("STATE"))
```

## Example app

Run the included example script:

```powershell
python examples\basic_demo.py
python examples\basic_demo.py --com COM15
```

## Notes

- Commands are sent as complete lines terminated by `\n` (never character-by-character).
- Responses are read as line-based text; multi-line responses are collected until a blank line or timeout.
- Serial speed is fixed at **115200 baud**.
- Package name on PyPI and the import/package name are both `camcontrol`.
- For development installs from source, you can use `pip install -e .` from the project folder.

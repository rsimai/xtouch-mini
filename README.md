# XTouch Mini

A minimal MIDI device controller application for Behringer XR18.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

The application automatically creates `config.json` with default settings. If the XR18 IP is incorrect or unreachable, you'll be prompted to enter the correct IP address.

```json
{
  "xr18_ip": "192.168.0.22",
  "xr18_port": 10024,
  "midi_device": null
}
```

## Usage

### Learn Mode
Discover and map MIDI controls to XR18 functions:

```bash
python main.py --learn
```

- Press controls on your XTouch Mini
- For each new control, specify:
  - Channel: 1-16, 'aux', or 'master'
  - Control type: volume, mute, or solo
- Button release events are automatically ignored
- Press Ctrl+C to save and exit
- To reprogram remove the control record

### Normal Mode
Run the MIDI to OSC translator:

```bash
python main.py
```

- Automatically verifies XR18 connection through ping, prompts for IP if needed
- Automatically connects to saved MIDI device
- Translates MIDI events to XR18 OSC commands
- Press Ctrl+C to exit

## Features

- **Auto-discovery**: Automatically detects and saves MIDI device
- **Interactive mapping**: Map controls during learn mode
- **Connection verification**: Pings XR18 to verify connectivity
- **Persistent settings**: Saves device and IP configuration
- **Button toggles**: Mute and solo buttons toggle on press
- **Smart filtering**: Ignores button release events during mapping

## Supported Controls

- **Channels 1-16**: Full volume, mute, and solo control
- **Aux channel**: Full volume, mute, and solo control
- **Master channel**: Full volume, mute, and solo control
- **Volume controls**: Continuous 0-127 MIDI to 0.0-1.0 OSC
- **Button controls**: Toggle behavior for mute/solo

## Build Single Binary

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller main.py --onefile
deactivate
```
Copy dist/main to your ~/bin, run this for the mapping.

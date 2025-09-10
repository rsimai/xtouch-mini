#!/usr/bin/env python3
import rtmidi
import json
import socket
import sys
import signal
from pythonosc import udp_client

def load_config():
    """Load configuration from config.json."""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("config.json not found. Using defaults.")
        return {"xr18_ip": "192.168.1.100", "xr18_port": 10024, "midi_device": None}

def check_xr18_connection(ip, port):
    """Check if XR18 is reachable."""
    import subprocess
    try:
        result = subprocess.run(['ping', '-c', '1', '-W', '2000', ip], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def list_midi_devices():
    """List available MIDI input devices."""
    midiin = rtmidi.MidiIn()
    ports = midiin.get_ports()
    midiin.close_port()
    return ports

def save_config(config):
    """Save configuration to config.json."""
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)

def save_controls(controls):
    """Save MIDI controls to controls.json."""
    with open('controls.json', 'w') as f:
        json.dump(controls, f, indent=2)

def load_controls():
    """Load MIDI controls from controls.json."""
    try:
        with open('controls.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("controls.json not found. Run with --learn first.")
        return {}

def map_controls():
    """Map controls to XR18 functions."""
    controls = load_controls()
    if not controls:
        return
    
    unmapped = {k: v for k, v in controls.items() if v.get('activity') is None}
    if not unmapped:
        print("All controls already mapped.")
        return
    
    print(f"Mapping {len(unmapped)} unmapped controls...")
    
    for control_key in unmapped:
        print(f"\nControl: {control_key}")
        
        channel_input = input("Channel number (1-16, 'aux', or 'master'): ").strip().lower()
        if channel_input == 'master':
            channel = 'master'
        elif channel_input == 'aux':
            channel = 'aux'
        else:
            try:
                channel = int(channel_input)
                if not 1 <= channel <= 16:
                    print("Invalid channel. Skipping.")
                    continue
            except ValueError:
                print("Invalid input. Skipping.")
                continue
        
        print("Control type:")
        print("1: volume")
        print("2: mute")
        print("3: solo")
        
        try:
            choice = int(input("Select (1-3): "))
            control_types = {1: "volume", 2: "mute", 3: "solo"}
            if choice not in control_types:
                print("Invalid choice. Skipping.")
                continue
            control_type = control_types[choice]
        except ValueError:
            print("Invalid input. Skipping.")
            continue
        
        osc_paths = {
            "volume": f"/ch/{channel:02d}/mix/fader",
            "mute": f"/ch/{channel:02d}/mix/on",
            "solo": f"/-stat/solosw/{channel:02d}"
        }
        
        if channel == 'master':
            osc_paths = {
                "volume": "/lr/mix/fader",
                "mute": "/lr/mix/on",
                "solo": "/-stat/solosw/lr"
            }
        elif channel == 'aux':
            osc_paths = {
                "volume": "/rtn/aux/mix/fader",
                "mute": "/rtn/aux/mix/on",
                "solo": "/rtn/aux/mix/solo"
            }
        else:
            osc_paths = {
                "volume": f"/ch/{channel:02d}/mix/fader",
                "mute": f"/ch/{channel:02d}/mix/on",
                "solo": f"/-stat/solosw/{channel:02d}"
            }
        

        
        controls[control_key] = {
            "activity": control_type,
            "channel": channel,
            "osc_path": osc_paths[control_type]
        }
    
    save_controls(controls)
    print(f"\nMapping saved to controls.json")

def map_control(key):
    """Map a single control to XR18 function."""
    print(f"\nNew control: {key}")
    
    channel_input = input("Channel number (1-16, 'aux', or 'master'): ").strip().lower()
    if channel_input == 'master':
        channel = 'master'
    elif channel_input == 'aux':
        channel = 'aux'
    else:
        try:
            channel = int(channel_input)
            if not 1 <= channel <= 16:
                print("Invalid channel. Skipping.")
                return None
        except ValueError:
            print("Invalid input. Skipping.")
            return None
    
    print("Control type:")
    print("1: volume")
    print("2: mute")
    print("3: solo")
    
    try:
        choice = int(input("Select (1-3): "))
        control_types = {1: "volume", 2: "mute", 3: "solo"}
        if choice not in control_types:
            print("Invalid choice. Skipping.")
            return None
        control_type = control_types[choice]
    except ValueError:
        print("Invalid input. Skipping.")
        return None
    
    if channel == 'master':
        osc_paths = {
            "volume": "/lr/mix/fader",
            "mute": "/lr/mix/on",
            "solo": "/-stat/solosw/lr"
        }
    elif channel == 'aux':
        osc_paths = {
            "volume": "/rtn/aux/mix/fader",
            "mute": "/rtn/aux/mix/on",
            "solo": "/rtn/aux/mix/solo"
        }
    else:
        osc_paths = {
            "volume": f"/ch/{channel:02d}/mix/fader",
            "mute": f"/ch/{channel:02d}/mix/on",
            "solo": f"/-stat/solosw/{channel:02d}"
        }
    

    
    return {
        "activity": control_type,
        "channel": channel,
        "osc_path": osc_paths[control_type]
    }

def learn_controls(midiin, force_learn=False):
    """Learn MIDI controls and create sorted list."""
    controls = load_controls()
    mode_text = "Force-learn mode" if force_learn else "Learn mode"
    print(f"{mode_text}: Press MIDI controls. Press Ctrl+C to exit and save.")
    
    def midi_callback(msg, data):
        if msg[0]:
            key = f"{msg[0][0]}_{msg[0][1]}" if len(msg[0]) > 1 else str(msg[0][0])
            value = msg[0][2] if len(msg[0]) > 2 else None
            
            # Skip button release events (value 0) during mapping
            if value == 0:
                return
            
            # Check if control is new or has no activity (or force-learn mode)
            if key not in controls or controls[key].get('activity') is None or force_learn:
                print(f"Control: {key}, Value: {value}")
                mapping = map_control(key)
                if mapping:
                    controls[key] = mapping
                    save_controls(controls)
                    print(f"Mapped {key} -> {mapping['osc_path']}")
                else:
                    controls[key] = {"activity": None}
    
    midiin.set_callback(midi_callback)
    
    def signal_handler(sig, frame):
        midiin.cancel_callback()
        sorted_controls = dict(sorted(controls.items()))
        save_controls(sorted_controls)
        print(f"\nSaved {len(sorted_controls)} controls to controls.json")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        signal_handler(None, None)

def select_device(devices, saved_device=None):
    """Select a MIDI device from available options."""
    if not devices:
        print("No MIDI devices found.")
        return None
    
    # Check if saved device is still available
    if saved_device and saved_device in devices:
        print(f"Using saved device: {saved_device}")
        return devices.index(saved_device)
    
    print("Available MIDI devices:")
    for i, device in enumerate(devices):
        print(f"{i}: {device}")
    
    try:
        choice = int(input("Select device (number): "))
        if 0 <= choice < len(devices):
            return choice
    except ValueError:
        pass
    
    print("Invalid selection.")
    return None

def main():
    learn_mode = "--learn" in sys.argv
    force_learn_mode = "--force-learn" in sys.argv
    config = load_config()
    
    if not learn_mode and not force_learn_mode:
        # Check XR18 connection
        while True:
            print(f"Checking XR18 at {config['xr18_ip']}:{config['xr18_port']}...")
            if check_xr18_connection(config['xr18_ip'], config['xr18_port']):
                print("XR18 found.")
                break
            else:
                print("XR18 not found.")
                new_ip = input("Enter XR18 IP address: ").strip()
                if not new_ip:
                    return
                config['xr18_ip'] = new_ip
                save_config(config)
        
        # Setup OSC client
        osc_client = udp_client.SimpleUDPClient(config['xr18_ip'], config['xr18_port'])
        
        # Send /xremote to enable remote control
        osc_client.send_message("/xremote", None)
    
    devices = list_midi_devices()
    device_index = select_device(devices, config.get('midi_device'))
    
    if device_index is not None:
        selected_device = devices[device_index]
        print(f"Selected: {selected_device}")
        
        # Save device selection if it's new
        if config.get('midi_device') != selected_device:
            config['midi_device'] = selected_device
            save_config(config)
        
        # Connect to MIDI device
        midiin = rtmidi.MidiIn()
        midiin.open_port(device_index)
        
        if learn_mode or force_learn_mode:
            learn_controls(midiin, force_learn_mode)
        else:
            controls = load_controls()
            if not controls:
                print("No controls found. Run with --learn first.")
                midiin.close_port()
                return
            
            print("Normal mode: Processing MIDI events. Press Ctrl+C to exit.")
            
            # Track button states for toggle functionality
            button_states = {}
            
            def midi_callback(msg, data):
                if msg[0]:
                    key = f"{msg[0][0]}_{msg[0][1]}" if len(msg[0]) > 1 else str(msg[0][0])
                    value = msg[0][2] if len(msg[0]) > 2 else 0
                    
                    if key in controls and controls[key].get('osc_path'):
                        osc_path = controls[key]['osc_path']
                        activity = controls[key]['activity']
                        
                        if activity == 'volume':
                            normalized_value = value / 127.0
                            osc_client.send_message(osc_path, normalized_value)
                            print(f"MIDI {key}={value} -> OSC {osc_path}={normalized_value}")
                        elif activity in ['mute', 'solo'] and value > 0:  # Only on button press
                            # Toggle button state
                            current_state = button_states.get(key, False)
                            new_state = not current_state
                            button_states[key] = new_state
                            
                            if activity == 'mute':
                                normalized_value = 0 if new_state else 1  # XR18 mute is inverted
                            else:  # solo
                                normalized_value = 1 if new_state else 0
                            
                            osc_client.send_message(osc_path, normalized_value)
                            print(f"MIDI {key} toggle -> OSC {osc_path}={normalized_value}")
            
            midiin.set_callback(midi_callback)
            
            def signal_handler(sig, frame):
                midiin.cancel_callback()
                print("\nExiting...")
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            
            try:
                while True:
                    pass
            except KeyboardInterrupt:
                signal_handler(None, None)
        
        midiin.close_port()
    else:
        print("No device selected.")

if __name__ == "__main__":
    main()
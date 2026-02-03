# Pico Hand Tracking Server

This module enables simultaneous control of arms/lower body and hands using two separate Pico controllers.

## Architecture

- **Terminal 1 (Main Control Loop)**: Runs the teleop policy loop connected to Pico #1 for arm and lower body control
- **Terminal 2 (Hand Tracking Server)**: Runs the hand tracking server connected to Pico #2 for hand tracking only

## Usage

### Step 1: Start the Hand Tracking Server

In a separate terminal, run:

```bash
python scripts/run_pico_hand_tracking_server.py --port 5557
```

Or directly:

```bash
python -m gr00t_wbc.control.teleop.device.pico.pico_hand_tracking_server --port 5557
```

This will:
- Connect to a different Pico controller (Pico #2)
- Stream only hand tracking data (left/right hand joints)
- Serve data via ZMQ on port 5557 (default)

### Step 2: Run the Main Teleop Loop

In the main terminal, run your teleop policy loop with:

```bash
# Set hand_control_device to "pico_hand_tracking"
python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body-control-device pico \
    --hand-control-device pico_hand_tracking \
    --hand-tracking-server-host localhost \
    --hand-tracking-server-port 5557
```

This will:
- Connect to Pico #1 for arm/lower body control
- Connect to the hand tracking server (running in Terminal 2) for hand tracking
- Combine both data streams for simultaneous control

## Configuration Options

- `--hand-tracking-server-host`: Host where the server is running (default: `localhost`)
- `--hand-tracking-server-port`: Port where the server is listening (default: `5557`)

## How It Works

1. The **Pico Hand Tracking Server** (`pico_hand_tracking_server.py`) connects to Pico #2 and extracts only hand tracking data (hand joints, headset pose).

2. The **Pico Hand Tracking Client Streamer** (`pico_hand_tracking_client_streamer.py`) connects to the server via ZMQ and receives hand tracking data.

3. The **TeleopStreamer** merges data from:
   - Body streamer (Pico #1): Arm poses, lower body navigation, control commands
   - Hand streamer (Pico #2 via server): Hand tracking data only

4. The combined data is processed and sent to the robot for simultaneous arm and hand control.

## Notes

- Make sure both Pico controllers are connected and the Pico service is running
- The server must be started before the main teleop loop
- If the server is unavailable, the client will return zero hand data (no crash)
- The server runs the Pico service automatically, so only one Pico service should be running per Pico device

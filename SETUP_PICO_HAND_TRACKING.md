# Setup Guide: Dual Pico Hand Tracking

This guide shows how to run the system with two Pico controllers:
- **Pico #1**: Arm and lower body control (main terminal)
- **Pico #2**: Hand tracking only (server terminal)

## Prerequisites

1. **Two Pico controllers** connected and configured
2. **Pico service** should be running (automatically started by the server)
3. **ROS2** environment should be set up (for the control loop)

## Step-by-Step Setup

### Step 1: Start the Control Loop (Terminal 1)

First, start the main G1 control loop:

```bash
python -m gr00t_wbc.control.main.teleop.run_g1_control_loop \
    --interface sim \
    --simulator mujoco \
    --control_frequency 50 \
    --sim_frequency 200
```

**Or for real robot:**
```bash
python -m gr00t_wbc.control.main.teleop.run_g1_control_loop \
    --interface real \
    --control_frequency 50
```

Keep this terminal running.

---

### Step 2: Start the Hand Tracking Server (Terminal 2)

In a **separate terminal**, start the Pico hand tracking server that connects to **Pico #2**:

```bash
# Option 1: Using the standalone script
python scripts/run_pico_hand_tracking_server.py --port 5557

# Option 2: Direct module execution
python -m gr00t_wbc.control.teleop.device.pico.pico_hand_tracking_server --port 5557
```

**Expected output:**
```
Starting Pico hand tracking server on port 5557...
Pico XR client initialized for hand tracking server
Pico service running with pid <PID>
Pico hand tracking server bound to port 5557
Pico hand tracking server running. Waiting for requests...
```

**Keep this terminal running.** The server will continuously stream hand tracking data from Pico #2.

---

### Step 3: Start the Teleop Policy Loop (Terminal 3 - Client)

In a **third terminal**, start the teleop policy loop that connects to **Pico #1** for arm/lower body and the server for hand tracking:

```bash
python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body_control_device pico \
    --hand_control_device pico_hand_tracking \
    --hand_tracking_server_host localhost \
    --hand_tracking_server_port 5557 \
    --teleop_frequency 20 \
    --enable_real_device
```

**Key parameters:**
- `--body_control_device pico`: Use Pico #1 for arm and lower body control
- `--hand_control_device pico_hand_tracking`: Use the hand tracking server (Pico #2)
- `--hand_tracking_server_host localhost`: Server host (use IP if on different machine)
- `--hand_tracking_server_port 5557`: Server port (must match server)
- `--teleop_frequency 20`: Teleop loop frequency (Hz)

**Expected output:**
```
running teleop policy, waiting teleop policy to be initialized...
Connecting to Pico hand tracking server at localhost:5557...
Connected to Pico hand tracking server
...
```

---

## Complete Command Reference

### Server Side (Terminal 2)
```bash
# Basic usage
python scripts/run_pico_hand_tracking_server.py --port 5557

# Custom port
python scripts/run_pico_hand_tracking_server.py --port 5558

# Direct module execution
python -m gr00t_wbc.control.teleop.device.pico.pico_hand_tracking_server --port 5557
```

### Client Side (Terminal 3)
```bash
# Basic usage
python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body_control_device pico \
    --hand_control_device pico_hand_tracking

# Full configuration
python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body_control_device pico \
    --hand_control_device pico_hand_tracking \
    --hand_tracking_server_host localhost \
    --hand_tracking_server_port 5557 \
    --teleop_frequency 20 \
    --enable_real_device \
    --enable_waist \
    --high_elbow_pose

# For simulation/testing (no real devices)
python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body_control_device pico \
    --hand_control_device pico_hand_tracking \
    --no-enable_real_device
```

---

## Troubleshooting

### Server Issues

**Problem:** Server fails to start
```bash
# Check if port is already in use
lsof -i :5557

# Kill existing process if needed
kill -9 <PID>
```

**Problem:** "Pico service not found"
- Make sure the Pico service script exists at `/opt/apps/roboticsservice/runService.sh`
- Or modify the path in `pico_hand_tracking_server.py`

**Problem:** "XRoboToolkit SDK not initialized"
- Make sure Pico #2 is connected and the XR SDK is installed
- Check that only one Pico service is running per Pico device

### Client Issues

**Problem:** "Timeout waiting for server response"
- Make sure the server (Terminal 2) is running
- Check that `--hand_tracking_server_port` matches the server port
- Verify network connectivity if using remote host

**Problem:** "Connection refused"
- Server might not be started yet - start Terminal 2 first
- Check firewall settings if connecting to remote host

**Problem:** Hand tracking not working
- Verify Pico #2 has hand tracking enabled
- Check server terminal for error messages
- Ensure hand tracking data is being received (check server logs)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Terminal 1: Control Loop                  │
│  run_g1_control_loop.py                                      │
│  - Receives commands from teleop policy                     │
│  - Controls robot joints                                     │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ ROS2 Messages
                            │
┌─────────────────────────────────────────────────────────────┐
│              Terminal 3: Teleop Policy Loop (Client)        │
│  run_teleop_policy_loop.py                                    │
│  - Pico #1 → Arm/Lower Body Control                          │
│  - Server (ZMQ) → Hand Tracking Data                        │
│  - Merges data and sends to control loop                     │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ ZMQ REQ/REP
                            │
┌─────────────────────────────────────────────────────────────┐
│            Terminal 2: Hand Tracking Server                 │
│  run_pico_hand_tracking_server.py                            │
│  - Pico #2 → Hand Tracking Only                              │
│  - Streams hand joints via ZMQ                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start (All-in-One)

If you want to run everything quickly:

**Terminal 1:**
```bash
python -m gr00t_wbc.control.main.teleop.run_g1_control_loop --interface sim
```

**Terminal 2:**
```bash
python scripts/run_pico_hand_tracking_server.py
```

**Terminal 3:**
```bash
python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body_control_device pico \
    --hand_control_device pico_hand_tracking
```

---

## Notes

- **Order matters**: Start Terminal 1 (control loop) → Terminal 2 (server) → Terminal 3 (teleop)
- **Pico assignment**: Make sure Pico #1 is the one you want for arm/body control, and Pico #2 is for hands
- **Network**: If running on different machines, use the machine's IP address instead of `localhost`
- **Port conflicts**: If port 5557 is in use, change it in both server and client commands

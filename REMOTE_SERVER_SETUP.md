# Remote Server Setup: Using Different Laptops

This guide explains how to run the hand tracking server on a different laptop than the client.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Laptop A (Main)                           │
│  - Control Loop (Terminal 1)                                  │
│  - Teleop Policy (Terminal 3)                                 │
│  - Pico #1 (Arm/Lower Body Control)                          │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ ZMQ over Network
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Laptop B (Server)                          │
│  - Hand Tracking Server (Terminal 2)                          │
│  - Pico #2 (Hand Tracking Only)                              │
└─────────────────────────────────────────────────────────────┘
```

## Setup Steps

### Step 1: Find IP Addresses

**On Laptop B (Server):**
```bash
# Linux/Mac
hostname -I
# or
ifconfig | grep "inet "

# Windows
ipconfig
# Look for IPv4 Address (e.g., 192.168.1.100)
```

**On Laptop A (Client):**
```bash
# Same commands to verify network connectivity
ping <LAPTOP_B_IP>
```

### Step 2: Start Server on Laptop B

**On Laptop B (Server laptop with Pico #2):**

```bash
# Navigate to project directory
cd /path/to/GR00T-WholeBodyControl

# Start the server
python scripts/run_pico_hand_tracking_server.py --port 5557
```

**Expected output:**
```
Starting Pico hand tracking server on *:5557...
Pico XR client initialized for hand tracking server
Pico service running with pid <PID>
Pico hand tracking server bound to port 5557
==> Pico hand tracking server is running
==> Listening on all interfaces (0.0.0.0:5557)
==> Clients can connect to: 192.168.1.100:5557
Pico hand tracking server running. Waiting for requests...
```

**Note the IP address shown** - you'll need it for the client.

### Step 3: Configure Firewall (If Needed)

**On Laptop B (Server):**

```bash
# Linux (UFW)
sudo ufw allow 5557/tcp

# Linux (firewalld)
sudo firewall-cmd --add-port=5557/tcp --permanent
sudo firewall-cmd --reload

# Mac (pfctl - may need to edit /etc/pf.conf)
# Or use System Preferences > Security & Privacy > Firewall

# Windows
# Control Panel > Windows Defender Firewall > Advanced Settings
# Add Inbound Rule for port 5557
```

### Step 4: Start Client on Laptop A

**On Laptop A (Main laptop with Pico #1):**

```bash
# Terminal 1: Control Loop
python -m gr00t_wbc.control.main.teleop.run_g1_control_loop --interface sim

# Terminal 3: Teleop Policy (with remote server)
python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body_control_device pico \
    --hand_control_device pico_hand_tracking \
    --hand_tracking_server_host 192.168.1.100 \
    --hand_tracking_server_port 5557
```

**Replace `192.168.1.100` with Laptop B's actual IP address.**

---

## Complete Command Reference

### Server Side (Laptop B)

```bash
# Basic (binds to all interfaces by default)
python scripts/run_pico_hand_tracking_server.py --port 5557

# Custom port
python scripts/run_pico_hand_tracking_server.py --port 5558
```

### Client Side (Laptop A)

```bash
# Connect to remote server
python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body_control_device pico \
    --hand_control_device pico_hand_tracking \
    --hand_tracking_server_host <LAPTOP_B_IP> \
    --hand_tracking_server_port 5557

# Example with IP 192.168.1.100
python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body_control_device pico \
    --hand_control_device pico_hand_tracking \
    --hand_tracking_server_host 192.168.1.100 \
    --hand_tracking_server_port 5557
```

---

## Network Requirements

1. **Same Network**: Both laptops must be on the same local network (same WiFi/router)
2. **Port Open**: Port 5557 (or your custom port) must be open on Laptop B
3. **No VPN**: VPNs may interfere with local network connections
4. **Firewall**: Firewall on Laptop B must allow incoming connections on port 5557

---

## Troubleshooting

### Connection Refused

**Problem:** Client can't connect to server

**Solutions:**
1. **Check server is running:**
   ```bash
   # On Laptop B
   netstat -an | grep 5557
   # Should show: tcp 0.0.0.0:5557 LISTEN
   ```

2. **Verify IP address:**
   ```bash
   # On Laptop B
   hostname -I
   # Use this exact IP in client
   ```

3. **Test connectivity:**
   ```bash
   # On Laptop A
   telnet <LAPTOP_B_IP> 5557
   # Or
   nc -zv <LAPTOP_B_IP> 5557
   ```

4. **Check firewall:**
   ```bash
   # On Laptop B, temporarily disable firewall to test
   # If it works, firewall is blocking - add port exception
   ```

### Timeout Errors

**Problem:** Client times out waiting for server

**Solutions:**
1. **Increase timeout** (edit `pico_hand_tracking_client_streamer.py`):
   ```python
   self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 seconds instead of 2
   ```

2. **Check network latency:**
   ```bash
   # On Laptop A
   ping <LAPTOP_B_IP>
   # Should be < 10ms on local network
   ```

3. **Verify server is responding:**
   ```bash
   # On Laptop B, check server logs for errors
   ```

### Wrong IP Address

**Problem:** Connected to wrong machine or IP changed

**Solutions:**
1. **Use static IP** or **reserve IP in router** for Laptop B
2. **Check IP before starting server:**
   ```bash
   # On Laptop B
   hostname -I
   ```

3. **Use hostname instead of IP** (if DNS configured):
   ```bash
   # On Laptop A
   python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
       --hand_tracking_server_host laptop-b.local \
       ...
   ```

---

## Security Considerations

⚠️ **Warning**: The server currently accepts connections from any IP on the network.

**For production use, consider:**
1. **Firewall rules** to restrict access to specific IPs
2. **VPN** for remote connections
3. **Authentication** in the ZMQ protocol (future enhancement)

**For local network use**, the current setup is sufficient.

---

## Testing Connection

**Quick test script** (run on Laptop A):

```python
import zmq
import pickle

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://<LAPTOP_B_IP>:5557")
socket.setsockopt(zmq.RCVTIMEO, 2000)

try:
    socket.send(b"request_data")
    message = socket.recv()
    data = pickle.loads(message)
    print("✓ Connection successful!")
    print(f"  Received data: {list(data.keys())}")
except Exception as e:
    print(f"✗ Connection failed: {e}")
finally:
    socket.close()
    context.term()
```

Save as `test_connection.py` and run:
```bash
python test_connection.py
```

---

## Example: Full Setup

**Laptop B (Server) - Terminal:**
```bash
$ hostname -I
192.168.1.100

$ python scripts/run_pico_hand_tracking_server.py
Starting Pico hand tracking server on *:5557...
==> Clients can connect to: 192.168.1.100:5557
Pico hand tracking server running. Waiting for requests...
```

**Laptop A (Client) - Terminal 1:**
```bash
$ python -m gr00t_wbc.control.main.teleop.run_g1_control_loop --interface sim
```

**Laptop A (Client) - Terminal 3:**
```bash
$ python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body_control_device pico \
    --hand_control_device pico_hand_tracking \
    --hand_tracking_server_host 192.168.1.100 \
    --hand_tracking_server_port 5557

Connecting to Pico hand tracking server at 192.168.1.100:5557...
Connected to Pico hand tracking server
...
```

---

For local setup (same machine), see `SETUP_PICO_HAND_TRACKING.md`

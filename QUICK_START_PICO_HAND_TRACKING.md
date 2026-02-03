# Quick Start: Dual Pico Hand Tracking

## 🚀 Quick Commands

### Terminal 1: Control Loop
```bash
python -m gr00t_wbc.control.main.teleop.run_g1_control_loop --interface sim
```

### Terminal 2: Hand Tracking Server (Pico #2)
```bash
python scripts/run_pico_hand_tracking_server.py
```

### Terminal 3: Teleop Policy (Pico #1 + Server)
```bash
python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body_control_device pico \
    --hand_control_device pico_hand_tracking
```

---

## 📋 What Each Terminal Does

| Terminal | Purpose | Device |
|----------|---------|--------|
| Terminal 1 | Control Loop | Robot control |
| Terminal 2 | Hand Tracking Server | Pico #2 (hands only) |
| Terminal 3 | Teleop Policy | Pico #1 (arms/body) + Server (hands) |

---

## ⚙️ Advanced Options

### Custom Server Port
```bash
# Server
python scripts/run_pico_hand_tracking_server.py --port 5558

# Client
python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body_control_device pico \
    --hand_control_device pico_hand_tracking \
    --hand_tracking_server_port 5558
```

### Remote Server
```bash
# Client (connecting to remote server)
python -m gr00t_wbc.control.main.teleop.run_teleop_policy_loop \
    --body_control_device pico \
    --hand_control_device pico_hand_tracking \
    --hand_tracking_server_host 192.168.1.100 \
    --hand_tracking_server_port 5557
```

---

## 🔍 Troubleshooting

**Server not connecting?**
- Make sure Terminal 2 is running first
- Check port matches in both server and client

**Hand tracking not working?**
- Verify Pico #2 has hand tracking enabled
- Check server terminal for errors

**Connection timeout?**
- Verify server is running: `lsof -i :5557`
- Check firewall if using remote host

---

For detailed setup, see `SETUP_PICO_HAND_TRACKING.md`

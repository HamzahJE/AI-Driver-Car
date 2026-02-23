# AI Driver Car

An autonomous driving robot with a **hybrid architecture**: a **Raspberry Pi Zero 2 W** uses a camera + **Azure OpenAI Vision LLM** to decide the general direction (navigate), while an **Arduino** with **3 ultrasonic sensors** handles real-time obstacle avoidance and smooth motor control (drive).

**LLM = Navigator** (slow, smart) — "go left, there's a gap"  
**Arduino + Sensors = Driver** (fast, reactive) — smooth steering, proportional speed, wall avoidance

---

## System Architecture

```
┌─────────────┐   rpicam-still   ┌──────────────────────────┐
│  Pi Camera   │ ──────────────► │   Raspberry Pi Zero 2 W   │
│  Module      │                 │                            │
└─────────────┘                  │  1. Capture image          │
                                 │  2. Send to Azure OpenAI   │
                                 │  3. Get goal: F/B/L/R/S    │
                                 │  4. Send goal over serial  │
                                 │                            │
                                 │  (repeats every ~2-4s)     │
                                 └────────────┬───────────────┘
                                              │ USB Serial (115200)
                                              ▼
┌──────────┐               ┌──────────────────────────────────────┐
│ HC-SR04  │──── Front ───►│             Arduino                   │
│ HC-SR04  │──── Left  ───►│                                       │
│ HC-SR04  │──── Right ───►│  • Reads sensors every 50ms           │
└──────────┘               │  • Receives GOAL direction from Pi    │
                           │  • Drives smoothly toward goal        │
                           │  • Auto-avoids walls (proportional)   │
                           │  • Emergency stop if < 10cm           │
                           │  • Sends sensor data back to Pi       │
                           └──────────┬───────────┬────────────────┘
                                      │           │
                                 ┌────┘           └────┐
                                 ▼                     ▼
                            Left Motor           Right Motor
                          (Pins 9, 10)           (Pins 5, 6)
```

## How It Works — Two Control Loops

```
SLOW LOOP (Pi — every ~2-4 seconds):
┌──────────┐    ┌───────────┐    ┌────────────┐    ┌────────────┐
│  Capture  │───►│  Base64   │───►│  Azure     │───►│  Send goal │
│  image    │    │  encode   │    │  OpenAI    │    │  F/B/L/R/S │
└──────────┘    └───────────┘    │  Vision    │    │  to Arduino│
                                 └────────────┘    └────────────┘

FAST LOOP (Arduino — every 50ms):
┌──────────────┐    ┌───────────────┐    ┌──────────────────────────┐
│  Read 3      │───►│  Current goal │───►│  Calculate motor speeds  │
│  ultrasonic  │    │  from Pi      │    │  • Slow near walls       │
│  sensors     │    │  (F/B/L/R/S)  │    │  • Veer away from sides  │
└──────────────┘    └───────────────┘    │  • Stop if blocked       │
                                         └──────────────────────────┘
```

The car drives **continuously and smoothly**. The LLM just updates the goal direction — the Arduino handles all the real-time driving.

---

## Serial Protocol

### Pi → Arduino (Goal commands)

| Command | Meaning                  |
|---------|--------------------------|
| `F`     | Drive forward            |
| `B`     | Drive backward           |
| `L`     | Turn left                |
| `R`     | Turn right               |
| `S`     | Stop                     |
| `T`     | Run self-test sequence   |

Arduino replies `A` (ACK) or `E` (error).

### Arduino → Pi (Sensor telemetry)

```
D:45
```
Format: `D:<front_cm>` — sent every 50ms.

Baud rate: **115200**

---

## Smart Driving Behaviour

| Situation | Arduino Action |
|-----------|---------------|
| Goal is F, path is clear | Drive forward at full speed |
| Goal is F, wall 30cm ahead | Slow down proportionally |
| Goal is F, wall 10cm ahead | Emergency stop |
| Goal is L | Spin left at turn speed |
| Goal is R | Spin right at turn speed |
| Any goal, obstacle < 10cm | Emergency stop regardless |

---

## Hardware Requirements

| Component               | Details                           |
|-------------------------|-----------------------------------|
| Raspberry Pi Zero 2 W   | Runs Python, captures images      |
| Pi Camera Module         | CSI-connected, uses `rpicam-still`|
| Arduino (Uno/Nano/etc.) | Smart motor controller + sensors  |
| 1 x HC-SR04 Ultrasonic  | Front distance sensor              |
| L9110S Motor Driver      | Drives 2 DC motors                |
| 2 x DC Motors           | Car drivetrain                    |
| USB Cable               | Pi ↔ Arduino serial link          |
| Power supply            | Battery pack for motors + boards  |

### Arduino Pin Wiring

| Arduino Pin | Function              |
|-------------|-----------------------|
| 9           | Left Motor Pin A      |
| 10          | Left Motor Pin B      |
| 5           | Right Motor Pin A     |
| 6           | Right Motor Pin B     |
| 7           | Front Ultrasonic TRIG |
| 8           | Front Ultrasonic ECHO |

### HC-SR04 Wiring (each sensor)

| HC-SR04 Pin | Connect To         |
|-------------|--------------------|
| VCC         | 5V                 |
| GND         | GND                |
| TRIG        | Arduino TRIG pin   |
| ECHO        | Arduino ECHO pin   |

---

## Project Structure

```
AI-Driver-Car/
├── main.py                              # Pi: capture → LLM → send goal to Arduino
├── .env                                 # API keys (not committed)
├── readme.md
├── modules/
│   ├── cam.py                           # Image capture via rpicam-still
│   ├── openai_vision.py                 # Azure OpenAI Vision — returns F/B/L/R/S
│   └── arduino_motorControl_Serial/
│       └── arduino_motorControl_Serial.ino  # Arduino: sensors + smart motor control
└── images/
    └── image.jpg                        # Latest captured frame (auto-generated)
```

---

## Quick Start Guide

### 1. Prerequisites

- Python 3.9+ on the Pi
- `rpicam-still` available (comes with Raspberry Pi OS)
- Arduino IDE (to flash the Arduino)
- An Azure OpenAI resource with a Vision-capable model deployed
- 1 x HC-SR04 ultrasonic sensor (front-facing) wired up (see pin table above)

### 2. Flash the Arduino

1. Open `modules/arduino_motorControl_Serial/arduino_motorControl_Serial.ino` in the Arduino IDE.
2. Select your board and port.
3. Upload.
4. **Test standalone:** Open Serial Monitor at **115200 baud**, send `T` — the car will test each direction for ~1 second while printing sensor readings. It respects obstacles during the test.

### 3. Set Up the Raspberry Pi

```bash
# Clone the repo
git clone <your-repo-url> ~/AI-Driver-Car
cd ~/AI-Driver-Car

# Create a virtual environment and install dependencies
python3 -m venv myenv
source myenv/bin/activate
pip install openai python-dotenv pyserial
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your-azure-openai-key
OPENAI_API_BASE=https://your-resource.openai.azure.com/
OPENAI_ORGANIZATION=your-org-id
API_VERSION=2024-02-15-preview
MODEL=your-deployment-name
```

### 5. Test the Camera

```bash
python modules/cam.py
# Should print: Saved to /home/.../AI-Driver-Car/images/image.jpg
```

### 6. Test the LLM API (with a static image)

```bash
python modules/openai_vision.py images/image.jpg
# Should print: LLM says: F   (or B, L, R, S)
```

### 7. Test Sensors (no Pi needed)

1. Open Arduino Serial Monitor at 115200 baud.
2. Send `T` — watch sensor readings and motor responses.
3. Place your hand in front of each sensor to verify distances.

### 8. Run the Full System

1. Connect the Pi Camera module.
2. Plug the Arduino into the Pi via USB.
3. Find your serial port:
   ```bash
   ls /dev/ttyACM* /dev/ttyUSB*
   ```
4. Update `SERIAL_PORT` in `main.py` if it's not `/dev/ttyACM0`.
5. Launch:
   ```bash
   python main.py
   ```
6. Press **Ctrl-C** to stop (sends `S` to the Arduino before exiting).

### Expected Output

```
[serial] Connected to Arduino on /dev/ttyACM0 @ 115200
[main] Starting AI driving loop  (Ctrl-C to stop)
[main] Arduino handles real-time driving. Pi sends direction goals.

[cam] Capturing image...
[sensor] Front: 65cm
[llm] Asking for driving command...
[sensor] Front: 60cm
[llm] New goal: F
[arduino] ACK — goal set to 'F'
[sensor] Front: 35cm
[cam] Capturing image...
[sensor] Front: 22cm
[llm] New goal: R
[arduino] ACK — goal set to 'R'
...
```

---

## Tuning

These constants in the Arduino code can be adjusted:

| Constant | Default | Description |
|----------|---------|-------------|
| `STOP_DIST` | 10 cm | Emergency stop distance |
| `SLOW_DIST` | 30 cm | Start slowing down |
| `TURN_DIST` | 25 cm | Steer away from side wall |
| `BASE_SPEED` | 200 | Normal PWM speed (0-255) |
| `MIN_SPEED` | 80 | Minimum PWM (below this, motors stall) |
| `TURN_SPEED` | 180 | PWM during turns |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `SerialException: could not open port` | Check `ls /dev/ttyACM* /dev/ttyUSB*` and update `SERIAL_PORT` in `main.py` |
| `rpicam-still failed` | Ensure Pi Camera is enabled (`sudo raspi-config` → Interface → Camera) |
| Sensor reads 999 | Check wiring — VCC→5V, GND→GND, TRIG→pin 7, ECHO→pin 8 |
| Car doesn't move | `MIN_SPEED` might be too low for your motors — increase it |
| Car spins in circles | Left/right motors may be swapped — swap M1/M2 pin assignments |
| Arduino returns garbage instead of ACK | Startup message wasn't flushed — try unplugging/replugging USB |
| `OPENAI_API_KEY` error | Check your `.env` file exists with correct keys |
| LLM always returns `S` | Verify model deployment supports vision (image input) |

---

## License

MIT
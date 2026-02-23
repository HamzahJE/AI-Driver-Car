# AI Driver Car

An autonomous driving robot that uses a **Raspberry Pi Zero 2 W** to capture images, sends them to an **Azure OpenAI Vision LLM** for scene analysis, and relays single-character driving commands (`F`/`B`/`L`/`R`/`S`) to an **Arduino** over USB serial to control the car's motors.

---

## System Overview

```
┌─────────────┐    rpicam-still    ┌─────────────────┐
│  Pi Camera   │ ────────────────► │                   │
│  Module      │                   │  Raspberry Pi     │
└─────────────┘                    │  Zero 2 W         │
                                   │                   │
                                   │  1. Capture image │
                                   │  2. Send to LLM   │
                                   │  3. Get F/B/L/R/S │
                                   │  4. Send over      │
                                   │     serial         │
                                   └────────┬──────────┘
                                            │ USB Serial
                                            │ (115200 baud)
                                            ▼
                  ┌──────────────────────────────────────┐
                  │            Arduino                    │
                  │  Reads command char → drives motors   │
                  │  Replies 'A' (ACK) or 'E' (error)    │
                  └──────────┬───────────┬───────────────┘
                             │           │
                        ┌────┘           └────┐
                        ▼                     ▼
                   Left Motor            Right Motor
                   (Pins 9,10)           (Pins 5,6)
```

## Flow of a Single Loop Iteration

```
┌──────────────┐     ┌──────────────────┐     ┌────────────────┐     ┌──────────┐
│  rpicam-still │────►│  Base64-encode   │────►│  Azure OpenAI  │────►│  Parse   │
│  capture JPG  │     │  image           │     │  Vision API    │     │  F/B/L/R/S│
└──────────────┘     └──────────────────┘     └────────────────┘     └─────┬────┘
                                                                           │
                                              ┌────────────────┐           │
                                              │  Arduino ACKs  │◄──── Serial.write(cmd)
                                              │  with 'A'/'E'  │
                                              └────────────────┘
                                                      │
                                                      ▼
                                               Motors respond
```

**On any error** (camera failure, API timeout, unexpected LLM response), the Pi sends `S` (stop) to keep the car safe.

---

## Serial Command Protocol

| Command | Action            |
|---------|-------------------|
| `F`     | Move forward      |
| `B`     | Move backward     |
| `L`     | Turn left         |
| `R`     | Turn right        |
| `S`     | Stop              |
| `T`     | Run test sequence |

- Arduino replies `A` (acknowledged) or `E` (unrecognised command).  
- Baud rate: **115200**

---

## Hardware Requirements

| Component               | Details                           |
|-------------------------|-----------------------------------|
| Raspberry Pi Zero 2 W   | Runs Python, captures images      |
| Pi Camera Module         | CSI-connected, uses `rpicam-still`|
| Arduino (Uno/Nano/etc.) | Motor controller via serial       |
| L9110S Motor Driver      | Drives 2 DC motors                |
| 2 x DC Motors           | Car drivetrain                    |
| USB Cable               | Pi ↔ Arduino serial link          |
| Power supply            | Battery pack for motors + boards  |

### Arduino Pin Wiring

| Arduino Pin | Function          |
|-------------|-------------------|
| 9           | Left Motor Pin A  |
| 10          | Left Motor Pin B  |
| 5           | Right Motor Pin A |
| 6           | Right Motor Pin B |

---

## Project Structure

```
AI-Driver-Car/
├── main.py                              # Main loop: capture → LLM → serial
├── .env                                 # API keys (not committed)
├── readme.md
├── modules/
│   ├── cam.py                           # Image capture via rpicam-still
│   ├── openai_vision.py                 # Azure OpenAI Vision — returns F/B/L/R/S
│   └── arduino_motorControl_Serial/
│       └── arduino_motorControl_Serial.ino  # Arduino motor firmware
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

### 2. Flash the Arduino

1. Open `modules/arduino_motorControl_Serial/arduino_motorControl_Serial.ino` in the Arduino IDE.
2. Select your board and port.
3. Upload.
4. **Test standalone:** Open Serial Monitor at **115200 baud**, send `T` — the car should go forward, backward, left, right, then stop (1 second each).

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
# Capture a single image
python modules/cam.py
# Should print: Saved to /home/.../AI-Driver-Car/images/image.jpg
```

### 6. Test the LLM API (with a static image)

```bash
# Use any image — no Arduino or camera needed
python modules/openai_vision.py images/image.jpg
# Should print: LLM says: F   (or B, L, R, S)
```

This is useful for verifying your API keys and model deployment work before wiring everything up.

### 7. Run the Full System

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

[cam] Capturing image...
[llm] Asking for driving command...
[llm] Decision: F
[arduino] ACK for 'F'
[cam] Capturing image...
[llm] Asking for driving command...
[llm] Decision: L
[arduino] ACK for 'L'
...
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `SerialException: could not open port` | Check `ls /dev/ttyACM* /dev/ttyUSB*` and update `SERIAL_PORT` in `main.py` |
| `rpicam-still failed` | Ensure the Pi Camera is connected and enabled (`sudo raspi-config` → Interface → Camera) |
| Arduino returns garbage instead of ACK | The startup message wasn't flushed — this is handled automatically, but try unplugging/replugging USB |
| `OPENAI_API_KEY` error | Check your `.env` file exists in the project root with the correct keys |
| LLM always returns `S` | Check that the model deployment supports vision (image input) |

---

## License

MIT
import time
import sys
import os
import serial
from dotenv import load_dotenv

# Load environment variables once at startup
project_root = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(project_root, '.env'))

from modules.cam import capture_image
from modules.openai_vision import get_driving_command

# ============================================================================
# SERIAL CONFIG — adjust port to match your Pi's serial device
# ============================================================================
SERIAL_PORT = '/dev/ttyUSB0'   # Common for USB-connected Arduino on Pi
BAUD_RATE = 115200
LOOP_INTERVAL = 1.0            # Seconds between each capture-decide-send cycle


def open_serial(port=SERIAL_PORT, baud=BAUD_RATE):
    """Open serial connection to the Arduino."""
    ser = serial.Serial(port, baud, timeout=1)
    time.sleep(2)  # Wait for Arduino to reset after serial connection
    print(f"[serial] Connected to Arduino on {port} @ {baud}")
    return ser


def send_command(ser, command):
    """Send a single-character command (F/B/L/R/S) to the Arduino and wait for ACK."""
    ser.write(command.encode())
    time.sleep(0.05)
    ack = ser.read(1).decode(errors='ignore')
    if ack == 'A':
        print(f"[arduino] ACK for '{command}'")
    elif ack == 'E':
        print(f"[arduino] ERROR — unrecognised command '{command}'")
    else:
        print(f"[arduino] No response (got '{ack}')")


def main():
    """Main loop: capture → ask LLM → send direction to Arduino."""
    ser = open_serial()

    print("[main] Starting AI driving loop  (Ctrl-C to stop)\n")
    try:
        while True:
            # 1. Capture an image from the Pi camera
            print("[cam] Capturing image...")
            try:
                capture_image()
            except Exception as e:
                print(f"[cam] ERROR: {e} — sending S (stop)")
                send_command(ser, 'S')
                time.sleep(LOOP_INTERVAL)
                continue

            # 2. Ask LLM which direction to go
            print("[llm] Asking for driving command...")
            try:
                command = get_driving_command()  # returns one of F, B, L, R, S
            except Exception as e:
                print(f"[llm] ERROR: {e} — sending S (stop)")
                send_command(ser, 'S')
                time.sleep(LOOP_INTERVAL)
                continue

            # 3. Validate & send to Arduino
            if command in ('F', 'B', 'L', 'R', 'S'):
                print(f"[llm] Decision: {command}")
                send_command(ser, command)
            else:
                print(f"[llm] Unexpected response '{command}' — sending S (stop)")
                send_command(ser, 'S')

            time.sleep(LOOP_INTERVAL)

    except KeyboardInterrupt:
        print("\n[main] Stopping — sending S (stop)")
        send_command(ser, 'S')
        ser.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
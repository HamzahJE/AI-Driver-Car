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
SERIAL_PORT = '/dev/ttyACM0'   # Arduino on Pi
BAUD_RATE = 115200
MOVE_DURATION = 0.5            # Seconds to drive before stopping and re-evaluating


def open_serial(port=SERIAL_PORT, baud=BAUD_RATE):
    """Open serial connection to the Arduino."""
    ser = serial.Serial(port, baud, timeout=1)
    time.sleep(2)  # Wait for Arduino to reset after serial connection
    ser.reset_input_buffer()  # Flush the "Robot Ready..." startup message
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
    """Main loop: stop → capture → ask LLM → move briefly → repeat."""
    ser = open_serial()

    print("[main] Starting AI driving loop  (Ctrl-C to stop)")
    print(f"[main] Move duration: {MOVE_DURATION}s per command\n")
    try:
        while True:
            # 1. STOP the car while we think — prevents hitting walls
            send_command(ser, 'S')

            # 2. Capture an image while stationary
            print("[cam] Capturing image...")
            try:
                capture_image()
            except Exception as e:
                print(f"[cam] ERROR: {e} — staying stopped")
                continue

            # 3. Ask LLM which direction to go
            print("[llm] Asking for driving command...")
            try:
                command = get_driving_command()  # returns one of F, B, L, R, S
            except Exception as e:
                print(f"[llm] ERROR: {e} — staying stopped")
                continue

            # 4. Execute the command for a short burst, then loop back to stop
            if command in ('F', 'B', 'L', 'R', 'S'):
                print(f"[llm] Decision: {command}")
                send_command(ser, command)
                if command != 'S':
                    time.sleep(MOVE_DURATION)  # Drive for a brief moment
            else:
                print(f"[llm] Unexpected response '{command}' — staying stopped")

    except KeyboardInterrupt:
        print("\n[main] Stopping — sending S (stop)")
        send_command(ser, 'S')
        ser.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
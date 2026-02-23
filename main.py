import time
import sys
import os
import serial
import threading
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


def open_serial(port=SERIAL_PORT, baud=BAUD_RATE):
    """Open serial connection to the Arduino."""
    ser = serial.Serial(port, baud, timeout=1)
    time.sleep(2)  # Wait for Arduino to reset after serial connection
    ser.reset_input_buffer()  # Flush the "Robot Ready..." startup message
    print(f"[serial] Connected to Arduino on {port} @ {baud}")
    return ser


def send_goal(ser, goal):
    """Send a goal direction (F/B/L/R/S) to the Arduino."""
    ser.reset_input_buffer()  # Clear any queued sensor data before sending
    ser.write(goal.encode())
    time.sleep(0.05)
    ack = ser.read(1).decode(errors='ignore')
    if ack == 'A':
        print(f"[arduino] ACK — goal set to '{goal}'")
    elif ack == 'E':
        print(f"[arduino] ERROR — unrecognised command '{goal}'")
    else:
        print(f"[arduino] No ACK (got '{ack}')")


def sensor_logger(ser, stop_event):
    """Background thread: read and display sensor data from Arduino."""
    while not stop_event.is_set():
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode(errors='ignore').strip()
                if line.startswith('D:'):
                    # D:front_cm
                    print(f"[sensor] Front: {line[2:]}cm")
            else:
                time.sleep(0.02)
        except Exception:
            time.sleep(0.1)


def main():
    """Main loop: Arduino drives continuously, Pi sends updated direction goals."""
    ser = open_serial()

    # Start background sensor logging
    stop_event = threading.Event()
    sensor_thread = threading.Thread(target=sensor_logger, args=(ser, stop_event), daemon=True)
    sensor_thread.start()

    print("[main] Starting AI driving loop  (Ctrl-C to stop)")
    print("[main] Arduino handles real-time driving. Pi sends direction goals.\n")

    # Start with stop until first LLM decision
    send_goal(ser, 'S')

    try:
        while True:
            # 1. Capture image (Arduino keeps driving the current goal)
            print("[cam] Capturing image...")
            try:
                capture_image()
            except Exception as e:
                print(f"[cam] ERROR: {e} — setting goal to S")
                send_goal(ser, 'S')
                time.sleep(1)
                continue

            # 2. Ask LLM for direction (Arduino still driving)
            print("[llm] Asking for driving command...")
            try:
                goal = get_driving_command()
            except Exception as e:
                print(f"[llm] ERROR: {e} — setting goal to S")
                send_goal(ser, 'S')
                time.sleep(1)
                continue

            # 3. Update the Arduino's goal direction
            if goal in ('F', 'B', 'L', 'R', 'S'):
                print(f"[llm] New goal: {goal}")
                send_goal(ser, goal)
            else:
                print(f"[llm] Unexpected '{goal}' — setting goal to S")
                send_goal(ser, 'S')

    except KeyboardInterrupt:
        print("\n[main] Stopping...")
        send_goal(ser, 'S')
        stop_event.set()
        ser.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
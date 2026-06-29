import serial
import time
import queue
import threading

GESTURE_TO_COMMAND = {
    "Open_Palm": "<O>",
    "Closed_Fist": "<C>",
    "Thumb_Up": "<U>",
    "Thumb_Down": "<D>",
    "Pointing_Up": "<P>",
    "ILoveYou": "<L>",
}

# For my personal setup, the serial port is '/dev/tty.usbmodem2101'. You may need to change this based on your system.
SERIAL_PORT = '/dev/tty.usbmodem2101'
BAUD_RATE = 115200
MIN_CONFIDENCE_SCORE = 0.5

# Thread-safe hand-off between the main loop and the serial worker thread.
# The main loop only ever puts() onto this queue, so it never blocks on I/O.
_command_queue = queue.Queue()

# Only ever read/written from the main thread, so no lock needed.
_last_command_sent = None


def _serial_worker():
    """Runs on a background thread and owns the serial port for the whole session.

    The port is opened once (lazily, on the first command) so the one-time 2s
    Pico-reset wait happens here, off the main thread — the UI never freezes.
    """
    ser = None
    while True:
        command = _command_queue.get()  # blocks until a command is queued
        if command is None:  # sentinel: shut the worker down
            _command_queue.task_done()
            break
        try:
            if ser is None:
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                time.sleep(2)  # one-time wait for the Pico to reset after the port opens
            # Terminate with '\n' — the Pico reads with sys.stdin.readline(),
            # which blocks until it receives a newline.
            ser.write((command + "\n").encode())
            print(f"Sent command: {command}")
        except serial.SerialException as e:
            print(f"Error sending command '{command}': {e}")
            if ser is not None:
                ser.close()
            ser = None  # force a reconnect attempt on the next command
        finally:
            _command_queue.task_done()

    if ser is not None:
        ser.close()


# Start the worker once on import. daemon=True so it dies with the main program.
_worker_thread = threading.Thread(target=_serial_worker, daemon=True)
_worker_thread.start()


def send_command(gesture_name, confidence_score):
    """Queue a command for the background worker. Non-blocking — safe to call
    from the video loop every frame."""
    global _last_command_sent

    if confidence_score < MIN_CONFIDENCE_SCORE:
        return

    command = GESTURE_TO_COMMAND.get(gesture_name)
    if command is None:
        print(f"No command mapped for gesture '{gesture_name}'.")
        return

    # The main loop fires every frame; only queue when the gesture changes so we
    # don't flood the queue (and the Pico) with the same command repeatedly.
    if command == _last_command_sent:
        return
    _last_command_sent = command

    _command_queue.put(command)


def shutdown():
    """Optional: flush and stop the worker cleanly (e.g. in your loop's finally)."""
    _command_queue.put(None)
    _worker_thread.join(timeout=5)

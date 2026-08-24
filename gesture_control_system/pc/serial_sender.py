import serial
import time
import queue
import threading
import uuid
import logging
import re

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
_last_send_time = 0.0
_last_warning_time = 0.0  # Track the last time a warning was printed

#   tag = f"[{cmd}|{command_id}] "
TAG = re.compile(r"\[(?P<cmd>[^|]+)\|(?P<command_id>[^\]]+)\]\s*(?P<data>.*)$")

# While a gesture is held, re-send it this often (seconds) so holding produces
# steady output without flooding the Pico on every frame.
REPEAT_INTERVAL = 0.33

# Regular expression for the tag of the result of our check module calls. This is used to extract the command and command_id from the log messages. 

logger = logging.getLogger(__name__)

_command_queued_logger = logging.getLogger(f"{logger}.command_queue") # Logs commands queued for sending to the Pico
_ACK_protocol_reader_logger = logging.getLogger(f"{logger}.ack_protocol") # Logs ACK/NAK messages received from the Pico that reach the PC side
_ACK_protocol_writer_logger = logging.getLogger(f"{logger}.ack_protocol_reciever") # Logs ACK/NAK messages received on the Pico side that are sent back to the PC
_output_logger = logging.getLogger(f"{logger}.output") # Logs output from the Pico's check modules

# Capture INFO level logs and above for both loggers
_command_queued_logger.setLevel(logging.INFO) 
_ACK_protocol_reader_logger.setLevel(logging.INFO) 
_ACK_protocol_writer_logger.setLevel(logging.INFO)
_output_logger.setLevel(logging.INFO)

 # Open the log file in write mode to overwrite previous logs each time the script runs
_command_queue_file_handler = logging.FileHandler(
    "command_queue_info.log",
    mode = 'w')

_ACK_protocol_reader_file_handler = logging.FileHandler(
    "ack_protocol_reader_info.log",
    mode = 'w') 

_ACK_protocol__writer_file_handler = logging.FileHandler(
    "ack_protocol_writer_info.log",
    mode = 'w'
)

_output_logger_file_handler = logging.FileHandler(
    "output_info.log",
    mode = 'w'
)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

_command_queue_file_handler.setFormatter(formatter)
_ACK_protocol_reader_file_handler.setFormatter(formatter)
_ACK_protocol__writer_file_handler.setFormatter(formatter)
_output_logger_file_handler.setFormatter(formatter)

# Set the handlers for each logger instance
_command_queued_logger.addHandler(_command_queue_file_handler)
_ACK_protocol_reader_logger.addHandler(_ACK_protocol_reader_file_handler)
_ACK_protocol_writer_logger.addHandler(_ACK_protocol__writer_file_handler)
_output_logger.addHandler(_output_logger_file_handler)

# ACK (acknowledgement) protocol — telemetry only.
# Every command is sent as a 3-line payload (command, command_id, send
# timestamp). The Pico echoes the command_id and timestamp back in its reply so
# the PC can correlate each ACK/NAK with the exact command it sent:
#   ACK:<cmd>|<command_id>|<timestamp>   handled successfully
#   NAK:<cmd>|<command_id>|<timestamp>   rejected (unknown) or the action raised
# Sends are fire-and-forget: the writer never waits for these. A dedicated
# reader thread drains the replies and logs them, so a slow or lost ACK can
# never stall fresh gestures. This suits real-time control as a dropped command
# self-heals, because a held gesture re-sends every REPEAT_INTERVAL anyway.
ACK_PREFIX = "ACK:"
NAK_PREFIX = "NAK:"
# Field separator inside an ACK/NAK line. Chosen so it can't collide with any
# field: commands are "<X>", command_ids are UUIDv4s, and the timestamp only
# uses digits, '-', ' ' and ':'.
FIELD_SEP = "|"


def _parse_ack(line, prefix):
    """Split an ACK/NAK line into ``(cmd, command_id, timestamp)``.

    Missing trailing fields come back as empty strings so a truncated or
    older-format reply still logs cleanly instead of raising.
    """
    parts = line[len(prefix):].split(FIELD_SEP, 2)
    parts += [""] * (3 - len(parts))
    return parts[0], parts[1], parts[2]

# Shared serial port. The writer thread owns opening/reconnecting; the reader
# thread only reads. `_serial_lock` guards (re)assignment and open/close of
# `_ser` so the two threads never race on the handle itself as the actual
# read()/write() calls happen outside the lock (pyserial permits one concurrent
# reader and one writer on the same port).
_serial_lock = threading.Lock()
_ser = None
_shutdown = threading.Event()


def _open_port(): # only called from the writer thread, under the lock
    """Open the port and wait for the Pico to reset. Done off the main thread,
    so the UI never freezes regardless of when this runs. The short read timeout
    keeps the reader thread responsive to shutdown and reconnects."""
    s = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.5)
    time.sleep(2)  # wait for the Pico to reset after the port opens
    return s


def _ensure_open(): # only called from the writer thread
    """Return an open port, opening it under the lock if needed. Raises
    serial.SerialException if the open fails."""
    global _ser
    with _serial_lock:
        if _ser is None:
            _ser = _open_port()
        return _ser


def _drop_port(): # only called from the writer thread
    """Close and clear the shared port so the writer reopens it next command."""
    global _ser
    with _serial_lock:
        if _ser is not None:
            _ser.close()
        _ser = None


def _coalesce_latest(first):
    """Drain everything already queued behind `first` and return a
    ``(command, shutdown)`` pair.

    Holding a gesture enqueues the same command every REPEAT_INTERVAL. If the
    writer briefly falls behind (e.g. a reconnect) those pile up, so before
    sending we collapse the backlog to the newest command (latest gesture wins)
    — this bounds queue growth. A shutdown sentinel (None) anywhere in the
    backlog wins outright.
    """
    command = first
    shutdown = command is None
    while True:
        try:
            nxt = _command_queue.get_nowait() # non-blocking snatching of the next item in the queue
        except queue.Empty: # since there are no items in our queue, there is nothing to coalesce, so we break out of the loop
            break
        _command_queue.task_done() # the consumer thread is now finished with the item, so we mark it as done
        if nxt is None:
            shutdown = True # shutdown sentinel precedence
        else:
            command = nxt
    
    return (None, True) if shutdown else (command, False)


def _serial_reader(): # reads response from the serial port in a background thread
    """Background reader: continuously drains the Pico's replies and logs
    ACK/NAK. Sends are fire-and-forget, so the ACK is pure telemetry here; this
    thread never blocks the writer. A NAK (command rejected) is surfaced as a
    warning; plain sensor debug lines from the Pico are ignored. Draining also
    keeps the OS input buffer from filling up with the Pico's chatter.
    """
    buffer = ""
    while not _shutdown.is_set():
        with _serial_lock:
            ser = _ser
        if ser is None:
            time.sleep(0.1)  # writer hasn't opened the port yet
            continue
        try:
            # line = ser.readline().decode(errors="replace").strip()
            chunk = ser.read(ser.in_waiting or 1).decode(errors="replace")  # read all available bytes, or block for 1 byte
        except serial.SerialException:
            time.sleep(0.1)  # port died; the writer will reopen it
            continue
        if not chunk: # line is empty, which means a read timeout occurred
            continue  # read timeout — loop so we notice shutdown/reconnect
        buffer += chunk
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            recv_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            if line.startswith(ACK_PREFIX):
                cmd, command_id, sent_time = _parse_ack(line, ACK_PREFIX)
                print("Debug 0")
                _ACK_protocol_reader_logger.info(
                    "Message Summary: %s", f"ACK '{cmd}' id={command_id}; sent={sent_time}; recv={recv_time}"
                )

            elif line.startswith(NAK_PREFIX):
                cmd, command_id, sent_time = _parse_ack(line, NAK_PREFIX)
                print("Debug 1")
                _ACK_protocol_reader_logger.info(
                    "Message Summary: %s", f"NAK '{cmd}' rejected by Pico; id={command_id}; sent={sent_time}; recv={recv_time}"
                )
            else:
                has_match = TAG.match(line)
                if has_match:
                    cmd = has_match.group("cmd")
                    command_id = has_match.group("command_id")
                    data = has_match.group("data")
                    _output_logger.info("Message Summary: %s", f"Successful Read: [{cmd}|{command_id}] {data}")
                else:
                    _output_logger.error("Message Summary: %s", f"Unsuccessful Read: {line}")




def _serial_writer(): # writes to the serial port in a background thread
    """Owns the serial port and writes commands. Never blocks on the ACK
    replies are handled asynchronously by _serial_reader, so a slow or lost ACK
    can't stall fresh gestures. The port is opened once (lazily, on startup) so
    the one-time 2s Pico-reset wait happens off the main thread.
    """
    # Open at startup so the 2s reset wait overlaps with the rest of the
    # program coming up. The first real command then sends without that delay.
    try:
        _ensure_open()
    except serial.SerialException as e:
        # print(f"Error opening serial port: {e}")  # retry on the first command
        _ACK_protocol_writer_logger.error(
            "Message Summary: %s", f"Error opening serial port: {e}"
        )

    while True:
        first = _command_queue.get()  # blocks until a command is queued
        command, shutdown = _coalesce_latest(first)
        _command_queue.task_done()  # accounts for `first`
        if shutdown:  # sentinel: shut the worker down
            break
        try:
            ser = _ensure_open()  # (re)connect if the port isn't open
            # Send the command as a 3-line payload: command, command_id, send
            # timestamp — one field per line. Each line ends with '\n' because
            # the Pico reads with sys.stdin.readline(), which blocks until it
            # receives a newline. The Pico echoes the command_id and timestamp
            # back in its ACK/NAK so the reader can correlate the reply.
            command_uuid = str(uuid.uuid4())  # standard UUIDv4 command_id
            command_send_time_stamp = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime()
            )
            ser.write(
                f"{command}\n{command_uuid}\n{command_send_time_stamp}\n".encode()
            )
            _ACK_protocol_writer_logger.info(
                "Message Summary: %s", f"Sent command '{command}' with id={command_uuid} at {command_send_time_stamp}"
            )
            
        except serial.SerialException as e:
            # print(f"Error sending command '{command}': {e}")
            _ACK_protocol_writer_logger.error(
                "Message Summary: %s", f"Error sending command '{command}': {e}"
            )
            _drop_port()  # force a reconnect attempt on the next command

    _shutdown.set()  # stop the reader thread
    _drop_port() # clean up the port on shutdown

# All this module does is start the background threads and provide a simple send_command() API. 
# The main loop can call send_command() every frame without blocking on I/O, and the background 
# threads handle the serial port and ACK/NAK telemetry asynchronously.

# Start both threads once on import. daemon=True so they die with the main
# program even if shutdown() is never called.
_worker_thread = threading.Thread(target=_serial_writer, daemon=True)
_worker_thread.start()
_reader_thread = threading.Thread(target=_serial_reader, daemon=True)
_reader_thread.start()


def send_command(hand_side, gesture_name, confidence_score):
    """Queue a command for the background worker. Non-blocking — safe to call
    from the video loop every frame."""
    global _last_command_sent, _last_send_time, _last_warning_time

    if confidence_score < MIN_CONFIDENCE_SCORE:
        return

    now = time.monotonic()
    command = GESTURE_TO_COMMAND.get(gesture_name)
    if command is None:
        # 1 sec buffer
        if (now - _last_warning_time) > 1.0:
            _last_warning_time = now
        return

    # The main loop fires every frame. Send on gesture change, OR re-send a held
    # gesture every REPEAT_INTERVAL so holding produces steady output without
    # flooding the queue (and the Pico) with the same command on every frame.
    now = time.monotonic()
    if command == _last_command_sent and (now - _last_send_time) < REPEAT_INTERVAL:
        return
    _last_command_sent = command
    _last_send_time = now

    # NOTE: Log here for command queueing, not in the worker thread, so the log reflects the actual frame that queued the command, not when it was sent.
    _command_queued_logger.info("Queue Sent: %s",f"Command Queued'{command}' for gesture '{gesture_name}' with confidence {confidence_score:.2f} on hand '{hand_side}'.")
    _command_queue.put(command)


def shutdown():
    """Optional: flush and stop the worker cleanly (e.g. in your loop's finally)."""
    _command_queue.put(None)
    _worker_thread.join(timeout=5)
    _shutdown.set()
    _reader_thread.join(timeout=2)
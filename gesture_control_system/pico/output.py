import time
import sys

_out_queue = []  # queue of strings to send to the sender
_debug_buffer = []  # buffer of strings to send to the sender
# _out_lock = _thread.allocate_lock()  # protects _out_queue
# _drain_started = False
_last_print_time = 0  # timestamp of the last print, used for throttling
PRINT_THROTTLE_MS = 100  # minimum time between prints in milliseconds


def buffer_log(msg):
    """Buffer a string to write. Debug/sensor output is throttled globally
    across all callers so bursts from multiple check_* modules don't
    collectively overwhelm a single drain cycle."""
    # with _out_lock:
    _debug_buffer.append(msg+"\n")

def drain_debug_buffer():
    """Drains _debug_buffer to sys.stdout immediately. This is used for debug output that must be sent to the sender without delay."""
    global _debug_buffer
    if _debug_buffer:
        sys.stdout.write("".join(_debug_buffer))
        if hasattr(sys.stdout, "flush"):
            sys.stdout.flush()
        _debug_buffer = []

def merge_debug_buffer():
    """Merges _debug_buffer to the end of the _out_queue and clears the _debug_buffer. 
    This is used to ensure that the debug output is sent to the sender in a timely manner, 
    without overwhelming the sender with too much output at once.
    """
    global _debug_buffer, _out_queue
    if _debug_buffer:
        _out_queue.extend(_debug_buffer)
        _debug_buffer = []

def queue_print(msg, throttle=True):
    """Queue a string to write. Debug/sensor output is throttled globally
    across all callers so bursts from multiple check_* modules don't
    collectively overwhelm a single drain cycle. Pass throttle=False for
    output that must never be dropped (e.g. ACK/NAK replies)."""
    # with _out_lock:
    global _last_print_time
    now = time.time() * 1000  # current time in milliseconds
    if throttle and (now - _last_print_time < PRINT_THROTTLE_MS):
        return
    _last_print_time = now
    _out_queue.append(msg+"\n")

def drain_now():
    """
    Drains _output_queue to sys.stdout immediately. This is used for ACK/NAK 
    messages that must be sent to the sender without delay.
    """
    global _out_queue
    if _out_queue:
        sys.stdout.write("".join(_out_queue))

        if hasattr(sys.stdout, "flush"):
            sys.stdout.flush()
        _out_queue = []
import sys
import check_acceleration as cacc
import check_angle as cang
import check_shake as cshk
import check_tapped as ctap

from output import queue_print, drain_now, buffer_log, merge_debug_buffer, drain_debug_buffer

actions = {
    "<O>": cacc.print_acceleration, # Open palm
    "<C>": cang.print_angle, # Closed fist
    "<U>": cshk.print_shake, # Thumb up
    "<D>": ctap.print_tapped, # Thumb down
    "<P>": cang.print_tilt_direction, # Point Up
    "<L>": cacc.print_acceleration_magnitude, # Love Sign (bit of a stretch)
}

# ACK protocol shared with the PC-side serial_sender. Each command arrives as a
# 3-line payload (command, command_id, send timestamp); the reply echoes the
# command_id and timestamp back so the sender can correlate it. The reply is
# always the LAST line emitted for a command, so the sender can skip the sensor
# debug output an action prints and match on these prefixes:
#   ACK:<cmd>|<command_id>|<timestamp>  handled successfully
#   NAK:<cmd>|<command_id>|<timestamp>  unknown command, or the action raised
ACK_PREFIX = "ACK:"
NAK_PREFIX = "NAK:"
FIELD_SEP = "|"  # separates cmd|command_id|timestamp; must match serial_sender


DUMP_EVERY_N_COMMANDS = 3
_commands_since_dump = 0

# TODO: Write back to pc in similar format as recieved, not as plain text
def _reply(prefix, cmd, command_id, timestamp):
    # sys.stdout.write(
    #     prefix + FIELD_SEP.join((cmd, command_id, timestamp)) + "\n"
    # )
    queue_print(prefix + FIELD_SEP.join((cmd, command_id, timestamp)) + "\n", throttle=False)

"""
_handle_command will drain every ACK/NAK message to the sender immediately, and will also drain the debug buffer every DUMP_EVERY_N_COMMANDS commands. 
This is to ensure that the sender receives the ACK/NAK messages in a timely manner, and that the debug buffer does not grow too large.
"""
def _handle_command(cmd, command_id, timestamp):
    global _commands_since_dump
    action = actions.get(cmd)
    if action is None:
        _reply(NAK_PREFIX, cmd, command_id, timestamp)
        drain_now()  # flush the output queue to the sender immediately
        return
    try:
        action(cmd, command_id)
    except Exception as e:
        # Report the failure instead of dying — one bad sensor read shouldn't
        # take the receiver loop down, and the sender needs a reply either way.
        queue_print(f"Action for {cmd} failed: {e}\n", throttle=False)
        _reply(NAK_PREFIX, cmd, command_id, timestamp)
        drain_now()
        return
    _reply(ACK_PREFIX, cmd, command_id, timestamp)

    _commands_since_dump += 1
    if _commands_since_dump >= DUMP_EVERY_N_COMMANDS:
        # merge_debug_buffer()
        # drain_now()
        drain_debug_buffer()
        _commands_since_dump = 0

    drain_now()  # flush remaining ACK messages and debug to the sender immediately

print("Receiver is ready. Waiting for commands...")

while True:
    cmd = sys.stdin.readline().strip()
    if not cmd:
        continue  # ignore blank lines between payloads
    # A command is followed by its command_id and send timestamp, one per line.
    command_id = sys.stdin.readline().strip()
    timestamp = sys.stdin.readline().strip()
    _handle_command(cmd, command_id, timestamp)
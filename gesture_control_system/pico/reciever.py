import sys
import check_acceleration as cacc
import check_angle as cang
import check_shake as cshk
import check_tapped as ctap

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


def _reply(prefix, cmd, command_id, timestamp):
    sys.stdout.write(
        prefix + FIELD_SEP.join((cmd, command_id, timestamp)) + "\n"
    )


def handle_command(cmd, command_id, timestamp):
    action = actions.get(cmd)
    if action is None:
        _reply(NAK_PREFIX, cmd, command_id, timestamp)
        return
    try:
        action()
    except Exception as e:
        # Report the failure instead of dying — one bad sensor read shouldn't
        # take the receiver loop down, and the sender needs a reply either way.
        print("Action for {} failed: {}".format(cmd, e))
        _reply(NAK_PREFIX, cmd, command_id, timestamp)
        return
    _reply(ACK_PREFIX, cmd, command_id, timestamp)

print("Receiver is ready. Waiting for commands...")

while True:
    cmd = sys.stdin.readline().strip()
    if not cmd:
        continue  # ignore blank lines between payloads
    # A command is followed by its command_id and send timestamp, one per line.
    command_id = sys.stdin.readline().strip()
    timestamp = sys.stdin.readline().strip()
    handle_command(cmd, command_id, timestamp)
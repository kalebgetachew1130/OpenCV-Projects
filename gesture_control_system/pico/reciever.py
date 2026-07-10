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

# ACK protocol shared with the PC-side serial_sender. The reply is always the
# LAST line emitted for a command, so the sender can skip the sensor debug
# output an action prints and match on these prefixes:
#   ACK:<cmd>  handled successfully
#   NAK:<cmd>  unknown command, or the action raised
ACK_PREFIX = "ACK:"
NAK_PREFIX = "NAK:"


def handle_command(cmd):
    action = actions.get(cmd)
    if action is None:
        sys.stdout.write(NAK_PREFIX + cmd + "\n")
        return
    try:
        action()
    except Exception as e:
        # Report the failure instead of dying — one bad sensor read shouldn't
        # take the receiver loop down, and the sender needs a reply either way.
        print("Action for {} failed: {}".format(cmd, e))
        sys.stdout.write(NAK_PREFIX + cmd + "\n")
        return
    sys.stdout.write(ACK_PREFIX + cmd + "\n")

print("Receiver is ready. Waiting for commands...")

while True:
    data = sys.stdin.readline().strip()
    if data:
        handle_command(data)
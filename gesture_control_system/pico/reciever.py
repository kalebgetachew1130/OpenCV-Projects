import sys
import check_acceleration as cacc
import check_angle as cang
import check_shake as cshk
import check_tapped as ctap

actions = {
    "<O>": cacc.print_acceleration,
    "<C>": cang.print_angle,
    "<U>": cshk.print_shake,
    "<D>": ctap.print_tapped,
    "<P>": cang.print_tilt_direction, #check if we are facing up or down, i.e., negative angle (angle)
    "<L>": cacc.print_acceleration_magnitude, #check magnitude of acceleration (acceleration)
}

def handle_command(cmd):
    if cmd in actions:
        actions[cmd]()
        sys.stdout.write(f"confirmed:{cmd}\n")
    else:
        sys.stdout.write("unknown\n")

print("Receiver is ready. Waiting for commands...")

while True:
    data = sys.stdin.readline().strip()
    if data:
        handle_command(data)
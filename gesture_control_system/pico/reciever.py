import sys
import check_acceleration as cacc
import check_angle as cang
import check_shake as cshk
import check_tapped as ctap

actions = {
    "<O>": cacc.print_acceleration,
    "<C>": cang.print_angle,
    "<U>": lambda: print("thumb up action"),
    "<D>": lambda: print("thumb down action"),
    "<P>": cshk.print_shake,
    "<L>": ctap.print_tapped,
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
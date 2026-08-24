from sensor import motion
from output import buffer_log

# Configure tap detection once when the module is imported
motion.set_tap(1, threshold=30)
# @param 1: number of taps needed to set motion.tapped to True (1 = single, 2 = double)
# @param threshold: force needed to register a tap (in newtons)


def print_tapped(cmd = None, command_id = None):
    # Check the tap flag once, print the result, and return it
    tag = f"[{cmd}|{command_id}] " if cmd and command_id else ""
    if motion.tapped:
        buffer_log(f"{tag}tapped")
        return True

    buffer_log(f"{tag}not tapped")
    return False

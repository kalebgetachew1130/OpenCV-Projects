from sensor import motion
from output import buffer_log

def print_shake(cmd = None, command_id = None):
    # Check for a shake once, print the result, and return it
    tag = f"[{cmd}|{command_id}] " if cmd and command_id else ""
    if motion.shake(threshold=12):
        buffer_log(f"{tag}shaken")
        return True

    buffer_log(f"{tag}still")
    return False

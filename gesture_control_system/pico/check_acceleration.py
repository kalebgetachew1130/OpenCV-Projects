from sensor import motion
from output import buffer_log

def print_acceleration(cmd = None, command_id = None):
    # Take a single reading, print it once, and return it
    x, y, z = motion.acceleration
    x = round(x, 2)
    y = round(y, 2)
    z = round(z, 2)

    tag = f"[{cmd}|{command_id}] " if cmd and command_id else ""
    buffer_log(f"{tag}x:{x}|y:{y}|z:{z}")
    return x, y, z

def print_acceleration_magnitude(cmd = None, command_id = None):
    x, y, z = motion.acceleration
    magnitude = (x**2 + y**2 + z**2) ** 0.5
    magnitude = round(magnitude, 2)

    tag = f"[{cmd}|{command_id}] " if cmd and command_id else ""
    buffer_log(f"{tag}Acceleration Magnitude: {magnitude}")
    return magnitude
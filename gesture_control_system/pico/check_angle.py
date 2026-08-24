from sensor import motion
from output import buffer_log



def print_angle(cmd = None, command_id = None):
    x, y, z = motion.angle
    tag = f"[{cmd}|{command_id}] " if cmd and command_id else ""
    buffer_log(f"{tag}Angle (y): {round(y, 2)}")
    return y

# #Prints Up if the angle is postive, Down if the angle is negative, and Level if the angle is 0
def print_tilt_direction(cmd = None, command_id = None):
    x, y, z = motion.angle
    tag = f"[{cmd}|{command_id}] " if cmd and command_id else ""
    if y > 0:
        buffer_log(f"{tag}Up")
        return "Up"
    elif y < 0:
        buffer_log(f"{tag}Down")
        return "Down"
    else:
        buffer_log(f"{tag}Level")
        return "Level"
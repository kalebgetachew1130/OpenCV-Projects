from sensor import motion


def print_angle():
    # Read the tilt angle once, print it, and return it
    x, y, z = motion.angle
    print("Angle: {:.0f}".format(y))
    return y

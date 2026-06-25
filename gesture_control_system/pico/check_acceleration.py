from sensor import motion


def print_acceleration():
    # Take a single reading, print it once, and return it
    x, y, z = motion.acceleration
    x = round(x, 2)
    y = round(y, 2)
    z = round(z, 2)

    print(x, y, z)
    return x, y, z

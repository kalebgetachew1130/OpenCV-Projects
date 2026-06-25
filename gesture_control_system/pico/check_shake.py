from sensor import motion


def print_shake():
    # Check for a shake once, print the result, and return it
    if motion.shake(threshold=12):
        print("shaken")
        return True

    print("still")
    return False

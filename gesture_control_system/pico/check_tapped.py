from sensor import motion

# Configure tap detection once when the module is imported
motion.set_tap(1, threshold=30)
# @param 1: number of taps needed to set motion.tapped to True (1 = single, 2 = double)
# @param threshold: force needed to register a tap (in newtons)


def print_tapped():
    # Check the tap flag once, print the result, and return it
    if motion.tapped:
        print("tapped")
        return True

    print("not tapped")
    return False

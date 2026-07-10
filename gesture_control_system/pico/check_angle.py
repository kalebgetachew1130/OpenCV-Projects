from sensor import motion



def print_angle():
    x, y, z = motion.angle
    # Read the tilt angle once, print it, and return it
    # For some reason the numbers here aren't changing
    print("x: {:.0f}".format(x))
    print("z: {:.0f}".format(z))
    print("Angle (y): {:.0f}".format(y))
    return y

# #Prints Up if the angle is postive, Down if the angle is negative, and Level if the angle is 0
def print_tilt_direction():
    x, y, z = motion.angle
    if y > 0:
        print("Up")
        return "Up"
    elif y < 0:
        print("Down")
        return "Down"
    else:
        print("Level")
        return "Level"
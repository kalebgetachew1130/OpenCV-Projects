from sensor import motion

x, y, z = motion.angle

def print_angle():
    # Read the tilt angle once, print it, and return it
    print("Angle: {:.0f}".format(y))
    return y

# #Prints Up if the angle is postive, Down if the angle is negative, and Level if the angle is 0
def print_tilt_direction():
    if y > 0:
        print("Up")
        return "Up"
    elif y < 0:
        print("Down")
        return "Down"
    else:
        print("Level")
        return "Level"
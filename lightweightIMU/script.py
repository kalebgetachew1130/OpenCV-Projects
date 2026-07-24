import serial


# this will be device specific, works using my Mac
PORT = '/dev/tty.usbserial-10'       # replace with your actual port
BAUD = 115200

# hardware parameters
GYRO_NOISE_THRESHOLD = 50
ACCEL_NOISE_THRESHOLD = 50

ser = serial.Serial(PORT, BAUD)

while True:
    line = ser.readline().decode('utf-8', errors='ignore').strip()

    data = line.split(',')

    if line:
        print("accel X: ", data[3])
        print("accel Y: ", data[4])
        print("accel Z: ", data[5])
        print("      ")
        print("gyro X: ", data[0])
        print("gyro Y: ", data[1])
        print("gyro Z: ", data[2])
        print("\n")




# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press ⌘F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

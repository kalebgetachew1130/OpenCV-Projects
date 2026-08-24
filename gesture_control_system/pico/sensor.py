from machine import Pin
from PiicoDev_LIS3DH import PiicoDev_LIS3DH

# Shared accelerometer instance — initialized once and imported by every check_* module
motion = PiicoDev_LIS3DH(bus=0, sda=Pin(16), scl=Pin(17), address=0x18)
motion.range = 2  # Set accelerometer range to ±2g
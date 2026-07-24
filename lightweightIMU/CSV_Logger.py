import serial
import csv
import time

PORT = '/dev/tty.usbserial-10'
BAUD = 115200
OUTPUT_FILE = 'imu_data.csv'

ser = serial.Serial(PORT, BAUD)
time.sleep(2)  # give the Arduino a moment to reset and stabilize

with open(OUTPUT_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'gyro_x', 'gyro_y', 'gyro_z', 'accel_x', 'accel_y', 'accel_z'])

    print(f"Logging to {OUTPUT_FILE}... press Ctrl+C to stop")

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                values = line.split(',')
                if len(values) == 6:
                    writer.writerow([time.time()] + values)
    except KeyboardInterrupt:
        print("\nStopped logging.")
    finally:
        ser.close()
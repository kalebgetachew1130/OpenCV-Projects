from machine import I2C, Pin

i2c = I2C(0, sda=Pin(16), scl=Pin(17), freq=400000)

# Try common accelerometer identification registers
tests = [
    ("LIS3DH", 0x0F, 0x33),
    ("MPU6050", 0x75, 0x68),
    ("ADXL345", 0x00, 0xE5),
    ("MMA8452Q", 0x0D, 0x2A),
]

print("Testing device at 0x18:")
for name, reg, expected_id in tests:
    try:
        data = i2c.readfrom_mem(0x18, reg, 1)
        print(f"  {name}: Register 0x{reg:02x} = 0x{data[0]:02x} (expected 0x{expected_id:02x}) {'✓ MATCH!' if data[0] == expected_id else ''}")
    except Exception as e:
        print(f"  {name}: Register 0x{reg:02x} - Error: {e}")
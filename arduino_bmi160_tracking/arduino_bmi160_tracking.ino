#include <BMI160Gen.h>
#include <Wire.h>

const int i2c_addr = 0x68; // Default I2C address for BMI160 [cite: 2]
const int calibButtonPin = 2; // Connect a button between Pin 2 and GND

// Kinematic variables
float vx = 0, vy = 0, vz = 0;
float px = 0, py = 0, pz = 0;
float ax_offset = 0, ay_offset = 0, az_offset = 0;

unsigned long lastTime = 0;
bool needsCalibration = true;

void setup() {
  Serial.begin(9600);
  pinMode(calibButtonPin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(calibButtonPin), triggerCalibration, FALLING);

  Wire.begin();
  if (!BMI160.begin(BMI160GenClass::I2C_MODE, i2c_addr)) {
    Serial.println("BMI160 initialization failed!");
    while (1); 
  }
  Serial.println("BMI160 Initialized.");
  calibrateSensor();
}

void triggerCalibration() {
  needsCalibration = true;
}

void calibrateSensor() {
  Serial.println("Calibrating... Keep sensor still.");
  long sumX = 0, sumY = 0, sumZ = 0;
  int samples = 100;
  int ax, ay, az;
  
  for(int i = 0; i < samples; i++) {
    BMI160.readAccelerometer(ax, ay, az);
    sumX += ax; sumY += ay; sumZ += az;
    delay(10);
  }
  
  ax_offset = sumX / samples;
  ay_offset = sumY / samples;
  az_offset = (sumZ / samples) - 16384; // Assuming Z points down (1g)
  
  // Reset kinematic variables
  vx = vy = vz = 0;
  px = py = pz = 0;
  lastTime = millis();
  needsCalibration = false;
  Serial.println("Calibration complete.");
}

void loop() {
  if (needsCalibration) {
    calibrateSensor();
  }

  int ax_raw, ay_raw, az_raw;
  BMI160.readAccelerometer(ax_raw, ay_raw, az_raw);

  // Convert raw data to m/s^2
  float ax = ((ax_raw - ax_offset) / 16384.0) * 9.81;
  float ay = ((ay_raw - ay_offset) / 16384.0) * 9.81;
  float az = ((az_raw - az_offset) / 16384.0) * 9.81;

  // Calculate Delta Time in seconds
  unsigned long currentTime = millis();
  float dt = (currentTime - lastTime) / 1000.0;
  lastTime = currentTime;

  // Deadband filter to reduce drift from tiny noise
  if (abs(ax) < 0.1) ax = 0;
  if (abs(ay) < 0.1) ay = 0;
  if (abs(az) < 0.1) az = 0;

  // First Integration: Acceleration -> Velocity
  vx += ax * dt;
  vy += ay * dt;
  vz += az * dt;

  // Second Integration: Velocity -> Position
  px += vx * dt;
  py += vy * dt;
  pz += vz * dt;

  Serial.print("Position(m) X:"); Serial.print(px);
  Serial.print(" Y:"); Serial.print(py);
  Serial.print(" Z:"); Serial.println(pz);

  delay(50); 
}
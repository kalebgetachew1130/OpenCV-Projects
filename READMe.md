# Gesture Control System

## System Overview

Camera-based gesture control system that converts real-time hand motion into structured commands sent to a Raspberry Pi Pico, which executes actions and returns sensor feedback (accelerometer data). The system is closed-loop and latency-sensitive.

## High-Level Pipeline

```text
Camera Input
    ↓
OpenCV Frame Capture
    ↓
MediaPipe Hand Landmark Tracking
    ↓
Gesture Classification
    └─ Rule-based or ML mapping from landmarks → gesture label + confidence
    ↓
Gesture Processing (PC)
    ├─ Smoothing (frame buffer / majority vote)
    ├─ Debounce (N-frame confirmation)
    ├─ Confidence filtering
    └─ State machine (IDLE / CONTROL / LOCKED)
    ↓
Command Encoder
    ├─ Structured message creation (JSON or packet format)
    └─ Attach cmd_id, timestamp, and confidence
    ↓
Serial Communication Layer
    ├─ Non-blocking USB serial
    └─ Send command to Pico
    ↓
Raspberry Pi Pico Firmware
    ├─ Parse commands
    ├─ Execute actuator logic
    └─ Read accelerometer (IMU)
    ↓
Feedback Channel
    ├─ Pico sends sensor data back to the PC
    └─ Optional ACK and telemetry stream
    ↓
PC Logging & Visualization
    ├─ Overlay UI (gesture, FPS, confidence)
    ├─ Serial logs
    └─ Latency measurement
```

## Software Components

### OpenCV (Video System)
- Webcam capture
- Frame timing control
- Debug rendering (FPS, overlays)
- Latency measurement hooks

### MediaPipe (Perception Layer)
- Hand landmark extraction
- Gesture feature generation

### Gesture Logic Layer
- Temporal smoothing (moving average or exponential smoothing)
- Debounce requiring a stable gesture over *N* frames
- Confidence filtering
- State-machine control

### Serial Protocol Layer
- Structured messages such as `{"cmd":"...","id":n,"conf":x}`
- ACK support (recommended)
- Optional retry handling

### Pico Firmware
- Command parsing
- Actuator control
- Accelerometer readout
- Feedback transmission

## Key Design Features

- Real-time processing pipeline with a target latency below 100 ms
- Closed-loop feedback system (command ↔ sensor response)
- Noise-resistant gesture recognition through temporal smoothing
- State-based control to prevent accidental triggers
- Structured communication protocol rather than raw strings

## OpenCV Capabilities Used

- Real-time video capture
- Frame-by-frame inference pipeline
- Gesture overlay visualization
- Landmark tracking display
- Temporal buffering for smoothing
- Debounce logic for frame consistency
- Motion-jitter reduction via coordinate smoothing
- FPS and latency measurement

## Hardware Options for Testing

### Phase 1 — Logic Validation
- NeoPixel LED strip for visual state output

### Phase 2 — Simple Motion
- SG90 servo motor for gesture-to-angle mapping

### Phase 3 — Spatial Control
- Pan-tilt servo mount for two-axis gesture control

### Phase 4 — Mechatronics
- DC motor with an L298N driver for continuous motion control

### Phase 5 — Full System Test
- Robot car kit for gesture-driven navigation

### Optional Advanced Input
- Leap Motion Controller for high-precision hand tracking

## End-State Goal

A stable gesture-controlled robotics interface in which:

- Hand motion maps to deterministic commands
- The system is noise-resistant and state-driven
- Latency is predictable and low
- Hardware responds smoothly and reliably

## Running the Program

```bash
cd gesture_control_system
python3.12 -m tracker_templates.gesture_tracker
```
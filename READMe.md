GESTURE CONTROL SYSTEM – 1 PAGE ARCHITECTURE SPEC

==================================================
SYSTEM OVERVIEW
==================================================
Camera-based gesture control system that converts real-time hand motion into structured commands sent to a Raspberry Pi Pico, which executes actions and returns sensor feedback (accelerometer data). System is closed-loop and latency-sensitive.

==================================================
HIGH-LEVEL PIPELINE (Goal)
==================================================

[Camera Input]
    ↓
[OpenCV Frame Capture]
    ↓
[MediaPipe Hand Landmark Tracking]
    ↓
[Gesture Classification Layer]
    - rule-based or ML mapping from landmarks → gesture label + confidence
    ↓
[Gesture Processing Layer (PC)]
    - smoothing (frame buffer / majority vote)
    - debounce (N-frame confirmation)
    - confidence filtering
    - state machine (IDLE / CONTROL / LOCKED)
    ↓
[Command Encoder]
    - structured message creation (JSON or packet format)
    - attach cmd_id + timestamp + confidence
    ↓
[Serial Communication Layer]
    - non-blocking USB serial
    - send command to Pico
    ↓
[Raspberry Pi Pico Firmware]
    - parse commands
    - execute actuator logic
    - read accelerometer (IMU)
    ↓
[Feedback Channel]
    - Pico sends sensor data back to PC
    - optional ACK + telemetry stream
    ↓
[PC Logging / Visualization]
    - overlay UI (gesture, FPS, confidence)
    - serial logs
    - latency measurement

==================================================
SOFTWARE COMPONENTS
==================================================

1. OpenCV (Video System)
- webcam capture
- frame timing control
- debug rendering (FPS, overlays)
- latency measurement hooks

2. MediaPipe (Perception Layer)
- hand landmark extraction
- gesture feature input

3. Gesture Logic Layer (YOUR CODE)
- smoothing: moving average / exponential smoothing
- debounce: require stable gesture over N frames
- confidence filtering
- state machine control

4. Serial Protocol Layer
- structured messages:
  {"cmd": "...", "id": n, "conf": x}
- ACK support (recommended)
- retry handling (optional)

5. Pico Firmware
- command parser
- actuator control
- accelerometer readout
- feedback transmission

==================================================
KEY DESIGN FEATURES
==================================================

- Real-time processing pipeline (low latency <100ms target)
- Closed-loop feedback system (command ↔ sensor response)
- Noise-resistant gesture recognition via temporal smoothing
- State-based control system to prevent accidental triggers
- Structured communication protocol instead of raw strings

==================================================
OPEN-CV CAPABILITIES USED
==================================================

- real-time video capture
- frame-by-frame inference pipeline
- gesture overlay visualization
- landmark tracking display
- temporal buffering (smoothing input signals)
- debounce logic (frame consistency enforcement)
- motion jitter reduction (coordinate smoothing)
- FPS + latency measurement tools

==================================================
HARDWARE OPTIONS FOR TESTING
==================================================

PHASE 1 (LOGIC VALIDATION)
- LED strip (NeoPixels) → visual state output

PHASE 2 (SIMPLE MOTION)
- SG90 servo motor → gesture-to-angle mapping

PHASE 3 (SPATIAL CONTROL)
- Pan-tilt servo mount → 2-axis gesture control

PHASE 4 (MECHATRONICS)
- DC motor + L298N driver → continuous motion control

PHASE 5 (FULL SYSTEM TEST)
- Robot car kit → gesture-driven navigation system

OPTIONAL ADVANCED INPUT
- Leap Motion Controller → high precision hand tracking

==================================================
END STATE GOAL
==================================================

A stable gesture-controlled robotics interface where:
- hand motion → deterministic commands
- system is noise-resistant and state-driven
- latency is predictable and low
- hardware responds smoothly and reliably

- To run this program, cd into the gesture_control_system directory and run the following command: 
python3.12 -m tracker_templates.gesture_tracker
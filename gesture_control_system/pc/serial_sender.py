import serial 
import time

GESTURE_TO_COMMAND = {
    "Open_Palm": "<O>",
    "Closed_Fist": "<C>",
    "Thumb_Up": "<U>",
    "Thumb_Down": "<D>",
    "Pointing_Up": "<P>",
    "ILoveYou": "<L>",
}

MIN_CONFIDENCE_SCORE = 0.5
BAUD_RATE = 115200

last_command_sent = None

def send_command(gesture_name, confidence_score):
    global last_command_sent
    
    if confidence_score < MIN_CONFIDENCE_SCORE:
        print(f"Gesture '{gesture_name}' confidence {confidence_score:.2f} below threshold. Not sending command.")
        return

    command = GESTURE_TO_COMMAND.get(gesture_name)
    if command is None:
        print(f"No command mapped for gesture '{gesture_name}'.")
        return

    if command == last_command_sent:
        print(f"Command '{command}' already sent. Not sending again.")
        return

    try:
        print("Attempting to send command: ", command)
        last_command_sent = command
        # with serial.Serial('COM3', BAUD_RATE, timeout=1) as ser:
        #     time.sleep(2)  # Wait for the serial connection to initialize
        #     ser.write(command.encode())
        #     print(f"Sent command: {command}")
        #     last_command_sent = command
    except serial.SerialException as e:
        print(f"Error sending command '{command}': {e}")
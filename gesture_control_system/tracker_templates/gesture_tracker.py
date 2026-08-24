import cv2
import sys
import time
import select
import logging
import mediapipe as mp
from math import hypot
from pc.serial_sender import send_command, shutdown
from mediapipe.tasks.python import vision
from pprint import pprint

BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
GestureRecognizerResult = mp.tasks.vision.GestureRecognizerResult
VisionRunningMode = vision.RunningMode

#Variables for Frame rate
prevTime = 0
currTime = 0

# Tasks API — no mp.solutions, no mp.framework needed
HAND_CONNECTIONS = vision.HandLandmarksConnections.HAND_CONNECTIONS

# Set the number of hands to detect (1 or 2). Adjust as needed.
NUM_HANDS = 1

# Set the interval (in seconds) at which to log hand info. Adjust as needed.
REPEAT_INTERVAL = 0.33


_latest_result = None
_last_log_time = 0.0  # timestamp of the last log, used for throttling

hands_cord_data = {"Left": None, "Right": None}  # global dict to store landmark coordinates
hands_log_data = {"Left": None, "Right": None}    # global dict to store hand data

def gesture_print_result(result: GestureRecognizerResult, output_image: mp.Image, timestamp_ms: int):
    # This runs on a BACKGROUND THREAD — MediaPipe's LIVE_STREAM mode calls it
    # asynchronously whenever a frame finishes processing. It does NOT run in
    # lockstep with your main loop, which is why we stash the result in a global
    # rather than returning it—there's no caller to return to after the frame has been processed.
    """
    General Idea of what's going on:
    Main loop:    frame1 → frame2 → frame3 → frame4 → frame5 ...
    Background:        [processing frame1...]  → callback fires → [processing frame2...] → callback fires ...
    """
    global _latest_result
    _latest_result = result  #main loop picks this up on its next iteration

gesture_options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path='../task/gesture_recognizer.task'),
    num_hands = NUM_HANDS,
    running_mode=VisionRunningMode.LIVE_STREAM,
    result_callback=gesture_print_result)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Capture INFO level logs and above
file_handler = logging.FileHandler(
    "gesture_tracker_hand_info.log",
    mode = 'w') # Open the log file in write mode to overwrite previous logs each time the script runs
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

"""
console_quit_requested() uses select() to check if there's input waiting on stdin without 
blocking the video loop. If a line equal to q (or EOF [End of Life], e.g. Ctrl-C [Force Quit]) is found, it returns 
True and the loop breaks.
"""
def console_quit_requested():
    """Return True if 'q' (followed by Enter) was typed in the console."""
    while select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline()
        if not line:  # stdin closed (e.g. EOF)
            return True
        if line.strip().lower() == 'q':
            return True
    return False

# TODO: Replace print statements with logging (e.g., winston / python logging) at the INFO level.
def log_hand_info(print_landmarks_allowed=False):
    #Extract wanted information about the hand into a custom dictionary structure
    hand_summary = [
        {
            "hand_index": idx,
            
            "handedness": hand_list[0].category_name,
            "landmark_confidence": round(hand_list[0].score, 2),

            #Inner Loop: Extract specific coordinates from 'hand_landmarks'
            #[:2] slices the list to preview ONLY the first 2 points (Wrist & Thumb base)
            "landmarks_preview": [
                {
                    "point_id": i, 
                    "x": round(lm.x, 3), 
                    "y": round(lm.y, 3), 
                    "z": round(lm.z, 3)

                    #NOTE: x and y are normalized to [0,1] relative to the image dimensions, while z is a relative depth value (negative means closer to camera) in refrence to your wrist.
                    } 
                for i, lm in enumerate(_latest_result.hand_landmarks[idx])
                # Loop over every landmark for the current hand, using enumerate to get both the index (point_id) and the landmark data (lm)
            ],

            "gesture_preview" : [
                {
                    "category_name": gesture.category_name,
                    "confidence": round(gesture.score, 2)
                }
                for gesture in _latest_result.gestures[idx]
            ]
        }
        # Loop over each detected hand's handedness info, using the index to also access its landmarks
        for idx, hand_list in enumerate(_latest_result.handedness) 
    ]

    for hand in hand_summary:
        # gesture_entry = hand["gesture_preview"][0] if hand["gesture_preview"] else None
        # gestue_name = hand["gesture_preview"][0]["category_name"] if gesture_entry else "None"
        hand_side = hand["handedness"]
        hands_log_data[hand_side] = hand["landmarks_preview"]  # Update the global dict with the landmark coordinates for each hand

    logger.info("Hand Summary: %s", hand_summary)  # Log the structured hand summary to the log file



    # Print the structured Python list beautifully — only when at least one hand has
    # an actual recognized gesture. MediaPipe returns the literal string "None" (not
    # empty/falsy) for the category name when no gesture is detected, so check against that.
    if print_landmarks_allowed and any(
        hand["gesture_preview"] and hand["gesture_preview"][0]["category_name"] != "None"
        for hand in hand_summary
    ):
        pprint(hand_summary, sort_dicts=False)

def get_landmark_pixel_coordinates(image):
    """Convert normalized landmark coordinates to pixel coordinates."""
    h, w = image.shape[:2]  # pull pixel dimensions for denormalizing coords
    for idx, hand_list in enumerate(_latest_result.handedness):
        handedness = hand_list[0].category_name
        landmarks = _latest_result.hand_landmarks[idx]
        pixel_coords = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
        hands_cord_data[handedness] = pixel_coords # fills the global dict with the pixel coordinates for each hand

def draw_hand_landmarks(image, hand_landmarks):
    """Draw landmarks and connections directly with OpenCV."""
    h, w = image.shape[:2] # pull pixel dimensions for denormalizing coords

    # hand_landmarks is a list of NormalizedLandmark objects (x, y, z in 0-1 range)
    # HAND_CONNECTIONS is a list of Connection(start, end) pairs — index pairs into that list
    for connection in HAND_CONNECTIONS:
        start = hand_landmarks[connection.start]  # NormalizedLandmark at the start joint
        end = hand_landmarks[connection.end]       # NormalizedLandmark at the end joint
        x0, y0 = int(start.x * w), int(start.y * h)  # scale from 0-1 to actual pixels
        x1, y1 = int(end.x * w), int(end.y * h)
        cv2.line(image, (x0, y0), (x1, y1), (255, 0, 0), 2)  # draw bone

    # Draw landmark dots
    for lm in hand_landmarks:
        cx, cy = int(lm.x * w), int(lm.y * h) # lm.x and lm.y are normalized to [0,1], so multiply by image width/height to get pixel coordinates
        cv2.circle(image, (cx, cy), 4, (0, 255, 0), -1) # draw joint dot

if __name__ == "__main__":
    with GestureRecognizer.create_from_options(gesture_options) as recognizer:
        try:
            capturer = cv2.VideoCapture(0)
            while True:
                success, img = capturer.read()
                if not success:
                    print("Failed to capture video")
                    break

                rgb_frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

                timestamp_ms = int(time.time() * 1000)
                # Send live image data to perform gesture recognition.
                # The results are accessible via the `result_callback` provided in
                # the `GestureRecognizerOptions` object.
                # The gesture recognizer must be created with the live stream mode.
                recognizer.recognize_async(mp_image, timestamp_ms)

                if _latest_result is not None and len(_latest_result.handedness) > 0:

                    now = time.monotonic()
                    if (now - _last_log_time) > REPEAT_INTERVAL:
                        log_hand_info() 
                        _last_log_time = now


                    for hand_landmarks in _latest_result.hand_landmarks:
                        draw_hand_landmarks(img, hand_landmarks)

                    get_landmark_pixel_coordinates(img)
                    """
                    To get the coordinates of a specific landmark, you can access the `hands_cord_data` dictionary. 
                    For example, to get the coordinates of the thumb tip (landmark 4)for the left hand, you can do 
                    the following:

                    x1, y1 = hands_cord_data["Left"][4][0], hands_cord_data["Left"][4][1]
                    
                    NOTE: hands_cord_data['Left or Right Hand']['landmark index'][0 for x, 1 for y]  (landmark index is 0-20, refer to mediapipe documentation for details)
                    """

                    # # Test display
                    # if hands_cord_data["Left"]:
                    #     x1, y1, x2, y2 = hands_cord_data["Left"][4][0], hands_cord_data["Left"][4][1], hands_cord_data["Left"][8][0], hands_cord_data["Left"][8][1]
                    # else:
                    #     x1, y1, x2, y2 = hands_cord_data["Right"][4][0], hands_cord_data["Right"][4][1], hands_cord_data["Right"][8][0], hands_cord_data["Right"][8][1]
                    
                    # cv2.line(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    # print(f"{hypot(x2 - x1, y2 - y1):.2f} pixels between thumb tip and index tip")
                    """
                    Display the top gesture for each detected hand on the video feed.
                    """
                    for i, hand_gesture_list in enumerate(_latest_result.gestures):
                        if hand_gesture_list:
                            top_gesture = hand_gesture_list[0].category_name
                            hand_side = _latest_result.handedness[i][0].category_name
                            
                            # Send command for the top gesture
                            send_command(hand_side, top_gesture, hand_gesture_list[0].score)  
                            
                            # Display the hand side and top gesture with confidence score on the video feed
                            display_text = f"{hand_side}: {top_gesture} with confidence {hand_gesture_list[0].score:.2f}"

                            y_position = 70 + (i * 40) 
                            
                            cv2.putText(img, display_text, (10, y_position), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                currTime = time.time()
                fps = 1/(currTime-prevTime)
                prevTime = currTime

                cv2.putText(img, f'FPS: {int(fps)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 4)

                cv2.imshow("Image", img)
                window_quit_requested = cv2.waitKey(1) & 0xFF == ord('q')
                if window_quit_requested or console_quit_requested():
                    break
        finally:
            shutdown()  # flush any queued command and stop the serial worker thread
            capturer.release()
            cv2.destroyAllWindows()
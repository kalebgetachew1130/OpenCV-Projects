import cv2
import sys
import time
import select
import mediapipe as mp
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

latest_result = None

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
    global latest_result
    latest_result = result  # main loop picks this up on its next iteration

gesture_options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path='../task/gesture_recognizer.task'),
    num_hands = 2,
    running_mode=VisionRunningMode.LIVE_STREAM,
    result_callback=gesture_print_result)

"""
console_quit_requested() uses select() to check if there's input waiting on stdin without 
blocking the video loop. If a line equal to q (or EOF, e.g. Ctrl-D) is found, it returns 
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

def pretty_print_hand_info():
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
                for i, lm in enumerate(latest_result.hand_landmarks[idx])
                # Loop over every landmark for the current hand, using enumerate to get both the index (point_id) and the landmark data (lm)
            ],

            "gesture_preview" : [
                {
                    "category_name": gesture.category_name,
                    "confidence": round(gesture.score, 2)
                }
                for gesture in latest_result.gestures[idx]
            ]
        }
        # Loop over each detected hand's handedness info, using the index to also access its landmarks
        for idx, hand_list in enumerate(latest_result.handedness) 
    ]

    # Print the structured Python list beautifully — only when at least one hand has
    # an actual recognized gesture. MediaPipe returns the literal string "None" (not
    # empty/falsy) for the category name when no gesture is detected, so check against that.
    if any(
        hand["gesture_preview"] and hand["gesture_preview"][0]["category_name"] != "None"
        for hand in hand_summary
    ):
        pprint(hand_summary, sort_dicts=False)

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
        cx, cy = int(lm.x * w), int(lm.y * h)
        cv2.circle(image, (cx, cy), 4, (0, 255, 0), -1) # draw joint dot

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

            if latest_result is not None and len(latest_result.handedness) > 0:
                pretty_print_hand_info()

                for hand_landmarks in latest_result.hand_landmarks:
                    draw_hand_landmarks(img, hand_landmarks)

                for i, hand_gesture_list in enumerate(latest_result.gestures):
                    if hand_gesture_list:
                        top_gesture = hand_gesture_list[0].category_name
                        hand_side = latest_result.handedness[i][0].category_name
                        
                        display_text = f"{hand_side}: {top_gesture}"
                        
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
        capturer.release()
        cv2.destroyAllWindows()
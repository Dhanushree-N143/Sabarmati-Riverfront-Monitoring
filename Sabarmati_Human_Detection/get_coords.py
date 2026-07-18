import cv2

VIDEO_FILE = "surv.mp4"

def click_event(event, x, y, flags, params):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"POINT: {x}, {y}")
        cv2.circle(img, (x, y), 5, (0, 0, 255), -1)
        cv2.imshow('Coordinate Finder', img)

cap = cv2.VideoCapture(VIDEO_FILE)
ret, frame = cap.read()

if ret:
    img = cv2.resize(frame, (640, 480))
    cv2.imshow('Coordinate Finder', img)
    cv2.setMouseCallback('Coordinate Finder', click_event)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
else:
    print("Could not read video file.")
import cv2
import numpy as np

class FilterStrategy:
    """Base class for all filters to ensure they are callable"""
    def __call__(self, frame: np.ndarray) -> np.ndarray:
        raise NotImplementedError

class Raw(FilterStrategy):
    """Returns the original frame with motion rectangles drawn."""

    def __init__(self,
                 motion_resolution=(160, 90),
                 min_area=150,
                 threshold=25):
        self.prev_gray = None
        self.motion_resolution = motion_resolution
        self.min_area = min_area
        self.threshold = threshold

    def __call__(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]

        # Downscale
        small = cv2.resize(frame, self.motion_resolution, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        if self.prev_gray is None:
            self.prev_gray = gray
            return frame

        # Take diff
        delta = cv2.absdiff(self.prev_gray, gray)
        self.prev_gray = gray

        _, thresh = cv2.threshold(delta, self.threshold, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        scale_x = w / self.motion_resolution[0]
        scale_y = h / self.motion_resolution[1]

        for c in contours:
            if cv2.contourArea(c) < self.min_area:
                continue

            x, y, bw, bh = cv2.boundingRect(c)

            X = int(x * scale_x)
            Y = int(y * scale_y)
            W = int(bw * scale_x)
            H = int(bh * scale_y)

            cv2.rectangle(frame, (X, Y), (X + W, Y + H), (0, 255, 0), 2)

        return frame


class Motion(FilterStrategy):
    """Returns the binary threshold mask showing movement."""
    def __init__(self):
        self.prev_frame = None
        self.accumulated_weight = 0.5

    def __call__(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_frame is None:
            self.prev_frame = gray.copy().astype("float")
            return frame 

        cv2.accumulateWeighted(gray, self.prev_frame, self.accumulated_weight)
        frame_diff = cv2.absdiff(gray, cv2.convertScaleAbs(self.prev_frame))
        _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        # Convert back to BGR for the GUI
        return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

class CannyEdge(FilterStrategy):
    """Returns Canny Edge Detection view."""
    def __call__(self, frame: np.ndarray) -> np.ndarray:
        edges = cv2.Canny(frame, 100, 200)
        # Convert back to BGR for consistent pipeline handling
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
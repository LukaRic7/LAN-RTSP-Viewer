import threading, time, cv2
from collections import deque
from tkinter import Canvas
import loggerric as lr
import numpy as np

from filters import Raw

class StreamPipeline(threading.Thread):
    """Handles reading frames via OpenCV native VideoCapture."""

    def __init__(self, camera_data: dict, stream_key: str, canvas: Canvas, fps=15, filter_func=None):
        lr.Log.debug('Initializing Streaming Pipeline...')

        super().__init__(daemon=True)
        self.camera_data = camera_data
        self.stream_key = stream_key
        self.canvas = canvas
        self.fps = fps
        
        # If no filter provided, use Raw (pass-through)
        self.filter_func = filter_func if filter_func else Raw()

        self.running = False
        self.lock = threading.Lock()
        self.latest_frame = None

        self.last_frame_time = 0
        self.frame_buffer = deque(maxlen=1) 
        self.detected_resolution = (0, 0) 

        self.cap = None

    def run(self):
        self.running = True
        self.__open_stream()
        
        frame_interval = 1.0 / self.fps if self.fps > 0 else 0
        last_process_time = 0

        while self.running and self.cap.isOpened():
            # Read & Drain buffer
            ret, frame = self.cap.read()
            
            if not ret:
                lr.Log.error(f"Lost connection to {self.camera_data.get('nickname', 'Camera')}")
                time.sleep(2) 
                self.__open_stream()
                continue

            # Apply filter & Update
            current_time = time.time()
            if (current_time - last_process_time) >= frame_interval:
                self.__process_frame(frame)
                last_process_time = current_time
            
            # Tiny sleep to release GIL (Global Interpreter Lock)
            time.sleep(0.001)

        self.cap.release()

    def stop(self):
        self.running = False

    def get_resolution(self):
        with self.lock:
            return self.detected_resolution

    def __open_stream(self):
        if self.cap is not None:
            self.cap.release()
            
        rtsp_url = self.camera_data['rtsp_nostream'] + self.camera_data['streams'][self.stream_key]
        self.cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Low latency

        if not self.cap.isOpened():
            lr.Log.error(f"Failed to open stream: {rtsp_url}")

    def __process_frame(self, frame):
        """Apply filter and update shared state"""
        timestamp = time.time()
        
        try:
            processed_frame = self.filter_func(frame)
        except Exception as e:
            lr.Log.error(f"Filter error: {e}")
            processed_frame = frame # Fallback to original

        with self.lock:
            self.latest_frame = processed_frame
            
            # Detect resolution based on the "Processed" frame 
            if self.detected_resolution != (processed_frame.shape[1], processed_frame.shape[0]):
                self.detected_resolution = (processed_frame.shape[1], processed_frame.shape[0])
            
            self.last_frame_time = timestamp
            self.frame_buffer.clear()
            self.frame_buffer.append(processed_frame)

    def get_frame(self):
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None, []
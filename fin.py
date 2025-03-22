import cv2
import numpy as np
import mss
import socket
import threading
import time
import pydirectinput  # Using pydirectinput for better game compatibility
from flask import Flask, Response, request
import psutil
import os

# Set the process priority to high
p = psutil.Process(os.getpid())
p.nice(psutil.HIGH_PRIORITY_CLASS)  # Windows


# Flask app setup
app = Flask(__name__)

# Socket setup for control input
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
CONTROL_PORT = 5001  # Port to receive control inputs
PC_IP = "0.0.0.0"  # Listen on all interfaces
sock.bind((PC_IP, CONTROL_PORT))

# Screen capture settings
fps = 30
frame_interval = 1 / fps
monitor = None

# Global variable for video frame
frame = None

def capture_screen():
    global frame, monitor
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        while True:
            start_time = time.time()
            sct_img = sct.grab(monitor)
            frame = np.array(sct_img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            elapsed = time.time() - start_time
            time.sleep(max(0, frame_interval - elapsed))

@app.route('/')
def index():
    return '''
    <html>
    <body>
        <img id="video" src="/video_feed" width="100%">
        <div id="dpad">
            <button onclick="sendControl('w')">Up</button>
            <br>
            <button onclick="sendControl('a')">Left</button>
            <button onclick="sendControl('s')">Down</button>
            <button onclick="sendControl('d')">Right</button>
            <button onclick="sendControl('y')">Y</button>
            <button onclick="sendControl('u')">U</button>
            <button onclick="sendControl('z')">Z</button>
            <button onclick="sendControl('x')">X</button>
        </div>
        <script>
            function sendControl(key) {
                fetch('/control', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ key: key })
                });
            }
            document.addEventListener('click', function(event) {
                fetch('/control', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ key: 'mouse_click' })
                });
            });
        </script>
    </body>
    </html>
    '''

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            if frame is None:
                continue
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control', methods=['POST'])
def control():
    data = request.get_json()
    if data and 'key' in data:
        key = data['key']
        sock.sendto(key.encode(), ("192.168.99.7", CONTROL_PORT))
        
        # Simulate key presses using pydirectinput
        if key in ['w', 'a', 's', 'd','y','u','z','x']:
            pydirectinput.press(key)
    return '', 204

if __name__ == '__main__':
    threading.Thread(target=capture_screen, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, threaded=True)

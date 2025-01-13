import cv2
import numpy as np

named_pipe_path = 'named_pipes/video_pipe'

def read_pipe():
    with open(named_pipe_path, 'rb') as pipe:
        while True:
            # Read boundary
            boundary_line = pipe.readline()
            if not boundary_line:
                print("No data from pipe.")
                continue

            if boundary_line.strip() == b'--frame':
                headers = {}
                while True:
                    header_line = pipe.readline()
                    if header_line == b'\r\n':
                        break
                    header_parts = header_line.decode('utf-8', errors='replace').split(':', 1)
                    if len(header_parts) == 2:
                        headers[header_parts[0].strip().lower()] = header_parts[1].strip()

                content_length = int(headers.get('content-length', 0))
                if content_length:
                    frame_data = pipe.read(content_length)
                    frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        cv2.imshow("Frame", frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break

read_pipe()

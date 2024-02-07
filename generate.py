import cv2
import numpy as np

# Video properties
fps = 24  # Frames per second
duration = 2 * 60  # 2 minutes
frame_count = fps * duration
width, height = 1920, 1080  # Resolution of the video

# Create a white image
white_frame = np.full((height, width, 3), 255, dtype=np.uint8)

# Create a black image for flashing
black_frame = np.zeros((height, width, 3), dtype=np.uint8)

# Initialize video writer
fourcc = cv2.VideoWriter_fourcc(*'MP4V')  # or use 'XVID' for an .avi file
out = cv2.VideoWriter('output_video.mp4', fourcc, fps, (width, height))

for frame_num in range(frame_count):
    # Check if current frame is in the range of 1:02 to 1:04
    if 62 * fps <= frame_num <= 64 * fps:
        out.write(black_frame)  # Write a black frame
    else:
        out.write(white_frame)  # Write a white frame

# Release the video writer
out.release()

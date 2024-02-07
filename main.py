import cv2
import os
import subprocess
import numpy as np

# Adjustable parameters
HIGHLIGHT_DURATION = 20  # seconds
COOLDOWN_PERIOD = 10  # seconds
DARKNESS_THRESHOLD = 10  # Adjust based on your criteria for "black" frame
FRAME_SAMPLE_RATE = 120  # Assume 24 fps, sample every 2 seconds

# Path configurations
INPUT_FOLDER = 'input'
OUTPUT_FOLDER = 'output'

# Helper function to execute FFmpeg commands
def execute_ffmpeg_command(command):
    try:
        return subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg command failed: {e}")

def get_video_duration(filename):
    command = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{filename}\""
    result = execute_ffmpeg_command(command)
    duration = float(result.stdout)
    return duration

def get_video_files_sorted(folder):
    """Get all video files from the folder, sorted alphabetically."""
    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    video_files = [f for f in files if f.endswith('.mp4')]  # Assuming MP4 format
    sorted_files = sorted(video_files)
    return sorted_files

def generate_video_segments(folder):
    sorted_files = get_video_files_sorted(folder)
    video_segments = []
    start_time = 0  # Initialize start time

    for filename in sorted_files:
        full_path = os.path.join(folder, filename)
        duration = get_video_duration(full_path)
        video_segments.append({"filename": full_path, "start_time": start_time, "duration": duration})
        start_time += duration  # Increment start time by the video's duration for the next video

    return video_segments

# Function to detect black frames and return their timestamps
def detect_black_frames(video_file, start_global_time):
    cap = cv2.VideoCapture(video_file)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    timestamps = []
    index = 0

    for frame_idx in range(0, frame_count, FRAME_SAMPLE_RATE):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        success, frame = cap.read()
        if not success:
            break

        # Calculate the frame's average brightness
        average_brightness = frame.mean()
        
        index += 2
        
        if index % 60 == 0:
            print(f"Processed {index} seconds...")
        if average_brightness < DARKNESS_THRESHOLD:
            # Calculate global timestamp for the black frame
            global_timestamp = start_global_time + (frame_idx / fps)
            timestamps.append(global_timestamp)
    
    cap.release()
    return timestamps

# Function to map video segments and detect highlights
def map_and_detect_highlights(video_segments):
    highlights = []
    last_processed_time = None

    for segment in video_segments:
        filename = segment['filename']
        start_time = segment['start_time']
        black_frame_timestamps = detect_black_frames(filename, start_time)

        for timestamp in black_frame_timestamps:
            # Apply cooldown period
            if last_processed_time is None or timestamp - last_processed_time > COOLDOWN_PERIOD:
                highlight_start = max(timestamp - HIGHLIGHT_DURATION, 0)
                highlights.append((highlight_start, timestamp))
                last_processed_time = timestamp

    return highlights

def calculate_highlight_segments(video_segments, highlights):
    highlight_instructions = []

    for highlight in highlights:
        highlight_start, highlight_end = highlight
        instructions = []

        # Iterate through each video segment to check if the highlight falls within it
        for segment in video_segments:
            segment_start = segment['start_time']
            # Assuming each segment includes a 'duration' key
            segment_end = segment_start + segment.get('duration', 0)

            # Check if the highlight overlaps with the current segment
            if highlight_start < segment_end and highlight_end > segment_start:
                # Calculate the overlap start and end within the segment
                overlap_start = max(highlight_start - segment_start, 0)
                overlap_end = min(highlight_end, segment_end) - segment_start

                # Calculate duration of the overlap
                overlap_duration = overlap_end - overlap_start

                instructions.append({
                    'filename': segment['filename'],
                    'start_time': overlap_start,
                    'duration': overlap_duration
                })

        highlight_instructions.append(instructions)

    return highlight_instructions

def generate_ffmpeg_commands(highlight_instructions):
    commands = []

    for i, instructions in enumerate(highlight_instructions, start=1):
        if len(instructions) == 1:
            # Simple case: Highlight is within a single segment
            command = f"ffmpeg -ss {instructions[0]['start_time']} -i \"{instructions[0]['filename']}\" -t {instructions[0]['duration']} -c copy \"{OUTPUT_FOLDER}\\highlight_{i}.mp4\""
            commands.append(command)
        else:
            # Highlight spans multiple segments, need to concatenate
            filter_complex = ""
            inputs = ""
            for j, instruction in enumerate(instructions):
                temp_filename = f"temp_part_{j}.mp4"
                commands.append(f"ffmpeg -ss {instruction['start_time']} -i \"{instruction['filename']}\" -t {instruction['duration']} -c copy \"{temp_filename}\"")
                inputs += f"-i \"{temp_filename}\" "
                filter_complex += f"[{j}:v:0][{j}:a:0]"
            filter_complex += f"concat=n={len(instructions)}:v=1:a=1 [v] [a]"

            concat_command = f"ffmpeg {inputs} -filter_complex \"{filter_complex}\" -map \"[v]\" -map \"[a]\" -r 60 -c:v libx264 -crf 22 -vsync cfr \"{OUTPUT_FOLDER}/highlight_{i}.mp4\""

            commands.append(concat_command)

            # Cleanup temporary files command for Windows
            cleanup_command = "del " + " ".join([f"\"temp_part_{j}.mp4\"" for j, _ in enumerate(instructions)])
            commands.append(cleanup_command)

    return commands

# Main function to process video segments
def process_video_segments():
    # Example video segments with start times
    video_segments = generate_video_segments(INPUT_FOLDER)
    print(f"Videos details identified: {video_segments}")

    # Detect highlights
    highlights = map_and_detect_highlights(video_segments)
    print(f"Highlights to extract: {highlights}")

    highlight_instructions = calculate_highlight_segments(video_segments, highlights)

    print(f"Method to create highlights: {highlight_instructions}")
    commands = generate_ffmpeg_commands(highlight_instructions)
    
    for command in commands:
        print(f"Running command {command}...")
        execute_ffmpeg_command(command)

process_video_segments()

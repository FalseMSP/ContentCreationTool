import os
import cv2
import numpy as np
from moviepy.editor import VideoFileClip

# Constants
DIRECTORY = 'C:/Users/CPSEGuest/Videos/Captures/'

def get_file_title(path):
    """Extract the filename without extension."""
    filename_with_extension = os.path.basename(path)
    title, _ = os.path.splitext(filename_with_extension)
    return title

def apply_pencil_sketch(frame):
    """Apply a pencil sketch effect to the given frame."""
    # Convert frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    
    # Invert the grayscale image
    inverted_gray = cv2.bitwise_not(gray)
    
    # Apply Gaussian blur to the inverted grayscale image
    blurred = cv2.GaussianBlur(inverted_gray, (21, 21), 0)
    
    # Blend the grayscale image with the blurred image
    sketch = cv2.divide(gray, 255 - blurred, scale=256)
    
    # Convert back to a 3-channel image
    sketch_colored = cv2.cvtColor(sketch, cv2.COLOR_GRAY2RGB)
    
    return sketch_colored

def detect_edges(frame):
    """Apply Canny edge detection and make the edges thicker and black on a white background."""
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 100, 200)  # Adjust thresholds here
    
    # Define a kernel for dilation (this controls the thickness of the lines)
    kernel = np.ones((5, 5), np.uint8)  # Adjust kernel size for thickness
    edges_dilated = cv2.dilate(edges, kernel, iterations=1)
    
    # Create a white image of the same size as the original frame
    white_background = np.ones_like(frame) * 255  # White background
    
    # Create a mask for the edges
    mask = edges_dilated != 0
    
    # Place black edges on the white background
    white_background[mask] = [0, 0, 0]  # Black color where edges are
    
    return white_background

def process_frame(frame):
    """Process each frame to add artistic pencil sketch and thicker black edges."""
    # Convert frame to numpy array (required for OpenCV)
    frame_np = np.array(frame)
    
    # Apply pencil sketch effect
    sketch_frame = apply_pencil_sketch(frame_np)
    
    # Apply edge detection on the sketch
    edges_frame = detect_edges(sketch_frame)
    
    # Convert back to a moviepy frame
    return edges_frame

def main(input_video_path, output_video_path):
    """Process the video to detect thicker black edges on a white background and add a pencil sketch effect, then save the result."""
    clip = VideoFileClip(input_video_path)
    # Apply the frame processing to each frame
    processed_clip = clip.fl_image(process_frame)
    # Write the result to a file
    processed_clip.write_videofile(output_video_path, codec='libx264')

def scan_directory(directory_path):
    """Scan the directory for video files."""
    video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv'}
    file_list = []
    
    for root, dirs, files in os.walk(directory_path):
        for file_name in files:
            _, ext = os.path.splitext(file_name)
            if ext.lower() in video_extensions:
                file_path = os.path.join(root, file_name)
                file_list.append(file_path)
    
    return file_list

if __name__ == "__main__":
    file_list = scan_directory(DIRECTORY)
    print(file_list)
    for file in file_list:
        fileName = get_file_title(file)
        input_video = file  # Path to the input video file
        output_video = f"{DIRECTORY}{fileName}Sketchified.mp4"  # Path to the output video file
        main(input_video, output_video)

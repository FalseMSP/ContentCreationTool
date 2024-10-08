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

def detect_edges(frame):
    """Apply Canny edge detection and make the edges thicker and black on a white background."""
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 25, 125)  # Adjust thresholds here
    
    # Define a kernel for dilation (this controls the thickness of the lines)
    kernel = np.ones((1, 1), np.uint8)  # Adjust kernel size for thickness
    edges_dilated = cv2.dilate(edges, kernel, iterations=1)
    
    # Create a white image of the same size as the original frame
    white_background = np.ones_like(frame) * 255  # White background
    
    # Convert dilated edges to a 3-channel image
    edges_colored = cv2.cvtColor(edges_dilated, cv2.COLOR_GRAY2RGB)
    
    # Create a mask for the edges
    mask = edges_dilated != 0
    
    # Place black edges on the white background
    white_background[mask] = [0, 0, 0]  # Black color where edges are
    
    return white_background

def process_frame(frame):
    """Process each frame to add thicker black edges on a white background."""
    # Convert frame to numpy array (required for OpenCV)
    frame_np = np.array(frame)
    edges_frame = detect_edges(frame_np)
    # Convert back to a moviepy frame
    return edges_frame

def main(input_video_path, output_video_path):
    """Process the video to detect thicker black edges on a white background and save the result."""
    clip = VideoFileClip(input_video_path)
    # Apply the edge detection to each frame
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
        output_video = f"{DIRECTORY}{fileName}Edgified.mp4"  # Path to the output video file
        main(input_video, output_video)

import os
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
from moviepy.video.fx import resize, crop
import google.auth
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import httplib2
import pickle



# Constants
DIRECTORY = 'C:/Users/CPSEGuest/Videos/Captures/'
from moviepy.editor import VideoFileClip
import cv2
import numpy as np

def get_file_title(path):
    # Extract the filename with extension
    filename_with_extension = os.path.basename(path)
    # Split the filename and extension
    title, _ = os.path.splitext(filename_with_extension)
    return title


def detect_edges(frame):
    """Apply Canny edge detection to a single frame."""
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 100, 200)  # You can adjust thresholds here
    # Convert edges to 3-channel image for compatibility with moviepy
    edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
    return edges_colored

def process_frame(frame):
    """Process each frame and return the result with edges detected."""
    # Convert frame to numpy array (required for OpenCV)
    frame_np = np.array(frame)
    edges_frame = detect_edges(frame_np)
    # Convert back to a moviepy frame
    return edges_frame

def main(input_video_path, output_video_path):
    """Process the video to detect edges and save the result."""
    clip = VideoFileClip(input_video_path)
    # Apply the edge detection to each frame
    processed_clip = clip.fl_image(process_frame)
    # Write the result to a file
    processed_clip.write_videofile(output_video_path, codec='libx264')

def scan_directory(directory_path):
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
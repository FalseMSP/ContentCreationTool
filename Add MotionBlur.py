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

def motion_blur(image, kernel_size=15):
    """Apply motion blur to an image."""
    kernel = np.zeros((kernel_size, kernel_size))
    kernel[int((kernel_size-1)/2), :] = np.ones(kernel_size)
    kernel /= kernel_size
    return cv2.filter2D(image, -1, kernel)

def compute_difference(prev_frame, curr_frame):
    """Compute the absolute difference between two frames."""
    diff = cv2.absdiff(curr_frame, prev_frame)
    return cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

def apply_motion_blur(frame, prev_frame, kernel_size=15, diff_threshold=30):
    """Apply motion blur based on the difference between frames."""
    # Convert frames to numpy arrays
    frame_np = np.array(frame)
    prev_frame_np = np.array(prev_frame)

    # Compute difference
    diff = compute_difference(prev_frame_np, frame_np)

    # Create a mask where the difference is significant
    _, mask = cv2.threshold(diff, diff_threshold, 255, cv2.THRESH_BINARY)

    # Apply motion blur to the current frame
    blurred_frame = motion_blur(frame_np, kernel_size)

    # Combine blurred and original frames based on the mask
    result = np.where(mask[:, :, None] == 255, blurred_frame, frame_np)
    return result

def main(input_video_path, output_video_path):
    """Process the video and apply motion blur where needed."""
    # Load video
    clip = VideoFileClip(input_video_path)
    
    # Store the previous frame
    prev_frame = None

    def process_frame(frame):
        nonlocal prev_frame

        if prev_frame is None:
            prev_frame = frame
            return frame

        # Apply motion blur effect
        processed_frame = apply_motion_blur(frame, prev_frame)

        # Update previous frame
        prev_frame = frame

        return processed_frame

    # Apply processing to each frame and write the result
    processed_clip = clip.fl_image(process_frame)
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
        output_video = f"{DIRECTORY}{fileName}MotionBlurred.mp4"  # Path to the output video file
        main(input_video, output_video)
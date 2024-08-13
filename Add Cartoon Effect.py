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

def apply_bilateral_filter(image):
    """Apply bilateral filter to smooth the image while preserving edges."""
    return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)

def apply_color_quantization(image, k=8):
    """Reduce the number of colors in the image."""
    # Convert image to a 2D array of pixels
    Z = image.reshape((-1, 3))
    Z = np.float32(Z)
    
    # Define criteria and apply k-means clustering
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, label, center = cv2.kmeans(Z, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    # Convert back to uint8 and reshape
    center = np.uint8(center)
    res = center[label.flatten()]
    result_image = res.reshape((image.shape))
    
    return result_image

def cartoonify_image(image):
    """Apply cartoon effect with flat colors to an image."""
    # Apply bilateral filter to smooth the image while preserving edges
    color = apply_bilateral_filter(image)
    
    # Convert to grayscale
    gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    
    # Apply median blur to the grayscale image
    gray = cv2.medianBlur(gray, 7)
    
    # Detect edges using adaptive thresholding
    edges = cv2.adaptiveThreshold(gray, 255,
                                 cv2.ADAPTIVE_THRESH_MEAN_C,
                                 cv2.THRESH_BINARY, 9, 10)
    
    # Apply color quantization to reduce the number of colors
    color_flat = apply_color_quantization(color, k=8)
    
    # Convert edges to color
    edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
    # Combine the smoothed color image with the edge image
    cartoon = cv2.bitwise_and(color_flat, edges_colored)
    
    return cartoon

def process_frame(frame):
    """Process each frame and return the result with edges detected."""
    # Convert frame to numpy array (required for OpenCV)
    frame_np = np.array(frame)
    edges_frame = cartoonify_image(frame_np)
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
        output_video = f"{DIRECTORY}{fileName}Cartoonified.mp4"  # Path to the output video file
        main(input_video, output_video)
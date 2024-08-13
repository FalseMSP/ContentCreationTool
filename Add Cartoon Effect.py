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
from sklearn.cluster import KMeans

# Constants
DIRECTORY = 'C:/Users/CPSEGuest/Videos/Captures/'
colors = [
    [255, 182, 193],  # Light Pink
    [255, 239, 179],  # Pastel Yellow
    [176, 224, 230],  # Powder Blue
    [152, 251, 152],  # Pale Green
    [255, 228, 225],  # Misty Rose
    [255, 240, 245],  # Lavender Blush
    [240, 248, 255],  # Alice Blue
    [255, 224, 178],  # Peach Puff
    [219, 219, 255],  # Periwinkle
    [255, 204, 229],  # Cotton Candy
    [255, 192, 203],  # Pink
    [200, 191, 231],  # Lavender
    [190, 255, 255],  # Light Cyan
    [240, 230, 140],  # Khaki
    [255, 240, 245],  # Lavender Blush
    [255, 239, 213],  # Blanched Almond
    [240, 255, 240],  # Honeydew
    [248, 248, 255],  # Ghost White
    [248, 222, 126],  # Light Goldenrod Yellow
    [245, 245, 245],  # White Smoke
    [255, 218, 185],  # Antique White
    [255, 228, 196],  # Bisque
    [255, 239, 196],  # Light Cream
    [255, 240, 200],  # Cream
    [200, 255, 200],  # Honeydew
    [255, 240, 245],  # Lavender Blush
    [135, 206, 250],  # Light Sky Blue
    [147, 112, 219],  # Medium Purple
    [255, 240, 245],  # Lavender Blush
    [205, 133, 63],   # Peru
    [255, 182, 193],  # Light Pink
    [255, 248, 220],  # Cornsilk
    [224, 255, 255],  # Light Cyan
    [240, 230, 140],  # Khaki
    [240, 248, 255],  # Alice Blue
    [253, 245, 230],  # Old Lace
    [255, 228, 225],  # Misty Rose
    [240, 255, 240],  # Honeydew
    [255, 228, 196],  # Bisque
]

from moviepy.editor import VideoFileClip
import cv2
import numpy as np
from multiprocessing import Pool

def get_file_title(path):
    # Extract the filename with extension
    filename_with_extension = os.path.basename(path)
    # Split the filename and extension
    title, _ = os.path.splitext(filename_with_extension)
    return title

import cv2
import numpy as np
from moviepy.editor import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

def find_closest_colors(pixels, colors):
    """
    Find the closest color in the 'colors' array to each pixel color in the 'pixels' array.
    """
    # Convert colors to a NumPy array if it's not already
    colors = np.array(colors)
    
    # Compute the squared differences between each pixel and each color
    pixel_colors_diff = pixels[:, np.newaxis, :] - colors
    
    # Compute squared Euclidean distances
    distances = np.sum(pixel_colors_diff ** 2, axis=2)
    
    # Find the index of the minimum distance for each pixel
    closest_color_indices = np.argmin(distances, axis=1)
    
    # Retrieve the closest colors
    return colors[closest_color_indices]

def process_frame(image):
    global colors
    """
    Process the image by rounding pixel colors to the nearest color in the 'colors' array.
    """
    # Convert image to float32 for precision
    image_float = image.astype(np.float32)
    
    # Reshape image to a 2D array where each row is a pixel with [B, G, R] values
    pixels = image_float.reshape(-1, 3)
    
    # Find the closest color for each pixel
    processed_pixels = find_closest_colors(pixels, colors)
    
    # Reshape back to the original image shape
    processed_image = processed_pixels.reshape(image.shape).astype(np.uint8)
    
    return processed_image

def process_video(input_path, output_path):
    """Process the video to flatten colors."""
    # Load the video
    clip = VideoFileClip(input_path)

    # Process each frame
    processed_clip = clip.fl_image(process_frame)

    # Write the result to the output file
    processed_clip.write_videofile(output_path, codec='libx264')

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
        process_video(input_video, output_video)
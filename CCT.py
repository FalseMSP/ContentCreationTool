import os
from moviepy.editor import VideoFileClip
from moviepy.video.fx import resize, crop

def crop_and_scale_to_9_16(input_path, output_path, start_trim_seconds, end_trim_seconds):
    # Load the video
    video = VideoFileClip(input_path)
    
    # Get the duration of the video in seconds
    duration = video.duration
    
    # Define the new start and end times for trimming
    start_time = start_trim_seconds
    end_time = duration - end_trim_seconds
    
    # Ensure the end time is not before the start time
    if end_time < start_time:
        raise ValueError("End trim time is before start trim time. Adjust the trim seconds.")
    
    # Trim the video
    trimmed_video = video.subclip(start_time, end_time)
    
    # Define target aspect ratio (9:16)
    target_aspect_ratio = 9 / 16
    
    # Get the original dimensions
    original_width, original_height = trimmed_video.size
    
    # Calculate the new dimensions to maintain the aspect ratio
    if original_width / original_height > target_aspect_ratio:
        # If the original video is wider than 9:16, crop the width
        new_width = int(original_height * target_aspect_ratio)
        new_height = original_height
        x1 = (original_width - new_width) // 2
        x2 = x1 + new_width
        y1, y2 = 0, new_height
    else:
        # If the original video is taller than 9:16, crop the height
        new_width = original_width
        new_height = int(original_width / target_aspect_ratio)
        x1, x2 = 0, new_width
        y1 = (original_height - new_height) // 2
        y2 = y1 + new_height
    
    # Crop the video to the new dimensions
    cropped_video = trimmed_video.crop(x1=x1, x2=x2, y1=y1, y2=y2)
    
    # Resize the cropped video to 9:16 frame (1080x1920 as an example)
    target_width = 1080
    target_height = int(target_width * (16 / 9))
    scaled_video = resize(cropped_video, newsize=(target_width, target_height))
    
    # Write the result to the output path
    scaled_video.write_videofile(output_path, codec="libx264")

def trim_video(input_path, output_path, start_trim_seconds, end_trim_seconds):
    # Load the video
    video = VideoFileClip(input_path)
    
    # Get the duration of the video in seconds
    duration = video.duration
    
    # Define the new start and end times for trimming
    start_time = start_trim_seconds
    end_time = duration - end_trim_seconds
    
    # Ensure the end time is not before the start time
    if end_time < start_time:
        raise ValueError("End trim time is before start trim time. Adjust the trim seconds.")
    
    # Trim the video
    trimmed_video = video.subclip(start_time, end_time)
    
    # Write the result to the output path
    trimmed_video.write_videofile(output_path, codec="libx264")
# Constants
DIRECTORY = 'C:/Users/CPSEGuest/Videos/Captures'

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

if __name__ == '__main__':
    file_list = scan_directory(DIRECTORY)
    print(file_list)

#!/usr/bin/env python3
"""
Script to add W A S D icons to a video with highlighting based on action timing.
Uses FFmpeg for better codec compatibility across platforms.
"""

import cv2
import numpy as np
import json
import os
import subprocess
import tempfile
from pathlib import Path
import re

def create_icon_overlay(frame, action_list, frame_number, fps=24, frames_per_action=None, total_frames=None):
    """
    Create icon overlay for the current frame.
    
    Args:
        frame: Input video frame
        action_list: List of actions to cycle through
        frame_number: Current frame number
        fps: Video frame rate
        frames_per_action: Number of frames per action (if None, will be calculated)
        total_frames: Total number of frames in video
    
    Returns:
        Frame with icons overlaid
    """
    height, width = frame.shape[:2]
    
    # Icon properties
    icon_size = 80
    icon_radius = 40
    icon_spacing = 100
    icon_y_offset = height - 150  # Position above video controls
    
    # Icon positions (centered horizontally)
    center_x = width // 2
    icon_positions = {
        'w': (center_x - icon_spacing, icon_y_offset - icon_spacing),
        'a': (center_x - icon_spacing, icon_y_offset),
        's': (center_x, icon_y_offset),
        'd': (center_x + icon_spacing, icon_y_offset)
    }
    
    # Calculate which action should be highlighted
    if frames_per_action is None and total_frames is not None:
        # Calculate frames per action based on total video length
        frames_per_action = total_frames // len(action_list)
    
    if frames_per_action:
        action_index = frame_number // frames_per_action
        
        if action_index < len(action_list):
            current_action = action_list[action_index].lower()
        else:
            current_action = None
    else:
        current_action = None
    
    # Draw icons
    for key, (x, y) in icon_positions.items():
        # Determine if this icon should be highlighted
        is_active = (key == current_action)
        
        # Icon color: green if active, gray if inactive
        if is_active:
            color = (0, 255, 0)  # Bright green
            border_color = (255, 255, 255)  # White border
            border_thickness = 3
        else:
            color = (128, 128, 128)  # Gray
            border_color = (64, 64, 64)  # Dark gray border
            border_thickness = 1
        
        # Draw icon background (rounded rectangle)
        cv2.rectangle(frame, (x - icon_radius, y - icon_radius), 
                     (x + icon_radius, y + icon_radius), color, -1)
        
        # Draw icon border
        cv2.rectangle(frame, (x - icon_radius, y - icon_radius), 
                     (x + icon_radius, y + icon_radius), border_color, border_thickness)
        
        # Draw letter
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 2.0
        font_thickness = 3
        text_size = cv2.getTextSize(key.upper(), font, font_scale, font_thickness)[0]
        text_x = x - text_size[0] // 2
        text_y = y + text_size[1] // 2
        
        # Draw text with black outline for better visibility
        cv2.putText(frame, key.upper(), (text_x, text_y), font, font_scale, 
                    (0, 0, 0), font_thickness + 2)  # Black outline
        cv2.putText(frame, key.upper(), (text_x, text_y), font, font_scale, 
                    (255, 255, 255), font_thickness)  # White text
    
    return frame

def get_ffmpeg_version():
    """Get FFmpeg version and return major version number."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            # Extract version from first line
            version_line = result.stdout.split('\n')[0]
            # Look for version number like "ffmpeg version 4.2.7" or "ffmpeg version 5.1.2"
            match = re.search(r'ffmpeg version (\d+)\.', version_line)
            if match:
                return int(match.group(1))
        return None
    except:
        return None

def get_ffmpeg_command(input_pattern, output_path, fps, width, height):
    """
    Generate optimized FFmpeg command for web-compatible video.
    Compatible with both older and newer FFmpeg versions.
    
    Args:
        input_pattern: Input frame pattern (e.g., 'frame_%06d.png')
        output_path: Output video path
        fps: Frame rate
        width: Video width
        height: Video height
    
    Returns:
        List of FFmpeg command arguments
    """
    # Get FFmpeg version
    ffmpeg_version = get_ffmpeg_version()
    
    # Determine output format and codec
    output_ext = os.path.splitext(output_path)[1].lower()
    
    if output_ext == '.mp4':
        # MP4 with H.264 - best web compatibility
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-framerate', str(fps),
            '-i', input_pattern,
            '-pix_fmt', 'yuv420p',  # Better compatibility
            '-vf', f'scale={width}:{height}'  # Ensure correct dimensions
        ]
        
        # Try to use libx264, fallback to default codec if not available
        try:
            # Check if libx264 is available
            result = subprocess.run(['ffmpeg', '-codecs'], capture_output=True, text=True)
            if 'libx264' in result.stdout:
                cmd.extend(['-c:v', 'libx264'])
                cmd.extend(['-crf', '23'])  # High quality, reasonable file size
            else:
                # Fallback to default codec
                cmd.extend(['-q:v', '3'])  # Quality setting for default codec
                print("Note: libx264 not available, using default codec")
        except:
            # If we can't check codecs, try libx264 anyway
            cmd.extend(['-c:v', 'libx264'])
            cmd.extend(['-crf', '23'])
        
        # Add version-specific options
        if ffmpeg_version and ffmpeg_version >= 5:
            # FFmpeg 5.0+ supports these options
            cmd.extend(['-preset', 'medium'])
            cmd.extend(['-movflags', '+faststart'])
        
        cmd.append(output_path)
        return cmd
        
    elif output_ext == '.webm':
        # WebM with VP9 - good web compatibility, smaller files
        return [
            'ffmpeg',
            '-y',
            '-framerate', str(fps),
            '-i', input_pattern,
            '-c:v', 'libvpx-vp9',
            '-crf', '30',
            '-b:v', '0',
            '-pix_fmt', 'yuv420p',
            '-vf', f'scale={width}:{height}',
            output_path
        ]
    elif output_ext == '.avi':
        # AVI with H.264 - basic compatibility
        cmd = [
            'ffmpeg',
            '-y',
            '-framerate', str(fps),
            '-i', input_pattern,
            '-pix_fmt', 'yuv420p',
            '-vf', f'scale={width}:{height}'
        ]
        
        # Try to use libx264, fallback to default codec if not available
        try:
            result = subprocess.run(['ffmpeg', '-codecs'], capture_output=True, text=True)
            if 'libx264' in result.stdout:
                cmd.extend(['-c:v', 'libx264'])
                cmd.extend(['-crf', '23'])
            else:
                cmd.extend(['-q:v', '3'])
                print("Note: libx264 not available, using default codec")
        except:
            cmd.extend(['-c:v', 'libx264'])
            cmd.extend(['-crf', '23'])
        
        # Add version-specific options
        if ffmpeg_version and ffmpeg_version >= 5:
            cmd.extend(['-preset', 'medium'])
        
        cmd.append(output_path)
        return cmd
        
    else:
        # Default to MP4
        cmd = [
            'ffmpeg',
            '-y',
            '-framerate', str(fps),
            '-i', input_pattern,
            '-pix_fmt', 'yuv420p',
            '-vf', f'scale={width}:{height}'
        ]
        
        # Try to use libx264, fallback to default codec if not available
        try:
            result = subprocess.run(['ffmpeg', '-codecs'], capture_output=True, text=True)
            if 'libx264' in result.stdout:
                cmd.extend(['-c:v', 'libx264'])
                cmd.extend(['-crf', '23'])
            else:
                cmd.extend(['-q:v', '3'])
                print("Note: libx264 not available, using default codec")
        except:
            cmd.extend(['-c:v', 'libx264'])
            cmd.extend(['-crf', '23'])
        
        # Add version-specific options
        if ffmpeg_version and ffmpeg_version >= 5:
            cmd.extend(['-preset', 'medium'])
            cmd.extend(['-movflags', '+faststart'])
        
        cmd.append(output_path)
        return cmd

def process_video(input_video_path, output_video_path, action_list, fps=24, frames_per_action=None):
    """
    Process the video and add icon overlays using FFmpeg for better compatibility.
    
    Args:
        input_video_path: Path to input video
        output_video_path: Path to output video
        action_list: List of actions
        fps: Video frame rate
        frames_per_action: Number of frames per action (if None, will be calculated)
    """
    # Open input video
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {input_video_path}")
        return
    
    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Calculate frames per action if not provided
    if frames_per_action is None:
        frames_per_action = total_frames // len(action_list)
        print(f"Calculated frames per action: {frames_per_action}")
    
    print(f"Video properties:")
    print(f"  Resolution: {width}x{height}")
    print(f"  Total frames: {total_frames}")
    print(f"  FPS: {actual_fps}")
    print(f"  Duration: {total_frames/actual_fps:.2f} seconds")
    print(f"  Actions: {action_list}")
    print(f"  Frames per action: {frames_per_action}")
    
    # Create temporary directory for frames
    with tempfile.TemporaryDirectory() as temp_dir:
        print("Processing video frames...")
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Add icon overlay
            frame_with_icons = create_icon_overlay(frame, action_list, frame_count, actual_fps, frames_per_action, total_frames)
            
            # Save frame as PNG
            frame_path = os.path.join(temp_dir, f"frame_{frame_count:06d}.png")
            cv2.imwrite(frame_path, frame_with_icons)
            
            frame_count += 1
            
            # Progress indicator
            if frame_count % 100 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"  Progress: {progress:.1f}% ({frame_count}/{total_frames})")
        
        # Close video capture
        cap.release()
        
        print("Frames processed. Now encoding with FFmpeg...")
        
        # Use FFmpeg to encode the frames
        try:
            # Check if FFmpeg is available
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            
            # Get optimized FFmpeg command
            ffmpeg_cmd = get_ffmpeg_command(
                os.path.join(temp_dir, 'frame_%06d.png'),
                output_video_path,
                actual_fps,
                width,
                height
            )
            
            print(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
            # Run FFmpeg
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Video encoding complete!")
                print(f"Output saved to: {output_video_path}")
            else:
                print(f"FFmpeg error: {result.stderr}")
                print("Falling back to OpenCV...")
                raise Exception("FFmpeg failed")
                
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("FFmpeg not available. Falling back to OpenCV (may have compatibility issues)...")
            
            # Fallback to OpenCV
            try:
                # Reopen video capture for fallback
                cap = cv2.VideoCapture(input_video_path)
                if not cap.isOpened():
                    print("Error: Could not reopen video for fallback")
                    return
                
                # Create video writer with OpenCV
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(output_video_path, fourcc, actual_fps, (width, height))
                
                if not out.isOpened():
                    print(f"Error: Could not create output video {output_video_path}")
                    cap.release()
                    return
                
                # Process frames again
                frame_count = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # Add icon overlay
                    frame_with_icons = create_icon_overlay(frame, action_list, frame_count, actual_fps, frames_per_action, total_frames)
                    
                    # Write frame
                    out.write(frame_with_icons)
                    
                    frame_count += 1
                    
                    # Progress indicator
                    if frame_count % 100 == 0:
                        progress = (frame_count / total_frames) * 100
                        print(f"  Fallback progress: {progress:.1f}% ({frame_count}/{total_frames})")
                
                # Clean up
                cap.release()
                out.release()
                print(f"Fallback video processing complete!")
                print(f"Output saved to: {output_video_path}")
                print("Note: OpenCV output may have compatibility issues. Install FFmpeg for better results.")
                
            except Exception as e:
                print(f"Fallback also failed: {str(e)}")
                return
                
        except Exception as e:
            print(f"Error running FFmpeg: {str(e)}")
            return

def check_ffmpeg():
    """Check if FFmpeg is available and provide installation instructions if not."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            ffmpeg_version = get_ffmpeg_version()
            
            if ffmpeg_version:
                if ffmpeg_version >= 5:
                    print(f"✓ FFmpeg is available (version {ffmpeg_version}.x) - Full feature support")
                else:
                    print(f"✓ FFmpeg is available (version {ffmpeg_version}.x) - Basic compatibility mode")
            else:
                print("✓ FFmpeg is available (version unknown)")
            return True
        else:
            print("✗ FFmpeg is not working properly")
            return False
    except FileNotFoundError:
        print("✗ FFmpeg not found")
        print("\nTo install FFmpeg:")
        print("  Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg")
        print("  CentOS/RHEL: sudo yum install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        print("  Or use conda: conda install ffmpeg")
        return False

def main():
    # Read configuration from environment variables (set by run.sh)
    import os
    
    print("=== Hunyuan-GameCraft Icon Overlay Generator ===")
    
    # Check FFmpeg availability
    ffmpeg_available = check_ffmpeg()
    if not ffmpeg_available:
        print("\nNote: FFmpeg is recommended for best compatibility.")
        print("The script will fall back to OpenCV if needed.\n")
    
    # Get inputs from environment variables
    input_video = os.environ.get('INPUT_VIDEO', 'home.mp4')
    output_video = os.environ.get('OUTPUT_VIDEO', 'home_icon.mp4')
    action_list_str = os.environ.get('ACTION_LIST', 'w a a a a')

    # input_video = "results/village_w_fp8_distilled_25/village.mp4"
    # output_video = "results/village_w_fp8_distilled_25/village_icon.mp4"
    # action_list_str = "w"

    fps = int(os.environ.get('FPS', '24'))
    
    # Convert action_list string to list
    action_list = action_list_str.split()
    
    # If no environment variables, use defaults
    if input_video == 'home.mp4':
        # Try to find the generated video in the current directory
        video_files = [f for f in os.listdir('.') if f.endswith(('.mp4', '.avi', '.mov', '.mkv')) and not f.endswith('_icon.mp4')]
        if video_files:
            input_video = video_files[0]
            output_video = input_video.replace('.mp4', '_icon.mp4').replace('.avi', '_icon.avi').replace('.mov', '_icon.mov').replace('.mkv', '_icon.mkv')
    
    # Check if input video exists
    if not os.path.exists(input_video):
        print(f"Error: Input video {input_video} not found!")
        print("Available files in current directory:")
        for f in os.listdir('.'):
            if f.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                print(f"  {f}")
        
        # Also check in results subdirectories
        results_dir = "results"
        if os.path.exists(results_dir):
            print(f"\nChecking in {results_dir}/ subdirectories:")
            for subdir in os.listdir(results_dir):
                subdir_path = os.path.join(results_dir, subdir)
                if os.path.isdir(subdir_path):
                    for f in os.listdir(subdir_path):
                        if f.endswith(('.mp4', '.avi', '.mov', '.mkv')) and not f.endswith('_icon.mp4'):
                            print(f"  {subdir_path}/{f}")
        return
    
    print(f"\nConfiguration:")
    print(f"  Input: {input_video}")
    print(f"  Output: {output_video}")
    print(f"  Actions: {action_list}")
    print(f"  FPS: {fps}")
    print(f"  FFmpeg: {'Available' if ffmpeg_available else 'Not available'}")
    print()
    
    # Process the video
    process_video(input_video, output_video, action_list, fps)
    
    print("\nDone!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script to generate HTML report from Hunyuan-GameCraft results folders.
Reads results/ folders and creates an HTML table with images, videos, and parameters.
"""

import os
import json
import glob
from pathlib import Path
import re

def get_image_files(folder_path):
    """Get image files from folder (jpeg, png, jpg)"""
    image_extensions = ['*.jpeg', '*.png', '*.jpg']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(folder_path, ext)))
    return image_files

def get_video_files(folder_path):
    """Get video files from folder (mp4, avi, mov, mkv)"""
    video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv']
    video_files = []
    for ext in video_extensions:
        video_files.extend(glob.glob(os.path.join(folder_path, ext)))
    return video_files

def get_run_sh_content(folder_path):
    """Get content of run.sh file if it exists"""
    run_sh_path = os.path.join(folder_path, 'run.sh')
    if os.path.exists(run_sh_path):
        try:
            with open(run_sh_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading run.sh: {str(e)}"
    return None

def get_data_json_content(folder_path):
    """Get content of data.json file if it exists"""
    data_json_path = os.path.join(folder_path, 'data.json')
    if os.path.exists(data_json_path):
        try:
            with open(data_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return f"Error reading data.json: {str(e)}"
    return None

def generate_html():
    """Generate HTML report from results folders"""
    
    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(base_dir, 'results')
    outputs_dir = os.path.join(base_dir, 'outputs')
    
    # Create outputs directory if it doesn't exist
    os.makedirs(outputs_dir, exist_ok=True)
    
    # HTML template
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hunyuan-GameCraft Results</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
            vertical-align: top;
        }
        th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #495057;
        }
        .image-container {
            width: 12%;
        }
        .image-container img {
            max-width: 120px;
            max-height: 100px;
            border-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            cursor: pointer;
            transition: transform 0.2s ease;
        }
        .image-container img:hover {
            transform: scale(1.05);
        }
        .video-container {
            width: 58%;
        }
        .video-container video {
            width: 100%;
            height: 350px;
            border-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            margin-bottom: 10px;
        }
        .video-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
            font-weight: bold;
        }
        .params-container {
            width: 30%;
            text-align: left;
        }
        .show-btn {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .show-btn:hover {
            background-color: #0056b3;
        }
        .show-btn:disabled {
            background-color: #6c757d;
            cursor: not-allowed;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        .modal-content {
            background-color: white;
            margin: 5% auto;
            padding: 20px;
            border-radius: 8px;
            width: 80%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
        }
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover {
            color: #000;
        }
        .code-block {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            overflow-x: auto;
            max-height: 400px;
            overflow-y: auto;
        }
        .params-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10px;
            font-size: 11px;
        }
        .params-table th, .params-table td {
            border: 1px solid #ddd;
            padding: 4px 6px;
            text-align: left;
        }
        .params-table th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #495057;
        }
        /* Image Modal Styles */
        .image-modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.8);
        }
        .image-modal-content {
            background-color: transparent;
            margin: 5% auto;
            padding: 0;
            border-radius: 8px;
            width: 90%;
            height: 90%;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .image-modal img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }
        .image-close {
            position: absolute;
            top: -40px;
            right: 0;
            color: white;
            font-size: 35px;
            font-weight: bold;
            cursor: pointer;
            background-color: rgba(0,0,0,0.5);
            border-radius: 50%;
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background-color 0.3s ease;
        }
        .image-close:hover {
            background-color: rgba(0,0,0,0.8);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Hunyuan-GameCraft Results Report</h1>
        <table>
            <thead>
                <tr>
                    <th>Image</th>
                    <th>Videos</th>
                    <th>Parameters</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>

    <!-- Modal for showing run.sh content -->
    <div id="runShModal" class="modal">
        <div class="modal-content">
            <span class="close">&times;</span>
            <h2>run.sh Content</h2>
            <div id="runShContent" class="code-block"></div>
        </div>
    </div>

    <!-- Modal for showing images -->
    <div id="imageModal" class="image-modal">
        <div class="image-modal-content">
            <span class="image-close">&times;</span>
            <img id="modalImage" src="" alt="Modal Image">
        </div>
    </div>

    <script>
        // Modal functionality
        var modal = document.getElementById("runShModal");
        var span = document.getElementsByClassName("close")[0];
        
        span.onclick = function() {
            modal.style.display = "none";
        }
        
        window.onclick = function(event) {
            if (event.target == modal) {
                modal.style.display = "none";
            }
        }
        
        function showRunSh(contentId) {
            var content = document.getElementById(contentId).textContent;
            document.getElementById("runShContent").textContent = content;
            modal.style.display = "block";
        }
        
        // Image Modal functionality
        var imageModal = document.getElementById("imageModal");
        var imageClose = document.getElementsByClassName("image-close")[0];
        
        imageClose.onclick = function() {
            imageModal.style.display = "none";
        }
        
        // Close image modal when clicking outside
        imageModal.onclick = function(event) {
            if (event.target == imageModal) {
                imageModal.style.display = "none";
            }
        }
        
        // Close image modal with Escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                imageModal.style.display = "none";
            }
        });
        
        function showImageModal(imageSrc, imageAlt) {
            document.getElementById("modalImage").src = imageSrc;
            document.getElementById("modalImage").alt = imageAlt;
            imageModal.style.display = "block";
        }
    </script>
</body>
</html>
    """
    
    # Check if results directory exists
    if not os.path.exists(results_dir):
        print(f"Results directory not found: {results_dir}")
        return
    
    # Get all subdirectories in results with their creation times
    folders_with_time = []
    for d in os.listdir(results_dir):
        folder_path = os.path.join(results_dir, d)
        if os.path.isdir(folder_path):
            # Get creation time (use mtime as fallback if ctime not available)
            try:
                creation_time = os.path.getctime(folder_path)
            except:
                creation_time = os.path.getmtime(folder_path)
            folders_with_time.append((d, creation_time))
    
    # Sort by creation time in descending order (newest first)
    folders_with_time.sort(key=lambda x: x[1], reverse=True)
    
    table_rows = []
    
    for folder, _ in folders_with_time:
        folder_path = os.path.join(results_dir, folder)
        
        # Get image and video files
        image_files = get_image_files(folder_path)
        video_files = get_video_files(folder_path)
        
        # Skip if no image or no videos
        if len(image_files) == 0 or len(video_files) == 0:
            print(f"Skipping {folder}: Found {len(image_files)} images and {len(video_files)} videos")
            continue
        
        # Use the first image
        image_file = image_files[0]
        
        # Get relative paths for web serving (relative to outputs folder for correct HTTP serving)
        image_rel_path = os.path.relpath(image_file, outputs_dir)
        
        # Debug: Print paths to help troubleshoot
        print(f"Folder: {folder}")
        print(f"  Image file: {image_file}")
        print(f"  Image rel path: {image_rel_path}")
        print(f"  Video files: {video_files}")
        print(f"  Base dir: {base_dir}")
        print(f"  Outputs dir: {outputs_dir}")
        print("---")
        
        # Get run.sh content
        run_sh_content = get_run_sh_content(folder_path)
        
        # Get data.json content
        data_json = get_data_json_content(folder_path)
        
        # Generate parameters table with only specific fields
        params_html = ""
        if data_json:
            params_html = '<table class="params-table">'
            # Only show the specific fields requested
            fields_to_show = ['execution_time_seconds', 'save_path', 'action_list', 'action_speed_list', 'precision', 'model_used', 'image_prompt']
            for field in fields_to_show:
                if field in data_json:
                    value = data_json[field]
                    if field == 'execution_time_seconds':
                        display_value = f"{value}s"
                    elif field == 'save_path':
                        # Extract just the folder name from the full path
                        display_value = os.path.basename(value)
                    else:
                        display_value = str(value)
                    params_html += f'<tr><th>{field}</th><td>{display_value}</td></tr>'
            params_html += '</table>'
        
        # Generate show button
        show_button = ""
        if run_sh_content:
            # Store content in a data attribute to avoid JavaScript injection issues
            content_id = f"content_{len(table_rows)}"
            show_button = f'<button class="show-btn" onclick="showRunSh(\'{content_id}\')">Show run.sh</button>'
            # Store content in a hidden div
            show_button += f'<div id="{content_id}" style="display:none;">{run_sh_content}</div>'
        else:
            show_button = '<button class="show-btn" disabled>No run.sh</button>'
        
        # Generate video HTML - show all videos
        video_html = ""
        for video_file in video_files:
            video_rel_path = os.path.relpath(video_file, outputs_dir)
            video_name = os.path.basename(video_file)
            
            # Determine video label
            if "_icon" in video_name:
                video_label = "With Icons"
            else:
                video_label = "Original"
            
            video_html += f"""
                <div class="video-label">{video_label}</div>
                <video controls preload="metadata">
                    <source src="{video_rel_path}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            """
        
        # Generate table row
        row = f"""
                <tr>
                    <td class="image-container">
                        <img src="{image_rel_path}" alt="Image from {folder}" loading="lazy" onclick="showImageModal('{image_rel_path}', 'Image from {folder}')">
                    </td>
                    <td class="video-container">
                        {video_html}
                    </td>
                    <td class="params-container">
                        {params_html}
                        {show_button}
                    </td>
                </tr>
        """
        table_rows.append(row)
    
    # Generate final HTML
    html_content = html_template.replace('{table_rows}', ''.join(table_rows))
    
    # Write HTML file
    output_file = os.path.join(outputs_dir, 'results_report.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML report generated: {output_file}")
    print(f"Total folders processed: {len(table_rows)}")
    print(f"To view the report, run: python3 -m http.server 3000")
    print(f"Then open: http://localhost:3000/outputs/results_report.html")

if __name__ == "__main__":
    generate_html()

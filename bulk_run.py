#!/usr/bin/env python3
"""
Bulk run script for Hunyuan GameCraft
Reads run.sh, creates temporary versions with modified parameters, and runs them in a loop
"""

import os
import subprocess
import tempfile
import shutil
import time
from pathlib import Path

# Configuration dictionary - modify these values as needed
CONFIGURATIONS = [
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls",
        "action_list": "w d d d",
        "action_speed_list": "0.05 0.05 0.05 0.05"
    },
    {
        "image_name": "das_office2", 
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls",
        "action_list": "w w d d",
        "action_speed_list": "0.03 0.03 0.05 0.05"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "d d w w",
        "action_speed_list": "0.05 0.05 0.03 0.03"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "w d w d w d w d",
        "action_speed_list": "0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "w d w d w d w d d d d d",
        "action_speed_list": "0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "w d w d w d w d",
        "action_speed_list": "0.1 0.1 0.1 0.1 0.1 0.1 0.1 0.1"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "w d w d w d w d",
        "action_speed_list": "0.2 0.2 0.2 0.2 0.2 0.2 0.2 0.2"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "w d w d w d w d",
        "action_speed_list": "1 1 1 1 1 1 1 1"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "s d",
        "action_speed_list": "0.05 0.05"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "s a a a",
        "action_speed_list": "0.1 0.05 0.05 0.05"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "s",
        "action_speed_list": "0.2"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "s",
        "action_speed_list": "2"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "a a a a",
        "action_speed_list": "0.1 0.1 0.1 0.1"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "d d d d",
        "action_speed_list": "0.1 0.1 0.1 0.1"
    },
    {
        "image_name": "das_office2",
        "image_prompt": "A modern glass-walled office with racing posters, sleek furniture, glass walls", 
        "action_list": "w d w d w d w d d d d d s s s d d d",
        "action_speed_list": "0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05 0.05"
    },
]

def read_run_sh():
    """Read the original run.sh file"""
    with open('run.sh', 'r') as f:
        return f.read()

def create_temp_run_sh(content, config):
    """Create a temporary run.sh with modified parameters"""
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False)
    
    # Replace the parameters in the content
    modified_content = content
    
    # Replace image_name
    modified_content = modified_content.replace(
        'image_name="das_office2"',
        f'image_name="{config["image_name"]}"'
    )
    
    # Replace image_prompt
    modified_content = modified_content.replace(
        'image_prompt="A modern glass-walled office with racing posters, sleek furniture, glass walls"',
        f'image_prompt="{config["image_prompt"]}"'
    )
    
    # Replace action_list
    modified_content = modified_content.replace(
        'action_list="w d d d"',
        f'action_list="{config["action_list"]}"'
    )
    
    # Replace action_speed_list
    modified_content = modified_content.replace(
        'action_speed_list="0.05 0.05 0.05 0.05"',
        f'action_speed_list="{config["action_speed_list"]}"'
    )
    
    # Write modified content to temporary file
    temp_file.write(modified_content)
    temp_file.close()
    
    # Make the temporary file executable
    os.chmod(temp_file.name, 0o755)
    
    return temp_file.name

def run_temp_script(temp_script_path):
    """Run the temporary script"""
    print(f"Running temporary script: {temp_script_path}")
    
    try:
        # Run the script
        result = subprocess.run([temp_script_path], 
                              capture_output=True, 
                              text=True, 
                              shell=True)
        
        if result.returncode == 0:
            print("Script completed successfully")
            print("STDOUT:", result.stdout)
        else:
            print(f"Script failed with return code {result.returncode}")
            print("STDERR:", result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running script: {e}")
        return False

def main():
    """Main function to run bulk operations"""
    print("Starting bulk run process...")
    
    # Check if run.sh exists
    if not os.path.exists('run.sh'):
        print("Error: run.sh not found in current directory")
        return
    
    # Read the original run.sh
    original_content = read_run_sh()
    print("Successfully read run.sh")
    
    # Process each configuration
    for i, config in enumerate(CONFIGURATIONS, 1):
        print(f"\n{'='*50}")
        print(f"Processing configuration {i}/{len(CONFIGURATIONS)}")
        print(f"Image: {config['image_name']}")
        print(f"Prompt: {config['image_prompt']}")
        print(f"Actions: {config['action_list']}")
        print(f"Speeds: {config['action_speed_list']}")
        print(f"{'='*50}")
        
        # Create temporary script
        temp_script_path = create_temp_run_sh(original_content, config)
        print(f"Created temporary script: {temp_script_path}")
        
        try:
            # Run the temporary script
            success = run_temp_script(temp_script_path)
            
            if success:
                print(f"Configuration {i} completed successfully")
            else:
                print(f"Configuration {i} failed")
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_script_path)
                print(f"Cleaned up temporary script: {temp_script_path}")
            except Exception as e:
                print(f"Warning: Could not clean up {temp_script_path}: {e}")
        
        # Wait a bit between runs (optional)
        if i < len(CONFIGURATIONS):
            print("Waiting 5 seconds before next configuration...")
            time.sleep(5)
    
    print(f"\n{'='*50}")
    print("Bulk run process completed!")
    print(f"Processed {len(CONFIGURATIONS)} configurations")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()

#!/bin/bash

# Start timing
start_time=$(date +%s)

JOBS_DIR=$(dirname $(dirname "$0"))
export PYTHONPATH=${JOBS_DIR}:$PYTHONPATH
export MODEL_BASE="weights/stdmodels"

# image_path="asset_local/home.jpeg"
# image_prompt="A modern family living room with glossy tiled floors, a cozy sofa, toys scattered around, and warm vibe"
image_name="das_office2"
image_path="asset_local/${image_name}.jpeg"
image_prompt="A modern glass-walled office with racing posters, sleek furniture, glass walls"
nproc_per_node=2
precision="fp16" # fp8, fp16
model_used="original" # distilled, original
action_list="w d d d"
action_list_compressed="${action_list// /}"
action_speed_list="0.05 0.05 0.05 0.05"
seed=$((RANDOM % 10000 + 1))

if [ "$model_used" == "original" ]; then
    checkpoint_path="weights/gamecraft_models/mp_rank_00_model_states.pt"
    infer_steps=50
elif [ "$model_used" == "distilled" ]; then
    checkpoint_path="weights/gamecraft_models/mp_rank_00_model_states_distill.pt"
    infer_steps=8
fi

# Define save path
save_path="./results/${image_name}_${action_list_compressed}_${precision}_${model_used}_${seed}"

# Create save directory if it doesn't exist
mkdir -p "$save_path"

# Copy input image to save-path folder
input_image=${image_path}
if [ -f "$input_image" ]; then
    cp "$input_image" "$save_path/"
    echo "Copied input image to $save_path/"
else
    echo "Warning: Input image $input_image not found"
fi

# Copy current run.sh file to save-path folder
script_path="$0"
if [ -f "$script_path" ]; then
    cp "$script_path" "$save_path/run.sh"
    echo "Copied run.sh to $save_path/run.sh"
else
    echo "Warning: Script file $script_path not found"
fi

# Run the main command
torchrun --nnodes=1 --nproc_per_node=${nproc_per_node} --master_port 29605 hymm_sp/sample_batch.py \
    --image-path ${image_path} \
    --prompt "${image_prompt}" \
    --add-pos-prompt "Realistic, High-quality." \
    --add-neg-prompt "overexposed, low quality, deformation, a poor composition, humans, people, bad hands, bad teeth, bad eyes, bad limbs, distortion, blurring, text, subtitles, static, picture, black border." \
    --ckpt ${checkpoint_path} \
    --video-size 704 1216 \
    --cfg-scale 2.0 \
    --image-start \
    --action-list ${action_list} \
    --action-speed-list ${action_speed_list} \
    --seed ${seed} \
    --infer-steps ${infer_steps} \
    --flow-shift-eval-video 5.0 \
    --save-path "$save_path" \
    $([ "$precision" == "fp8" ] && echo "--use-fp8")

# #fake it
# cp results/dash_office1_sd_fp16_original_6869/dash_office1.mp4 $save_path/${image_name}.mp4

echo "Waiting for video generation to complete..."

# Wait for video files to be created (check for common video extensions)
video_created=false
max_wait_time=3600  # Maximum wait time: 1 hour
wait_interval=10    # Check every 10 seconds
elapsed_wait=0

while [ "$video_created" = false ] && [ $elapsed_wait -lt $max_wait_time ]; do
    # Check for video files with common extensions
    if ls "$save_path"/*.mp4 2>/dev/null | grep -q . || \
       ls "$save_path"/*.avi 2>/dev/null | grep -q . || \
       ls "$save_path"/*.mov 2>/dev/null | grep -q . || \
       ls "$save_path"/*.mkv 2>/dev/null | grep -q .; then
        video_created=true
        echo "Video file detected in $save_path"
    else
        echo "Waiting for video... [${elapsed_wait}s elapsed]"
        sleep $wait_interval
        elapsed_wait=$((elapsed_wait + wait_interval))
    fi
done

if [ "$video_created" = false ]; then
    echo "Warning: No video file detected after waiting ${max_wait_time} seconds"
fi

# Generate icon overlay video
echo "Generating icon overlay video..."

cd "$save_path"
# Find the generated video file
video_file=$(find . -maxdepth 1 -name "*.mp4" -o -name "*.avi" -o -name "*.mov" -o -name "*.mkv" | head -1)
if [ -n "$video_file" ]; then
    # Remove ./ prefix if present
    video_file=$(basename "$video_file")
    
    # Set environment variables for add_icons.py
    export INPUT_VIDEO="$video_file"
    export OUTPUT_VIDEO="${video_file%.*}_icon.${video_file##*.}"
    export ACTION_LIST="$action_list"
    export FPS="24"
    
    echo "Processing video: $video_file"
    echo "Output will be: $OUTPUT_VIDEO"
    echo "Actions: $ACTION_LIST"
    
    # Run add_icons.py
    /home/nitish/anaconda3/envs/HYGameCraft/bin/python ./../../add_icons.py
    
    if [ $? -eq 0 ]; then
        echo "Icon overlay video generated successfully: $OUTPUT_VIDEO"
    else
        echo "Error: Failed to generate icon overlay video"
    fi
else
    echo "Warning: No video file found for icon generation"
fi

# Return to original directory
cd - > /dev/null

# End timing
end_time=$(date +%s)
execution_time=$((end_time - start_time))

# Create data.json with execution information
cat > "$save_path/data.json" << EOF
{
    "execution_time_seconds": $execution_time,
    "start_time": "$(date -d @$start_time)",
    "end_time": "$(date -d @$end_time)",
    "input_image": "$input_image",
    "script_file": "$script_path",
    "checkpoint_path": "$checkpoint_path",
    "save_path": "$save_path",
    "precision": "${precision}",
    "model_used": "${model_used}",
    "action_list": "${action_list}",
    "action_speed_list": "${action_speed_list}",
    "infer_steps": "${infer_steps}",
    "video_created": $video_created,
    "video_files": "$(ls "$save_path"/*.mp4 "$save_path"/*.avi "$save_path"/*.mov "$save_path"/*.mkv 2>/dev/null | tr '\n' ' ' | sed 's/ *$//')",
    "total_wait_time_seconds": $elapsed_wait,
    "seed": ${seed},
    "image_prompt": "${image_prompt}",
    "action_list_compressed": "${action_list_compressed}"
}
EOF

echo "Execution completed in ${execution_time} seconds"
echo "Data saved to $save_path/data.json"

/home/nitish/anaconda3/envs/HYGameCraft/bin/python generate_html.py

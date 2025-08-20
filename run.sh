#!/bin/bash

# Start timing
start_time=$(date +%s)

JOBS_DIR=$(dirname $(dirname "$0"))
export PYTHONPATH=${JOBS_DIR}:$PYTHONPATH
export MODEL_BASE="weights/stdmodels"

image_path="asset_local/home.jpeg"
image_prompt="A modern family living room with glossy tiled floors, a cozy sofa, toys scattered around, and warm vibe"
nproc_per_node=2
precision="fp8" # fp8, fp16
model_used="distilled" # distilled, original
action_list="w a a a a"
action_speed_list="0.05 0.05 0.05 0.1 0.3"
seed=25016

if [ "$model_used" == "original" ]; then
    checkpoint_path="weights/gamecraft_models/mp_rank_00_model_states.pt"
    infer_steps=50
elif [ "$model_used" == "distilled" ]; then
    checkpoint_path="weights/gamecraft_models/mp_rank_00_model_states_distill.pt"
    infer_steps=8
fi

# Define save path
save_path="./results/home_${precision}_${model_used}_${seed}"

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
    cp "$script_path" "$save_path/"
    echo "Copied run.sh to $save_path/"
else
    echo "Warning: Script file $script_path not found"
fi

# Run the main command
torchrun --nnodes=1 --nproc_per_node=${nproc_per_node} --master_port 29605 hymm_sp/sample_batch.py \
    --image-path ${image_path} \
    --prompt "${image_prompt}" \
    --add-pos-prompt "Realistic, High-quality." \
    --add-neg-prompt "overexposed, low quality, deformation, a poor composition, bad hands, bad teeth, bad eyes, bad limbs, distortion, blurring, text, subtitles, static, picture, black border." \
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
        echo "Waiting for video... (${elapsed_wait}s elapsed)"
        sleep $wait_interval
        elapsed_wait=$((elapsed_wait + wait_interval))
    fi
done

if [ "$video_created" = false ]; then
    echo "Warning: No video file detected after waiting ${max_wait_time} seconds"
fi

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
    "total_wait_time_seconds": $elapsed_wait
}
EOF

echo "Execution completed in ${execution_time} seconds"
echo "Data saved to $save_path/data.json"

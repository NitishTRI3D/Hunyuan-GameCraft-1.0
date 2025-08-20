#!/bin/bash
JOBS_DIR=$(dirname $(dirname "$0"))
export PYTHONPATH=${JOBS_DIR}:$PYTHONPATH
export MODEL_BASE="weights/stdmodels"
checkpoint_path="weights/gamecraft_models/mp_rank_00_model_states_distill.pt"


torchrun --nnodes=1 --nproc_per_node=2 --master_port 29605 hymm_sp/sample_batch.py \
    --image-path "asset_local/home.jpeg" \
    --prompt "A modern family living room with glossy tiled floors, a cozy sofa, toys scattered around, and warm vibe" \
    --add-pos-prompt "Realistic, High-quality." \
    --add-neg-prompt "overexposed, low quality, deformation, a poor composition, bad hands, bad teeth, bad eyes, bad limbs, distortion, blurring, text, subtitles, static, picture, black border." \
    --ckpt ${checkpoint_path} \
    --video-size 704 1216 \
    --cfg-scale 2.0 \
    --image-start \
    --action-list w a \
    --action-speed-list 0.05 0.05 \
    --seed 250160 \
    --infer-steps 8 \
    --flow-shift-eval-video 5.0 \
    --save-path './results/home_fp8_distilled_wa' \
    --use-fp8

#!/bin/bash
set -e
if [ "$PLATFORM" = "BM1684X" ]; then
    export LD_LIBRARY_PATH="/opt/sophon/libsophon-current/lib:/opt/sophon/sophon-opencv-latest/lib:/opt/sophon/sophon-ffmpeg-latest/lib:$LD_LIBRARY_PATH"
elif [ "$PLATFORM" = "BM1688_1CORE" ] || [ "$PLATFORM" = "BM1688_2CORE" ]; then
    export LD_LIBRARY_PATH="/opt/sophon/libsophon-current/lib:/opt/sophon/sophon-opencv-latest/lib:/opt/sophon/sophon-ffmpeg-latest/lib:/opt/sophon/sophon-soc-libisp_1.0.0/lib:$LD_LIBRARY_PATH"
else
    echo "error: get ${PLATFORM}, not support platform!" && exit 1
fi

if [ "$PLATFORM" = "BM1684X" ]; then
    exec ./smart_album \
        --image_model ./models/BM1684X/cn_clip_image_vit_h_14_bm1684x_f16_1b.bmodel \
        --text_model ./models/BM1684X/cn_clip_text_vit_h_14_bm1684x_f16_1b.bmodel \
        --bce_model ./models/BM1684X/text2vec_base_chinese_bm1684x_f16_1b.bmodel \
        --dev_id 0
elif [ "$PLATFORM" = "BM1688_1CORE" ]; then
    exec ./smart_album \
        --image_model ./models/BM1688_1CORE/cn_clip_image_vit_h_14_bm1688_f16_1b.bmodel \
        --text_model ./models/BM1688_1CORE/cn_clip_text_vit_h_14_bm1688_f16_1b.bmodel \
        --bce_model ./models/BM1688_1CORE/text2vec_base_chinese_bm1688_f16_1b.bmodel \
        --dev_id 0
elif [ "$PLATFORM" = "BM1688_2CORE" ]; then
    exec ./smart_album \
        --image_model ./models/BM1688_2CORE/cn_clip_image_vit_h_14_bm1688_f16_1b_2core.bmodel \
        --text_model ./models/BM1688_2CORE/cn_clip_text_vit_h_14_bm1688_f16_1b_2core.bmodel \
        --bce_model ./models/BM1688_2CORE/text2vec_base_chinese_bm1688_f16_1b_2core.bmodel \
        --dev_id 0
else
    echo "error: get ${PLATFORM}, not support platform!"
    exit 1
fi

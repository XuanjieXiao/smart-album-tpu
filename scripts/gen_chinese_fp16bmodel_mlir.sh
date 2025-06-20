#!/bin/bash
model_dir=$(dirname $(readlink -f "$0"))

if [ ! $1 ]; then
    target=bm1684x
    target_dir=BM1684X
else
    target=${1,,}
    target_dir=${target^^}
    if test $target = "bm1684"
    then
        echo "bm1684 do not support fp16"
        exit
    fi
fi

outdir=../models/$target_dir
function gen_image_encode_mlir()
{
    model_transform.py \
      --model_name cn_clip_image_vit_h_14 \
      --model_def ../models/onnx/vit-h-14.img.fp32.onnx \
      --input_shapes [[$1,3,224,224]] \
      --pixel_format rgb \
      --mlir cn_clip_image_vit_h_14_$1b.mlir
}

function gen_image_encode_fp16bmodel()
{
    model_deploy.py \
        --mlir cn_clip_image_vit_h_14_$1b.mlir \
        --quantize F16 \
        --chip $target \
        --model ./cn_clip_image_vit_h_14_${target}_f16_$1b.bmodel

    mv ./cn_clip_image_vit_h_14_${target}_f16_$1b.bmodel $outdir/

    if test $target = "bm1688";then
        model_deploy.py \
            --mlir cn_clip_image_vit_h_14_$1b.mlir \
            --quantize F16 \
            --chip $target \
            --model cn_clip_image_vit_h_14_${target}_f16_$1b_2core.bmodel \
            --num_core 2
        mv cn_clip_image_vit_h_14_${target}_f16_$1b_2core.bmodel $outdir/
    fi
}

function gen_text_encoder_mlir()
{
    model_transform.py \
      --model_name cn_clip_text_vit_h_14 \
      --model_def ../models/onnx/vit-h-14.txt.fp32.onnx \
      --input_shapes [[$1,52]] \
      --pixel_format rgb \
      --mlir cn_clip_text_vit_h_14_$1b.mlir
}

function gen_text_encoder_fp16bmodel() {
    model_deploy.py \
        --mlir cn_clip_text_vit_h_14_$1b.mlir \
        --quantize F16 \
        --chip $target \
        --model ./cn_clip_text_vit_h_14_${target}_f16_$1b.bmodel

    mv ./cn_clip_text_vit_h_14_${target}_f16_$1b.bmodel $outdir/
    
    if test $target = "bm1688"; then
        model_deploy.py \
            --mlir cn_clip_text_vit_h_14_$1b.mlir \
            --quantize F16 \
            --chip $target \
            --model cn_clip_text_vit_h_14_${target}_f16_$1b_2core.bmodel \
            --num_core 2
        mv cn_clip_text_vit_h_14_${target}_f16_$1b_2core.bmodel $outdir/
    fi
}

pushd $model_dir
if [ ! -d $outdir ]; then
    mkdir -p $outdir
fi

# batch_size=1
# image encode
gen_image_encode_mlir 1
gen_image_encode_fp16bmodel 1
# text encode
gen_text_encoder_mlir 1
gen_text_encoder_fp16bmodel 1


# batch_size=4

# gen_image_encode_mlir 4
# gen_image_encode_fp16bmodel 4
# gen_text_encoder_mlir 4
# gen_text_encoder_fp16bmodel 4

popd
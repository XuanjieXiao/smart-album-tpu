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
function gen_embedding_encode_mlir()
{
    model_transform.py \
      --model_name text2vec_base_chinese \
      --model_def ../models/onnx/text2vec_base_chinese.onnx \
      --input_shapes [[$1,512],[$1,512]] \
      --mlir text2vec_base_chinese_$1b.mlir \
      --debug
}

function gen_embedding_encode_fp16bmodel()
{
    model_deploy.py \
        --mlir text2vec_base_chinese_$1b.mlir \
        --quantize F16 \
        --chip $target \
        --model ./text2vec_base_chinese_${target}_f16_$1b.bmodel

    mv ./text2vec_base_chinese_${target}_f16_$1b.bmodel $outdir/

    if test $target = "bm1688";then
        model_deploy.py \
            --mlir text2vec_base_chinese_$1b.mlir \
            --quantize F16 \
            --chip $target \
            --model text2vec_base_chinese_${target}_f16_$1b_2core.bmodel \
            --num_core 2
        mv text2vec_base_chinese_${target}_f16_$1b_2core.bmodel $outdir/
    fi
}

pushd $model_dir
if [ ! -d $outdir ]; then
    mkdir -p $outdir
fi

# batch_size=1
# embedding encode
gen_embedding_encode_mlir 1
gen_embedding_encode_fp16bmodel 1

popd
#===----------------------------------------------------------------------===#
#
# Copyright (C) 2022 Sophgo Technologies Inc.  All rights reserved.
#
# SOPHON-DEMO is licensed under the 2-Clause BSD License except for the
# third-party components.
#
#===----------------------------------------------------------------------===#
from .bert_tokenizer import FullTokenizer
_tokenizer = FullTokenizer()
from .utils import tokenize
from .clip import CLIP

def load(image_model, text_model, dev_id):
    model = CLIP(image_model, text_model, dev_id)
    return model, model.preprocess
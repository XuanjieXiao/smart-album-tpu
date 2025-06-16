#===----------------------------------------------------------------------===#
#
# Copyright (C) 2022 Sophgo Technologies Inc.  All rights reserved.
#
# SOPHON-DEMO is licensed under the 2-Clause BSD License except for the
# third-party components.
#
#===----------------------------------------------------------------------===#

from .bce_embedding import BCEEmbedding
__all__ = ["BCEEmbedding"]

def load(bce_model, dev_id):
    """
    初始化BCE模型。
    """
    bce_service = BCEEmbedding(bce_model, dev_id)
    return bce_service


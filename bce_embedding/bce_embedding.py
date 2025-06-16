#===----------------------------------------------------------------------===#
#
# Copyright (C) 2022 Sophgo Technologies Inc.  All rights reserved.
#
# SOPHON-DEMO is licensed under the 2-Clause BSD License except for the
# third-party components.
#
#===----------------------------------------------------------------------===#
import numpy as np
import os
import time
from transformers import BertTokenizer

import sophon.sail as sail
import logging
logging.basicConfig(level=logging.INFO)

# 加载 tokenizer
tokenizer_path = '/data/xuanjiexiao/xuanjiexiao/smart-album-tpu/models/shibing624/text2vec-base-chinese'

class BCEEmbedding:
    def __init__(self, bce_model, dev_id):
        # bce bmodel
        self.bce_net = sail.Engine(bce_model, dev_id, sail.IOMode.SYSIO)
        logging.info("load {} success!".format(bce_model))
        self.bce_net_graph_name = self.bce_net.get_graph_names()[0]
        self.bce_net_input_name_0 = self.bce_net.get_input_names(self.bce_net_graph_name)[0]
        self.bce_net_input_name_1 = self.bce_net.get_input_names(self.bce_net_graph_name)[1]
        self.bce_net_output_name = self.bce_net.get_output_names(self.bce_net_graph_name)[0]
        self.bce_net_input_shape_0 = self.bce_net.get_input_shape(self.bce_net_graph_name, self.bce_net_input_name_0)
        self.bce_net_input_shape_1 = self.bce_net.get_input_shape(self.bce_net_graph_name, self.bce_net_input_name_1)
        self.bce_net_output_shape = self.bce_net.get_output_shape(self.bce_net_graph_name, self.bce_net_output_name)
        self.bce_net_batch_size = self.bce_net_input_shape_0[0]

        self.embed_dim = self.bce_net_output_shape[1] # 768 for text2vec_base_chinese

        self.encode_text_time = 0.0
        self.tokenizer = BertTokenizer.from_pretrained(tokenizer_path)
    
    def pad_to_512(self, arr):
        pad_width = 512 - arr.shape[1]
        if pad_width > 0:
            return np.pad(arr, pad_width=((0, 0), (0, pad_width)), mode='constant', constant_values=0)
        return arr[:, :512]  # 如果长度大于512则截断

    def get_bce_embedding(self, text):
        self.start_time = time.time()
        inputs = self.tokenizer(text, return_tensors='np', padding='max_length', truncation=True, max_length=32)
        
        input_ids_padded = self.pad_to_512(inputs['input_ids'])
        attention_mask_padded = self.pad_to_512(inputs['attention_mask'])

        bce_inputs = {
            self.bce_net_input_name_0: input_ids_padded,
            self.bce_net_input_name_1: attention_mask_padded
        }
        output = self.bce_net.process(self.bce_net_graph_name, bce_inputs)[self.bce_net_output_name]
        self.encode_text_time = time.time() - self.start_time
        logging.info(f"Encode text time: {self.encode_text_time:.4f} seconds")
        output = output[0]
        return output / np.linalg.norm(output)

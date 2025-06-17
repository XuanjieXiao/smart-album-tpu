import torch
import torch.nn as nn
from transformers import BertModel, BertTokenizer

class MeanPoolingBert(nn.Module):
    def __init__(self, model_name='shibing624/text2vec-base-chinese'):
        super(MeanPoolingBert, self).__init__()
        self.bert = BertModel.from_pretrained(model_name)

    def forward(self, input_ids, attention_mask):
        output = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        token_embeddings = output[0]  # [batch_size, seq_len, hidden_size]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)
        sum_mask = input_mask_expanded.sum(dim=1).clamp(min=1e-9)
        return sum_embeddings / sum_mask  # shape: [batch_size, hidden_size]

# 实例化模型
model = MeanPoolingBert()
model.eval()

# 创建示例输入
tokenizer = BertTokenizer.from_pretrained('/data/xuanjiexiao/SmartAlbumFiles/Smart-Album/models/shibing624/text2vec-base-chinese')
sample = tokenizer("这是用于导出ONNX的文本", return_tensors="pt", padding='max_length', truncation=True, max_length=512)
input_ids = sample['input_ids']
attention_mask = sample['attention_mask']

# 导出 ONNX 模型
torch.onnx.export(
    model,
    (input_ids, attention_mask),
    "text2vec_base_chinese.onnx",
    input_names=["input_ids", "attention_mask"],
    output_names=["sentence_embedding"],
    dynamic_axes={
        "input_ids": {0: "batch_size", 1: "seq_len"},
        "attention_mask": {0: "batch_size", 1: "seq_len"},
        "sentence_embedding": {0: "batch_size"},
    },
    opset_version=14
)

print("✅ 成功导出为 text2vec_base_chinese.onnx")

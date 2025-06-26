from typing import Union, List
import numpy as np
from clip import _tokenizer
__all__ = ["tokenize"]

def tokenize(texts: Union[str, List[str]], context_length: int = 52) -> np.ndarray:
    """
    NumPy version of tokenize function, returns tokenized representation as ndarray
    """
    if isinstance(texts, str):
        texts = [texts]

    all_tokens = []
    for text in texts:
        # [CLS] + token_ids[:context_length-2] + [SEP]
        token_ids = _tokenizer.convert_tokens_to_ids(_tokenizer.tokenize(text))
        tokens = [_tokenizer.vocab['[CLS]']] + token_ids[:context_length - 2] + [_tokenizer.vocab['[SEP]']]
        all_tokens.append(tokens)

    result = np.zeros((len(all_tokens), context_length), dtype=np.int64)

    for i, tokens in enumerate(all_tokens):
        if len(tokens) > context_length:
            raise ValueError("Tokenized input is longer than context_length.")
        result[i, :len(tokens)] = tokens

    return result

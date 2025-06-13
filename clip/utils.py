# Code modified from https://github.com/openai/CLIP

import json
import os
from pathlib import Path
from typing import Union, List
import urllib

import torch
from torchvision.transforms import Compose, ToTensor, Normalize, Resize, InterpolationMode
from tqdm import tqdm

from clip import _tokenizer

__all__ = ["tokenize", "image_transform"]


def _convert_image_to_rgb(image):
    return image.convert("RGB")

def tokenize(texts: Union[str, List[str]], context_length: int = 52) -> torch.LongTensor:
    """
    Returns the tokenized representation of given input string(s)
    Parameters
    ----------
    texts : Union[str, List[str]]
        An input string or a list of input strings to tokenize
    context_length : int
        The context length to use; all baseline models use 52 as the context length
    Returns
    -------
    A two-dimensional tensor containing the resulting tokens, shape = [number of input strings, context_length]
    """
    if isinstance(texts, str):
        texts = [texts]

    all_tokens = []
    for text in texts:
        all_tokens.append([_tokenizer.vocab['[CLS]']] + _tokenizer.convert_tokens_to_ids(_tokenizer.tokenize(text))[
                                                        :context_length - 2] + [_tokenizer.vocab['[SEP]']])

    result = torch.zeros(len(all_tokens), context_length, dtype=torch.long)

    for i, tokens in enumerate(all_tokens):
        assert len(tokens) <= context_length
        result[i, :len(tokens)] = torch.tensor(tokens)

    return result


def _convert_to_rgb(image):
    return image.convert('RGB')


def image_transform(image_size=224):
    transform = Compose([
        Resize((image_size, image_size), interpolation=InterpolationMode.BICUBIC),
        _convert_to_rgb,
        ToTensor(),
        Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711)),
    ])
    return transform


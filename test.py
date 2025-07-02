import base64
from openai import OpenAI

url = "http://172.24.12.226:10900/v1"
api_key = "null"
vlm_model = "qwen2.5-vl-3b"
prompt = "描述这个图片"
image_path = "/data/xuanjiexiao/xuanjiexiao/smart-album-tpu/uploads/047fa9e7-877c-46f8-a8cd-fb96c4ee355e.jpg"
vlm_client = OpenAI(base_url=url,api_key=api_key)

completion_vlm = vlm_client.chat.completions.create(
                model=vlm_model,
                messages=[
                    {"role": "user",   
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64.b64encode(open(image_path, 'rb').read()).decode()}"
                                }
                            }
                        ]
                    },
                ],
                stream=False)
                
vlm_result_str = completion_vlm.choices[0].message[0].content

print(f"VLM Result: {vlm_result_str}")

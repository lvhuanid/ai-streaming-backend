from openai import OpenAI

client = OpenAI(
    api_key="MODELSCOPE_ACCESS_TOKEN", # 请替换成您的ModelScope Access Token
    base_url="https://api-inference.modelscope.cn/v1/"
)


response = client.chat.completions.create(
    model="Qwen/Qwen3.5-35B-A3B", # ModelScope Model-Id
    messages=[
        {
            'role': 'system',
            'content': 'You are a helpful assistant.'
        },
        {
            'role': 'user',
            'content': '用python写一下快排'
        }
    ],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content, end='', flush=True)
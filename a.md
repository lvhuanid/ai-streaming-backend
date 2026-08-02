# 创建 .venv 目录（默认使用系统最新 Python 或指定版本）
uv venv

# （可选）指定 Python 版本创建环境
uv venv --python 3.11

# 直接根据 requirements.txt 安装依赖到当前 .venv 中
uv pip install -r requirements.txt

uv run uvicorn app.main:app --reload
# 部署指南

## 方式一：Streamlit 本地开发（推荐）

在项目根目录执行：

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

pip install -r requirements.txt
pip install streamlit-agraph
cp .env.example .env
# 编辑 .env 填入 LLM API Key

streamlit run streamlit_app.py
# 访问 http://localhost:8501/
```

## 方式二：FastAPI 服务

```bash
pip install -r requirements.txt
cp .env.example .env

python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
# 文档 http://localhost:8000/docs
```

更多说明见项目根目录 [`README.md`](../README.md)。

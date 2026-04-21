Installed python code as package wit
uv pip install -e . from root of the project
Notes:
- Do not use this app only as API! FastAPI docs are unable to process StreamingResponses - use curl or streamlit frontend! 

1. Add API_URL in .env file of project repo
2. To run app uv run uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000 for now and uv run streamlit run src/frontend/chatbot_page.py  
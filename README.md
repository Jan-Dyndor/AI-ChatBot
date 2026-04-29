Installed python code as package wit
uv pip install -e . from root of the project
Notes:
- Do not use this app only as API! FastAPI docs are unable to process StreamingResponses - use curl or streamlit frontend! 

1. Add API_URL in .env file of project repo
2. To run app 

backedn: uv run uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000 --no-access-log

Frontend: uv run streamlit run src/frontend/chatbot_page.py  

Current Scope of Project:
- Pydantic .env reading
- Ollama AI bot streaming responses 
- Streamilt frontend that sends POSTs request to FastAPI endpoint. Streamlit for now takes care of whole history of chat between user-bot 
- Logging middleware that also adds ID to header fro future tracing in case of microservices 
- tests 
- Clean layer architecture 
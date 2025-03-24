from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel  # Import BaseModel for request body
import openai
import requests
import json
import logging

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for development only)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Set OpenAI API key
openai.api_key = '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'

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Predefined questions
PREDEFINED_QUESTIONS = [
    "What is the purpose of this grant?",
    "Who is eligible to apply for this grant?",
    "What is the total funding amount available?",
    "What is the maximum and minimum funding amount per applicant?",
    "What is the deadline for submitting the application?",
    "What documents are required for the application?",
    "What are the evaluation criteria for this grant?",
    "Are there any restrictions on how the grant money can be used?",
    "Who is the contact person or organization for more information?",
    "Are there any post-award reporting requirements?"
]

# Define a Pydantic model for the request body
class GetAnswersRequest(BaseModel):
    api_endpoint: str

# Function to fetch data from the API endpoint
def fetch_data_from_api(api_endpoint: str):
    try:
        response = requests.get(api_endpoint)
        response.raise_for_status()  # Raise an error for bad status codes
        if response.headers['Content-Type'] == 'application/json':
            return response.json()
        else:
            return response.text
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch data from API: {str(e)}")

# Function to ask GPT-3.5 or GPT-4 based on file content
def ask_gpt(question: str, file_content: str):
    # Construct the prompt with the file content and the question
    prompt = f"Based on the following document content, answer the question:\n\n{file_content}\n\nQuestion: {question}\nAnswer:"
    
    # Format the messages for the chat model
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
    
    # Call the GPT chat model using the chat/completions endpoint
    response = openai.ChatCompletion.create(
        model="gpt-4",  # or "gpt-3.5-turbo"
        messages=messages,
        max_tokens=500,
        temperature=0.5
    )

    # Extract the answer from the response
    answer = response['choices'][0]['message']['content'].strip()
    return answer

# Homepage with form to input API endpoint
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Endpoint to fetch data from the API and answer predefined questions
@app.post("/fetch_and_answer")
async def fetch_and_answer(api_endpoint: str = Form(...)):
    try:
        # Fetch data from the API endpoint
        file_content = fetch_data_from_api(api_endpoint)

        # Answer predefined questions
        predefined_answers = {}
        for question in PREDEFINED_QUESTIONS:
            answer = ask_gpt(question, file_content)
            predefined_answers[question] = answer

        return JSONResponse(content={
            "message": "Data fetched and predefined questions answered successfully",
            "file_content": file_content,
            "predefined_answers": predefined_answers
        })
    except HTTPException as e:
        return JSONResponse(content={"error": e.detail}, status_code=e.status_code)

# Endpoint to answer user-defined questions
@app.post("/ask_question")
async def ask_question(question: str = Form(...), file_content: str = Form(...)):
    if not question or not file_content:
        return JSONResponse(content={"error": "Missing question or file content"}, status_code=400)

    answer = ask_gpt(question, file_content)
    return JSONResponse(content={"answer": answer})

# Downstream API endpoint for external systems
@app.post("/api/get_answers")
async def get_answers(request: GetAnswersRequest):  # Use the Pydantic model here
    try:
        # Fetch data from the API endpoint
        file_content = fetch_data_from_api(request.api_endpoint)  # Access api_endpoint from the request body

        # Answer predefined questions
        predefined_answers = {}
        for question in PREDEFINED_QUESTIONS:
            answer = ask_gpt(question, file_content)
            predefined_answers[question] = answer

        # Return the answers in a structured format
        return JSONResponse(content={
            "status": "success",
            "data": {
                "file_content": file_content,
                "predefined_answers": predefined_answers
            }
        })
    except HTTPException as e:
        return JSONResponse(content={"status": "error", "message": e.detail}, status_code=e.status_code)

# Run the FastAPI application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

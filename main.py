import os
import io
import json
import traceback
from typing import List
from dotenv import load_dotenv
from pypdf import PdfReader
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from openai import OpenAI

load_dotenv()

groq_key = os.getenv("GROQ_API_KEY")
if not groq_key:
    raise RuntimeError("GROQ_API_KEY is missing! Add GROQ_API_KEY=gsk_... to your .env file.")

app = FastAPI(title="SyllabusPulse - Adaptive Weak-Spot Simulator")

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Groq OpenAI-compatible client
client = OpenAI(
    api_key=groq_key,
    base_url="https://api.groq.com/openai/v1",
    timeout=20.0,
)

MODELS_TO_TRY = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant",
]

SESSION_STORE = {
    "pdf_text": "",
    "filename": ""
}


# --- Pydantic Schemas ---

class MCQItem(BaseModel):
    id: int
    unit: str = Field(description="Topic or unit name from the syllabus PDF")
    page_ref: int = Field(description="Exact page number where this concept appears")
    question: str
    options: List[str] = Field(description="Exactly 4 distinct choices")
    correct_index: int = Field(description="0-based index of the right option (0 to 3)")
    misconception_note: str = Field(description="Why a student typically picks a wrong option for this concept")


class QuizResponse(BaseModel):
    questions: List[MCQItem]


class FixItRequest(BaseModel):
    weak_units: List[str]
    missed_questions: List[str]


class FixItResponse(BaseModel):
    unit: str
    easy_summary_points: List[str]
    analogy: str
    redemption_quiz: List[MCQItem]


# --- Helper: Extract Page-Tagged Text ---
def extract_pdf_with_pages(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_content = []
    for i, page in enumerate(reader.pages[:15], start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages_content.append(f"--- [PAGE {i}] ---\n{text}")
    return "\n\n".join(pages_content)


# --- Helper: Generate Guaranteed JSON via Groq ---
def generate_json_with_groq(prompt: str, schema_cls):
    schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
    system_msg = (
        "You are an expert university exam and remediation engine. "
        "You MUST return ONLY valid JSON matching this exact JSON Schema—no markdown, no extra text:\n"
        f"{schema_json}"
    )

    last_err = None
    for model_name in MODELS_TO_TRY:
        try:
            print(f"[SyllabusPulse] Trying Groq model: {model_name}...")
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            raw = completion.choices[0].message.content
            validated = schema_cls.model_validate_json(raw)
            print(f"[SyllabusPulse] Success with {model_name}!")
            return validated.model_dump()
        except Exception as e:
            last_err = e
            print(f"[SyllabusPulse] {model_name} failed: {e}")
            continue

    raise last_err


# --- API Endpoints ---

@app.get("/")
def serve_home():
    return FileResponse("static/index.html")


@app.post("/api/upload-and-generate")
async def upload_and_generate(file: UploadFile = File(...), num_questions: int = 6):
    try:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            return JSONResponse(status_code=400, content={"detail": "Please upload a valid PDF file."})

        file_bytes = await file.read()
        extracted_text = extract_pdf_with_pages(file_bytes)

        if len(extracted_text) < 100:
            return JSONResponse(
                status_code=400,
                content={"detail": "Could not extract enough readable text from this PDF."}
            )

        SESSION_STORE["pdf_text"] = extracted_text
        SESSION_STORE["filename"] = file.filename

        prompt = f"""
        Analyze the following syllabus/lecture notes (tagged with [PAGE X]) and generate {num_questions} diagnostic
        multiple-choice questions across 3 distinct syllabus units/topics found in the text.

        Rules:
        - Output JSON with top-level key "questions" containing {num_questions} items.
        - Group questions cleanly under 3 clear unit/topic names.
        - Each item must have: id (int), unit (str), page_ref (int), question (str), options (list of 4 strings),
          correct_index (int 0-3), misconception_note (str).
        - Cite the exact [PAGE X] number for every question.

        COURSE MATERIAL:
        {extracted_text[:14000]}
        """

        return generate_json_with_groq(prompt, QuizResponse)

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Backend Error: {str(e)}"})


@app.post("/api/fix-weak-spot")
async def fix_weak_spot(req: FixItRequest):
    try:
        if not SESSION_STORE["pdf_text"]:
            return JSONResponse(
                status_code=400,
                content={"detail": "No PDF uploaded in current session. Please upload a PDF first."}
            )

        target_unit = req.weak_units[0] if req.weak_units else "Core Concepts"

        prompt = f"""
        A student failed questions in the syllabus unit: "{target_unit}".
        Specifically, they struggled with: {req.missed_questions}

        Using the course material below, return JSON with keys:
        - "unit": "{target_unit}"
        - "easy_summary_points": list of 4-5 ultra-clear, jargon-free bullet point strings
        - "analogy": one memorable everyday analogy string
        - "redemption_quiz": list of 3 fresh MCQ objects (each with id, unit, page_ref, question, options [4 strings], correct_index [0-3], misconception_note)

        COURSE MATERIAL:
        {SESSION_STORE["pdf_text"][:14000]}
        """

        return generate_json_with_groq(prompt, FixItResponse)

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Backend Error: {str(e)}"})
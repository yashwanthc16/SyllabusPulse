# SyllabusPulse — Adaptive Weak-Spot & Exam Simulator

**SyllabusPulse** is an AI-powered diagnostic and closed-loop remedial learning platform built for university students. Instead of acting as a generic PDF chatbot, it extracts syllabus units from lecture notes, generates page-grounded diagnostic tests, classifies conceptual gaps into **Red / Amber / Green** mastery tiers, diagnoses student misconceptions, and provides targeted **Fix-It Micro-Lessons** with a redemption drill to flip **Red → Green**.

---

## Key Features

- **Page-Grounded Diagnostic Generation:** Extracts text with `[PAGE X]` tags from uploaded lecture PDFs and builds syllabus-aligned MCQs using strict Pydantic JSON schemas.
- **Unit Mastery Radar (Red / Amber / Green):** Automatically categorizes each syllabus topic based on diagnostic accuracy (`< 50%` Red, `50–79%` Amber, `80%+` Green).
- **Misconception Diagnosis:** Explains the exact faulty mental model or trap behind each missed question along with its PDF page citation.
- **Closed-Loop Fix-It Mode:** Generates jargon-free bullet points, an everyday real-world analogy, a downloadable revision sheet, and a 3-question redemption drill that flips a unit from **Red → Green** once mastered.

---

## Tech Stack

- **Backend:** Python, FastAPI, Pydantic, PyPDF
- **AI Inference:** Groq API (`llama-3.3-70b-versatile` with automatic multi-model fallback)
- **Frontend:** HTML5, Vanilla JavaScript, Tailwind CSS

---

## Local Setup & Run Instructions

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/](https://github.com/)<your-username>/syllabus-pulse.git
   cd syllabus-pulse
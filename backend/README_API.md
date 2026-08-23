# Resume Processor API

## Overview

The Resume Processor is a class-based API for parsing and screening resumes using LLMs (Groq + Instructor). It's designed for easy integration with Flask/FastAPI backends.

**✨ New: Two-level caching with Supabase!** Cache parsed resumes and screening results to save time and API costs. 

## Architecture

```
main.py
├── ResumeExtractor (handles file I/O)
│   ├── extract_text_from_file() - from file path
│   └── extract_text_from_bytes() - from uploaded files
│
└── ResumeProcessor (main API class)
    ├── parse_resume_from_path()
    ├── parse_resume_from_bytes()
    ├── screen_resume()
    ├── process_resume_from_path()
    └── process_resume_from_bytes()
```

## Usage

### 1. Basic Parsing

```python
from main import ResumeProcessor

processor = ResumeProcessor()

# From file path
parsed = processor.parse_resume_from_path("resume.pdf")

# From uploaded bytes (Flask example)
file_bytes = request.files['file'].read()
filename = request.files['file'].filename
parsed = processor.parse_resume_from_bytes(file_bytes, filename)
```

### 2. Screening Only (with pre-parsed resume)

```python
screened = processor.screen_resume(
    parsed_resume=parsed_data,
    job_title="Senior Software Engineer",
    job_description="5+ years experience...",
    weights={  # Optional
        'skills': 0.30,
        'experience': 0.25,
        'education': 0.15,
        'projects': 0.15,
        'certifications': 0.10,
        'cultural_fit': 0.05
    }
)
```

### 3. Complete Workflow (Parse + Screen)

```python
# From file path
result = processor.process_resume_from_path(
    file_path="resume.pdf",
    job_title="Senior Software Engineer",
    job_description="5+ years experience..."
)

# From uploaded bytes (Flask example)
result = processor.process_resume_from_bytes(
    file_bytes=file_bytes,
    filename=filename,
    job_title="Senior Software Engineer",
    job_description="5+ years experience..."
)

# Result structure
{
    "parsed": {
        "full_name": "John Doe",
        "email": "john@example.com",
        "skills": [...],
        "work_experience": [...],
        ...
    },
    "screened": {
        "overall_score": 8.5,
        "recommendation": "Strong Match",
        "summary": "...",
        "skill_match": {...},
        "experience_match": {...},
        "strengths": [...],
        "concerns": [...],
        ...
    }
}
```

## Flask Integration

See `app.py` for a complete Flask example with two endpoints:

### POST /api/parse
Upload a resume for parsing only.

**Request:**
```bash
curl -X POST http://localhost:5000/api/parse \
  -F "file=@resume.pdf"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "full_name": "John Doe",
    "email": "john@example.com",
    ...
  }
}
```

### POST /api/screen
Upload a resume and screen against job requirements.

**Request:**
```bash
curl -X POST http://localhost:5000/api/screen \
  -F "file=@resume.pdf" \
  -F "job_title=Senior Software Engineer" \
  -F "job_description=5+ years experience with Python..."
```

**Response:**
```json
{
  "success": true,
  "data": {
    "parsed": {...},
    "screened": {
      "overall_score": 8.5,
      "recommendation": "Strong Match",
      ...
    }
  }
}
```

## Running the Flask App

```bash
# Install dependencies
pip install flask

# Run the server
python app.py

# Server will start on http://localhost:5000
```

## Testing from Command Line

```bash
# Parse only
python main.py

# Parse + Screen
python main.py screen
```

## Configuration

Initialize with custom models:

```python
processor = ResumeProcessor(
    parser_model="llama-3.3-70b-versatile",
    screener_model="llama-3.3-70b-versatile"
)
```

## Environment Variables

Create a `.env` file:

```
GROQ_API_KEY=your_groq_api_key_here
```

## Supported File Formats

- PDF (.pdf)
- Microsoft Word (.docx, .doc)

## Error Handling

All methods raise exceptions on error:
- `FileNotFoundError` - File not found
- `ValueError` - Unsupported file format
- `Exception` - Parsing/screening errors

Handle them appropriately in your Flask routes.

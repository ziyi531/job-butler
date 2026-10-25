import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.app.config import settings, BASE_DIR
from backend.app.services import email_service, rag_service, llm_service

app = FastAPI(
    title="Butler Agent API",
    description="Backend API for job hunter email monitoring and RAG-based interview coach.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REQUEST/RESPONSE SCHEMAS ---

class JDInput(BaseModel):
    jd_text: str

class SettingsUpdate(BaseModel):
    llm_provider: str
    gemini_api_key: Optional[str] = None
    gemini_api_base: Optional[str] = None
    gemini_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None
    openai_model: Optional[str] = None
    email_imap_server: Optional[str] = None
    email_address: Optional[str] = None
    email_password: Optional[str] = None
    http_proxy: Optional[str] = None

class ProjectCreate(BaseModel):
    filename: str  # e.g., "new_project" (without extension)
    content: str   # Markdown string

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"message": "Butler Agent Backend API is running."}

@app.post("/emails/sync")
def sync_emails():
    """Trigger manual email fetch & classification."""
    try:
        emails = email_service.sync_emails()
        return {"status": "success", "count": len(emails), "emails": emails}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync emails: {str(e)}")

@app.get("/emails")
def get_emails(category: Optional[str] = None):
    """Retrieve pre-classified emails from cache."""
    emails = email_service.load_cached_emails()
    # If cache is completely empty, auto-sync once
    if not emails:
        emails = email_service.sync_emails()
        
    if category:
        emails = [e for e in emails if e.get("category") == category]
    return emails

@app.get("/projects")
def list_projects():
    """List all project markdown files in knowledge base."""
    kb_path = os.path.join(settings.PROJECTS_KB_DIR)
    if not os.path.exists(kb_path):
        return []
    
    projects = []
    for file in os.listdir(kb_path):
        if file.endswith(".md"):
            filepath = os.path.join(kb_path, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            projects.append({
                "name": file[:-3], # strip .md
                "filename": file,
                "content": content
            })
    return projects

@app.post("/projects")
def create_project(project: ProjectCreate):
    """Create or update a project markdown document."""
    # Clean filename
    clean_name = "".join([c for c in project.filename if c.isalnum() or c in ("-", "_")])
    if not clean_name:
        raise HTTPException(status_code=400, detail="Invalid project filename")
    
    filepath = os.path.join(settings.PROJECTS_KB_DIR, f"{clean_name}.md")
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(project.content)
        return {"status": "success", "message": f"Saved {clean_name}.md successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save project: {str(e)}")

@app.post("/projects/index")
def index_projects():
    """Trigger chunking and embedding generation for all project documents."""
    try:
        result = rag_service.index_projects()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebuild RAG index: {str(e)}")

@app.post("/match")
def match_jd(data: JDInput):
    """Analyze JD, query project RAG database, and generate interview preparation guides."""
    if not data.jd_text.strip():
        raise HTTPException(status_code=400, detail="Job description text cannot be empty")
        
    try:
        # Step 1: Parse JD using LLM
        jd_analysis = llm_service.parse_jd(data.jd_text)
        
        # Step 2: Use skills + role title to query Vector DB
        skills = jd_analysis.get("required_skills", [])
        role = jd_analysis.get("role_name", "")
        query_string = f"{role} {' '.join(skills)}"
        
        # Search RAG
        retrieved_chunks = rag_service.query_projects(query_string, top_k=4)
        
        # Step 3: Matchmaking & Coach generation
        coach_guide = llm_service.generate_match_and_coach(jd_analysis, retrieved_chunks)
        
        return {
            "jd_analysis": jd_analysis,
            "retrieved_chunks": [
                {
                    "project_name": c["project_name"],
                    "text": c["text"],
                    "score": round(c["score"], 3)
                } for c in retrieved_chunks
            ],
            "coach_guide": coach_guide
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing JD Match: {str(e)}")

@app.get("/settings")
def get_config_settings():
    """Retrieve current settings state (safe representation)."""
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "gemini_api_key_configured": bool(settings.GEMINI_API_KEY),
        "gemini_api_base": settings.GEMINI_API_BASE,
        "gemini_model": settings.GEMINI_MODEL,
        "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
        "openai_api_base": settings.OPENAI_API_BASE,
        "openai_model": settings.OPENAI_MODEL,
        "email_imap_server": settings.EMAIL_IMAP_SERVER,
        "email_address": settings.EMAIL_ADDRESS,
        "email_password_configured": bool(settings.EMAIL_PASSWORD),
        "email_sync_days": settings.EMAIL_SYNC_DAYS,
        "email_max_fetch": settings.EMAIL_MAX_FETCH,
        "http_proxy": settings.HTTP_PROXY
    }

@app.post("/settings")
def update_config_settings(data: SettingsUpdate):
    """Update configurations and save them back to .env file."""
    env_path = BASE_DIR / ".env"
    
    # Read existing env
    env_lines = []
    existing_keys = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            env_lines = f.readlines()
        for idx, line in enumerate(env_lines):
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=")[0].strip()
                existing_keys[key] = idx
                
    def set_key(key: str, val: Any):
        if val is None:
            return
        line_str = f"{key}={val}\n"
        if key in existing_keys:
            env_lines[existing_keys[key]] = line_str
        else:
            env_lines.append(line_str)
            existing_keys[key] = len(env_lines) - 1

    # Apply updates
    set_key("LLM_PROVIDER", data.llm_provider)
    if data.gemini_api_key is not None:
        set_key("GEMINI_API_KEY", data.gemini_api_key)
    if data.gemini_api_base is not None:
        set_key("GEMINI_API_BASE", data.gemini_api_base)
    if data.gemini_model is not None:
        set_key("GEMINI_MODEL", data.gemini_model)
    if data.openai_api_key is not None:
        set_key("OPENAI_API_KEY", data.openai_api_key)
    if data.openai_api_base is not None:
        set_key("OPENAI_API_BASE", data.openai_api_base)
    if data.openai_model is not None:
        set_key("OPENAI_MODEL", data.openai_model)
    if data.email_imap_server is not None:
        set_key("EMAIL_IMAP_SERVER", data.email_imap_server)
    if data.email_address is not None:
        set_key("EMAIL_ADDRESS", data.email_address)
    if data.email_password is not None:
        set_key("EMAIL_PASSWORD", data.email_password)
    if data.http_proxy is not None:
        set_key("HTTP_PROXY", data.http_proxy)

    # Save back to .env
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(env_lines)
            
        # Hot-reload configurations into the memory settings object
        settings.LLM_PROVIDER = data.llm_provider
        if data.gemini_api_key is not None:
            settings.GEMINI_API_KEY = data.gemini_api_key
        if data.gemini_api_base is not None:
            settings.GEMINI_API_BASE = data.gemini_api_base
        if data.gemini_model is not None:
            settings.GEMINI_MODEL = data.gemini_model
        if data.openai_api_key is not None:
            settings.OPENAI_API_KEY = data.openai_api_key
        if data.openai_api_base is not None:
            settings.OPENAI_API_BASE = data.openai_api_base
        if data.openai_model is not None:
            settings.OPENAI_MODEL = data.openai_model
        if data.email_imap_server is not None:
            settings.EMAIL_IMAP_SERVER = data.email_imap_server
        if data.email_address is not None:
            settings.EMAIL_ADDRESS = data.email_address
        if data.email_password is not None:
            settings.EMAIL_PASSWORD = data.email_password
        if data.http_proxy is not None:
            settings.HTTP_PROXY = data.http_proxy
            # Apply to current process environment dynamically
            if data.http_proxy.strip():
                os.environ["HTTP_PROXY"] = data.http_proxy.strip()
                os.environ["HTTPS_PROXY"] = data.http_proxy.strip()
            else:
                os.environ.pop("HTTP_PROXY", None)
                os.environ.pop("HTTPS_PROXY", None)
            
        return {"status": "success", "message": "Settings updated and saved to .env file"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write .env configuration: {str(e)}")

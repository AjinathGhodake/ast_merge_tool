"""
AST Merge API
FastAPI backend for AST-based code merging.
Supports Python and JavaScript with AWS Bedrock for LLM merging.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from merge_engine import parse_code, merge_code, detect_language
from ast_differ import compute_diff
from context_extractor import extract_context

app = FastAPI(
    title="AST Merge API",
    description="AST-based intelligent code merge tool with Bedrock LLM support",
    version="0.2.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ParseRequest(BaseModel):
    code: str
    language: Optional[str] = None  # "python", "javascript", or auto-detect


class DiffRequest(BaseModel):
    base_code: str
    target_code: str
    language: Optional[str] = None


class MergeRequest(BaseModel):
    base_code: str
    target_code: str
    strategy: str = "auto"  # "smart", "llm_all", "auto"
    language: Optional[str] = None
    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    bedrock_model_id: Optional[str] = None
    verify_ssl: bool = True


class ContextRequest(BaseModel):
    base_code: str
    target_code: str
    language: Optional[str] = None
    include_unchanged: bool = False


@app.get("/")
async def root():
    return {
        "name": "AST Merge API",
        "version": "0.2.0",
        "supported_languages": ["python", "javascript"],
        "llm_provider": "AWS Bedrock (Claude)",
        "endpoints": {
            "POST /parse": "Parse code into AST structure",
            "POST /diff": "Compare two code versions",
            "POST /context": "Extract merge context",
            "POST /merge": "Merge two code versions",
        }
    }


@app.post("/parse")
async def parse_endpoint(request: ParseRequest):
    """Parse code and return AST structure."""
    try:
        language = request.language or detect_language(request.code)
        parsed = parse_code(request.code, language)
        return {
            "success": True,
            "data": parsed.to_dict(),
            "detected_language": language
        }
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Syntax error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/diff")
async def diff_endpoint(request: DiffRequest):
    """Compare two code versions and return differences."""
    try:
        language = request.language or detect_language(request.target_code)
        base_parsed = parse_code(request.base_code, language)
        target_parsed = parse_code(request.target_code, language)
        diff = compute_diff(base_parsed, target_parsed)
        return {
            "success": True,
            "data": diff.to_dict(),
            "detected_language": language
        }
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Syntax error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/context")
async def context_endpoint(request: ContextRequest):
    """Extract merge context for changes."""
    try:
        language = request.language or detect_language(request.target_code)
        base_parsed = parse_code(request.base_code, language)
        target_parsed = parse_code(request.target_code, language)
        diff = compute_diff(base_parsed, target_parsed)
        context = extract_context(base_parsed, target_parsed, diff)
        return {
            "success": True,
            "data": context.to_dict(),
            "detected_language": language
        }
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Syntax error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/merge")
async def merge_endpoint(request: MergeRequest):
    """Merge two code versions using AST analysis and optional Bedrock LLM."""
    try:
        result = merge_code(
            request.base_code,
            request.target_code,
            strategy=request.strategy,
            language=request.language,
            aws_region=request.aws_region,
            aws_profile=request.aws_profile,
            aws_access_key=request.aws_access_key,
            aws_secret_key=request.aws_secret_key,
            aws_session_token=request.aws_session_token,
            bedrock_model_id=request.bedrock_model_id,
            verify_ssl=request.verify_ssl
        )
        return {
            "success": result.success,
            "data": result.to_dict()
        }
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Syntax error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

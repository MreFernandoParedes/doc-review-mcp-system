"""Schemas de Pydantic para validación de requests/responses"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class DocumentAnalysisRequest(BaseModel):
    """Request para análisis de documento"""
    document_id: str = Field(..., description="ID del documento a analizar")
    rector_ids: Optional[List[str]] = Field(None, description="IDs de documentos rectores (opcional, se auto-detectan)")
    analysis_type: str = Field("full", description="Tipo de análisis: full, quick, deep")
    sensitivity: str = Field("moderate", description="Sensibilidad: strict, moderate, flexible")

class DocumentAnalysisResponse(BaseModel):
    """Response del análisis"""
    status: str
    doc_id: str
    result: str
    iterations: Optional[int] = None
    contradictions_found: Optional[int] = None
    compliance_score: Optional[float] = None
    tool_use_log: Optional[List[Dict]] = None

class DocumentUploadResponse(BaseModel):
    """Response al subir documento"""
    document_id: str
    filename: str
    status: str
    message: Optional[str] = None

class DocumentListResponse(BaseModel):
    """Response al listar documentos"""
    total: int
    documents: List[Dict[str, Any]]

class HealthResponse(BaseModel):
    """Response de health check"""
    status: str
    service: str
    database: str
    claude_api: bool
    timestamp: datetime
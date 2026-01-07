"""Endpoints de la API REST"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
from typing import Optional
import os
import asyncio
from datetime import datetime

from .schemas import (
    DocumentAnalysisRequest,
    DocumentAnalysisResponse,
    DocumentUploadResponse,
    DocumentListResponse,
    HealthResponse
)
from ..models.database import get_db, Document
from ..mcp.orchestrator import ClaudeOrchestrator
from ..mcp.servers.reader import DocumentReader

router = APIRouter()

# Cargar .env ANTES de inicializar orchestrator
from dotenv import load_dotenv
load_dotenv()
# Inicializar orquestador (singleton)
orchestrator = ClaudeOrchestrator()

@router.get("/", response_model=dict)
async def root():
    """Endpoint raíz con información del servicio"""
    return {
        "service": "Document Review MCP System",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "analyze": "/analyze",
            "documents": "/documents",
            "upload": "/upload"
        }
    }

@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check del sistema"""
    
    # Verificar base de datos
    try:
        db.query(Document).first()
        db_status = "connected"
    except:
        db_status = "error"
    
    # Verificar Claude API
    claude_available = orchestrator.client is not None
    
    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        service="doc-review-mcp-system",
        database=db_status,
        claude_api=claude_available,
        timestamp=datetime.utcnow()
    )

@router.post("/analyze", response_model=DocumentAnalysisResponse)
async def analyze_document(request: DocumentAnalysisRequest):
    """
    Analiza un documento contra documentos rectores
    
    - **document_id**: ID del documento a analizar
    - **rector_ids**: IDs de rectores (opcional, se auto-detectan si no se especifica)
    - **analysis_type**: full (completo), quick (rápido), deep (profundo)
    - **sensitivity**: strict, moderate, flexible
    """
    try:
        # Ejecutar análisis
        result = orchestrator.analyze_document(
            doc_id=request.document_id,
            rector_ids=request.rector_ids,
            analysis_type=request.analysis_type
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Error desconocido"))
        
        return DocumentAnalysisResponse(
            status=result["status"],
            doc_id=request.document_id,
            result=result["result"],
            iterations=result.get("iterations"),
            contradictions_found=result.get("contradictions_found"),
            compliance_score=result.get("compliance_score"),
            tool_use_log=result.get("tool_use_log")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    tipo: Optional[str] = None,
    es_rector: Optional[bool] = None,
    institucion: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista documentos con filtros opcionales
    
    - **tipo**: LEY, REGL, POL, DIR, ISO
    - **es_rector**: true (solo rectores), false (solo operativos)
    - **institucion**: PERU, PCM, MRE, etc.
    """
    try:
        query = db.query(Document)
        
        if tipo:
            query = query.filter(Document.tipo == tipo.upper())
        if es_rector is not None:
            query = query.filter(Document.es_rector == es_rector)
        if institucion:
            query = query.filter(Document.institucion == institucion.upper())
        
        documents = query.order_by(Document.nivel_jerarquico, Document.año).all()
        
        doc_list = []
        for doc in documents:
            doc_list.append({
                "doc_id": doc.doc_id,
                "tipo": doc.tipo,
                "nivel_jerarquico": doc.nivel_jerarquico,
                "institucion": doc.institucion,
                "año": doc.año,
                "tema_principal": doc.tema_principal,
                "es_rector": doc.es_rector,
                "alcance": doc.alcance,
                "filename": doc.filename
            })
        
        return DocumentListResponse(
            total=len(doc_list),
            documents=doc_list
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{doc_id}")
async def get_document(doc_id: str, db: Session = Depends(get_db)):
    """
    Obtiene información detallada de un documento
    """
    try:
        document = db.query(Document).filter(Document.doc_id == doc_id).first()
        
        if not document:
            raise HTTPException(status_code=404, detail=f"Documento '{doc_id}' no encontrado")
        
        return {
            "doc_id": document.doc_id,
            "filename": document.filename,
            "tipo": document.tipo,
            "nivel_jerarquico": document.nivel_jerarquico,
            "institucion": document.institucion,
            "numero_oficial": document.numero_oficial,
            "año": document.año,
            "tema_principal": document.tema_principal,
            "es_rector": document.es_rector,
            "alcance": document.alcance,
            "vigente": document.vigente,
            "content_length": len(document.content),
            "upload_date": document.upload_date.isoformat(),
            "last_modified": document.last_modified.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = "DIR",
    db: Session = Depends(get_db)
):
    """
    Sube un nuevo documento al sistema
    
    - **file**: Archivo .txt
    - **doc_type**: Tipo de documento (LEY, REGL, POL, DIR, ISO)
    """
    try:
        # Validar extensión
        if not file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos .txt")
        
        # Leer contenido
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Parsear filename para extraer metadata
        # Formato esperado: TIPO_INST_NUM_AÑO_TEMA.txt
        doc_id = file.filename.replace('.txt', '')
        
        # Verificar si ya existe
        existing = db.query(Document).filter(Document.doc_id == doc_id).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Documento '{doc_id}' ya existe")
        
        # Crear documento (simplificado - en producción parsear metadata)
        import hashlib
        
        document = Document(
            doc_id=doc_id,
            filename=file.filename,
            filepath=f"./data/documents/uploaded/{file.filename}",
            tipo=doc_type.upper(),
            nivel_jerarquico=4,  # Default
            institucion="MRE",
            numero_oficial="000",
            año=2024,
            tema_principal="documento_subido",
            content=content_str,
            content_hash=hashlib.sha256(content_str.encode()).hexdigest()[:16],
            es_rector=False,
            alcance="operativo",
            vigente=True
        )
        
        db.add(document)
        db.commit()
        
        # Guardar archivo físico
        os.makedirs("./data/documents/uploaded", exist_ok=True)
        with open(f"./data/documents/uploaded/{file.filename}", 'w', encoding='utf-8') as f:
            f.write(content_str)
        
        return DocumentUploadResponse(
            document_id=doc_id,
            filename=file.filename,
            status="uploaded",
            message=f"Documento subido exitosamente. ID: {doc_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
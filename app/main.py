"""FastAPI Application - Punto de entrada principal"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

from app.models.database import init_db
from app.api import routes

# Cargar variables de entorno
load_dotenv()

# Inicializar base de datos
init_db()

# Crear app FastAPI
app = FastAPI(
    title="Document Review MCP System",
    description="Sistema de revisión y análisis de documentos usando Claude + MCP",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS (para desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(routes.router, prefix="/api/v1", tags=["api"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "Document Review MCP System",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
        "api": "/api/v1"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    print("\n" + "="*80)
    print("🚀 Document Review MCP System")
    print("="*80)
    print(f"📁 Database: {os.getenv('DB_PATH', './data/docs.db')}")
    print(f"🤖 Claude API: {'Configured' if os.getenv('ANTHROPIC_API_KEY') and os.getenv('ANTHROPIC_API_KEY') != 'tu_clave_aqui_temporalmente' else 'Not configured (DEMO mode)'}")
    print(f"🌐 API Docs: http://localhost:{os.getenv('PORT', 8000)}/docs")
    print("="*80 + "\n")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    print("\n👋 Cerrando sistema...")

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )

# Para ejecución directa
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
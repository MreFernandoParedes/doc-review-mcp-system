"""Configuración de SQLite con SQLAlchemy"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Crear engine de SQLite
DATABASE_URL = f"sqlite:///{os.getenv('DB_PATH', './data/docs.db')}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo de Documentos
class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, unique=True, index=True)  # LEY_PERU_31814_2023_IA_promocion_desarrollo
    filename = Column(String)
    filepath = Column(String)
    
    # Metadata del documento
    tipo = Column(String, index=True)  # LEY, REGL, POL, DIR, ISO
    nivel_jerarquico = Column(Integer, index=True)  # 1-5
    institucion = Column(String)  # PERU, PCM, MRE
    numero_oficial = Column(String)
    año = Column(Integer)
    tema_principal = Column(String)
    
    # Contenido
    content = Column(Text)
    content_hash = Column(String)  # Para detectar cambios
    
    # Clasificación
    es_rector = Column(Boolean, default=False)
    alcance = Column(String)  # nacional, institucional, operativo
    vigente = Column(Boolean, default=True)
    
    # Relaciones
    documentos_relacionados = Column(JSON)  # Lista de doc_ids relacionados
    subtemas = Column(JSON)  # Lista de subtemas
    
    # Control
    upload_date = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_extra = Column(JSON)

# Modelo de Análisis
class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String, unique=True, index=True)
    target_doc_id = Column(String, index=True)
    rector_doc_ids = Column(JSON)  # Lista de doc_ids rectores
    analysis_type = Column(String)  # full, quick, deep
    
    # Resultados
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # pending, completed, failed
    result = Column(Text)
    contradictions_found = Column(Integer)
    compliance_score = Column(Float)
    
    # Detalles
    contradictions_detail = Column(JSON)  # Lista detallada de contradicciones
    iterations = Column(Integer)
    tool_use_log = Column(JSON)
    processing_time = Column(Float)

# Modelo de Correcciones
class Correction(Base):
    __tablename__ = "corrections"
    
    id = Column(Integer, primary_key=True, index=True)
    correction_id = Column(String, unique=True, index=True)
    analysis_id = Column(String, index=True)
    original_doc_id = Column(String)
    
    corrected_content = Column(Text)
    corrections_applied = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    approved = Column(Integer, default=0)  # 0=pending, 1=approved, -1=rejected
    approved_by = Column(String)
    approved_at = Column(DateTime)

# Funciones de inicialización
def init_db():
    """Crea todas las tablas"""
    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos inicializada")

def get_db():
    """Dependency para FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Ejecutar si se llama directamente
if __name__ == "__main__":
    init_db()
    print(f"📁 Base de datos creada en: {DATABASE_URL}")
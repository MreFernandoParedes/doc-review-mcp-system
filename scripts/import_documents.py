"""Script para importar documentos a SQLite con metadata automática"""
import os
import sys
import hashlib
from datetime import datetime

# Agregar path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import init_db, SessionLocal, Document

# Configuración de tipos de documentos
TIPO_CONFIG = {
    "LEY": {"nivel": 1, "alcance": "nacional", "es_rector": True},
    "REGL": {"nivel": 2, "alcance": "nacional", "es_rector": True},
    "POL": {"nivel": 3, "alcance": "institucional", "es_rector": True},
    "DIR": {"nivel": 4, "alcance": "operativo", "es_rector": False},
    "ISO": {"nivel": 5, "alcance": "internacional", "es_rector": False},
    "NTP": {"nivel": 5, "alcance": "nacional", "es_rector": False},
}

def parse_filename(filename: str) -> dict:
    """
    Parsea el nombre del archivo según nomenclatura:
    TIPO_INSTITUCION_NUMERO_AÑO_TEMA.txt
    Ejemplo: LEY_PERU_31814_2023_IA_promocion_desarrollo.txt
    """
    parts = filename.replace(".txt", "").split("_")
    
    if len(parts) < 4:
        return None
    
    tipo = parts[0]
    institucion = parts[1]
    numero = parts[2]
    año = parts[3]
    tema = "_".join(parts[4:]) if len(parts) > 4 else "sin_tema"
    
    return {
        "tipo": tipo,
        "institucion": institucion,
        "numero_oficial": numero,
        "año": int(año) if año.isdigit() else 2024,
        "tema_principal": tema.replace("_", " "),
    }

def calculate_hash(content: str) -> str:
    """Calcula hash del contenido"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

def import_documents(base_path: str = "./data/documents"):
    """Importa todos los documentos de las carpetas organizadas"""
    
    db = SessionLocal()
    
    # Inicializar BD
    init_db()
    
    imported = 0
    errors = []
    
    print("\n🚀 Iniciando importación de documentos...\n")
    
    # Recorrer carpetas
    for root, dirs, files in os.walk(base_path):
        for filename in files:
            if not filename.endswith(".txt"):
                continue
            
            filepath = os.path.join(root, filename)
            
            try:
                # Leer contenido
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parsear nombre
                metadata = parse_filename(filename)
                if not metadata:
                    errors.append(f"❌ No se pudo parsear: {filename}")
                    continue
                
                # Obtener configuración del tipo
                tipo_config = TIPO_CONFIG.get(metadata["tipo"], {})
                
                # Crear doc_id
                doc_id = filename.replace(".txt", "")
                
                # Verificar si ya existe
                existing = db.query(Document).filter(Document.doc_id == doc_id).first()
                if existing:
                    print(f"⏭️  Ya existe: {doc_id}")
                    continue
                
                # Crear documento
                document = Document(
                    doc_id=doc_id,
                    filename=filename,
                    filepath=filepath,
                    tipo=metadata["tipo"],
                    nivel_jerarquico=tipo_config.get("nivel", 999),
                    institucion=metadata["institucion"],
                    numero_oficial=metadata["numero_oficial"],
                    año=metadata["año"],
                    tema_principal=metadata["tema_principal"],
                    content=content,
                    content_hash=calculate_hash(content),
                    es_rector=tipo_config.get("es_rector", False),
                    alcance=tipo_config.get("alcance", "desconocido"),
                    vigente=True,
                    documentos_relacionados=[],
                    subtemas=[],
                    metadata_extra={"folder": os.path.basename(root)}
                )
                
                db.add(document)
                db.commit()
                
                print(f"✅ Importado: {doc_id}")
                imported += 1
                
            except Exception as e:
                errors.append(f"❌ Error en {filename}: {str(e)}")
                continue
    
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN DE IMPORTACIÓN")
    print(f"{'='*60}")
    print(f"✅ Documentos importados: {imported}")
    print(f"❌ Errores: {len(errors)}")
    
    if errors:
        print(f"\n⚠️  ERRORES:")
        for error in errors:
            print(f"  {error}")
    
    db.close()

if __name__ == "__main__":
    import_documents()
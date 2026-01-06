"""MCP Server: Lector de documentos desde SQLite"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from app.models.database import SessionLocal, Document
from typing import Optional, List

class DocumentReader:
    """Lee documentos desde la base de datos SQLite"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def read_document(self, doc_id: str, section: Optional[str] = None) -> dict:
        """
        Lee un documento completo o una sección específica
        
        Args:
            doc_id: ID del documento (ej: LEY_PERU_31814_2023_IA_promocion_desarrollo)
            section: Sección específica a leer (opcional)
        
        Returns:
            Dict con contenido y metadata del documento
        """
        try:
            document = self.db.query(Document).filter(Document.doc_id == doc_id).first()
            
            if not document:
                return {
                    "success": False,
                    "error": f"Documento '{doc_id}' no encontrado en la base de datos"
                }
            
            content = document.content
            
            # Si se solicita una sección específica
            if section:
                content = self._extract_section(content, section)
            
            return {
                "success": True,
                "doc_id": doc_id,
                "content": content,
                "metadata": {
                    "tipo": document.tipo,
                    "nivel_jerarquico": document.nivel_jerarquico,
                    "institucion": document.institucion,
                    "año": document.año,
                    "tema": document.tema_principal,
                    "es_rector": document.es_rector,
                    "alcance": document.alcance,
                    "length": len(content)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error al leer documento: {str(e)}"
            }
    
    def list_documents(
        self, 
        tipo: Optional[str] = None,
        es_rector: Optional[bool] = None,
        institucion: Optional[str] = None
    ) -> dict:
        """
        Lista documentos con filtros opcionales
        
        Args:
            tipo: Filtrar por tipo (LEY, REGL, POL, DIR, ISO)
            es_rector: Filtrar solo rectores (True) u operativos (False)
            institucion: Filtrar por institución (PERU, PCM, MRE)
        
        Returns:
            Dict con lista de documentos
        """
        try:
            query = self.db.query(Document)
            
            if tipo:
                query = query.filter(Document.tipo == tipo)
            if es_rector is not None:
                query = query.filter(Document.es_rector == es_rector)
            if institucion:
                query = query.filter(Document.institucion == institucion)
            
            documents = query.order_by(Document.nivel_jerarquico, Document.año).all()
            
            result = []
            for doc in documents:
                result.append({
                    "doc_id": doc.doc_id,
                    "tipo": doc.tipo,
                    "nivel": doc.nivel_jerarquico,
                    "institucion": doc.institucion,
                    "año": doc.año,
                    "tema": doc.tema_principal,
                    "es_rector": doc.es_rector
                })
            
            return {
                "success": True,
                "total": len(result),
                "documents": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error al listar documentos: {str(e)}"
            }
    
    def get_document_hierarchy(self, doc_id: str) -> dict:
        """
        Obtiene la jerarquía de documentos relacionados
        (ej: para una directiva, obtiene la ley y reglamento que la rigen)
        
        Args:
            doc_id: ID del documento
        
        Returns:
            Dict con documentos superiores en la jerarquía
        """
        try:
            document = self.db.query(Document).filter(Document.doc_id == doc_id).first()
            
            if not document:
                return {"success": False, "error": "Documento no encontrado"}
            
            # Obtener documentos de nivel superior
            superior_docs = self.db.query(Document).filter(
                Document.nivel_jerarquico < document.nivel_jerarquico
            ).order_by(Document.nivel_jerarquico).all()
            
            hierarchy = []
            for doc in superior_docs:
                hierarchy.append({
                    "doc_id": doc.doc_id,
                    "tipo": doc.tipo,
                    "nivel": doc.nivel_jerarquico,
                    "tema": doc.tema_principal
                })
            
            return {
                "success": True,
                "documento_actual": {
                    "doc_id": document.doc_id,
                    "nivel": document.nivel_jerarquico
                },
                "documentos_superiores": hierarchy
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error al obtener jerarquía: {str(e)}"
            }
    
    def _extract_section(self, content: str, section: str) -> str:
        """
        Extrae una sección específica del documento
        (simplificado - puedes mejorarlo según tu estructura de docs)
        """
        lines = content.split('\n')
        section_content = []
        in_section = False
        
        for line in lines:
            if section.lower() in line.lower():
                in_section = True
            
            if in_section:
                section_content.append(line)
                
                # Detectar fin de sección (siguiente título similar)
                if len(section_content) > 1 and line.strip() and line[0].isdigit():
                    if not section.lower() in line.lower():
                        break
        
        return '\n'.join(section_content) if section_content else content
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        self.db.close()


# Testing
if __name__ == "__main__":
    reader = DocumentReader()
    
    print("\n🧪 TESTING DocumentReader\n")
    
    # Test 1: Leer documento
    print("Test 1: Leer LEY 31814")
    result = reader.read_document("LEY_PERU_31814_2023_IA_promocion_desarrollo")
    if result["success"]:
        print(f"✅ Documento leído: {result['metadata']['length']} caracteres")
        print(f"   Tipo: {result['metadata']['tipo']} | Nivel: {result['metadata']['nivel_jerarquico']}")
    else:
        print(f"❌ Error: {result['error']}")
    
    # Test 2: Listar rectores
    print("\nTest 2: Listar documentos rectores")
    result = reader.list_documents(es_rector=True)
    if result["success"]:
        print(f"✅ {result['total']} documentos rectores encontrados:")
        for doc in result["documents"]:
            print(f"   - {doc['doc_id']}")
    else:
        print(f"❌ Error: {result['error']}")
    
    # Test 3: Jerarquía
    print("\nTest 3: Obtener jerarquía de una directiva")
    result = reader.get_document_hierarchy("DIR_MRE_020_2024_correo_electronico")
    if result["success"]:
        print(f"✅ Documentos superiores:")
        for doc in result["documentos_superiores"]:
            print(f"   Nivel {doc['nivel']}: {doc['doc_id']}")
    else:
        print(f"❌ Error: {result['error']}")
    
    reader.close()
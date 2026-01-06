"""Script para ver el contenido de la base de datos"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import SessionLocal, Document
from sqlalchemy import func

def view_documents():
    db = SessionLocal()
    
    print("\n" + "="*80)
    print("📚 DOCUMENTOS EN LA BASE DE DATOS")
    print("="*80 + "\n")
    
    # Obtener todos los documentos ordenados por nivel jerárquico
    documents = db.query(Document).order_by(Document.nivel_jerarquico, Document.año).all()
    
    if not documents:
        print("❌ No hay documentos en la base de datos")
        return
    
    # Agrupar por tipo
    tipos = {}
    for doc in documents:
        if doc.tipo not in tipos:
            tipos[doc.tipo] = []
        tipos[doc.tipo].append(doc)
    
    # Mostrar por tipo (corregido)
    for tipo, docs in sorted(tipos.items(), key=lambda x: x[1][0].nivel_jerarquico if x[1] else 999):
        print(f"\n📁 {tipo} (Nivel {docs[0].nivel_jerarquico}) - {docs[0].alcance.upper()}")
        print("-" * 80)
        
        for doc in docs:
            rector_icon = "⭐" if doc.es_rector else "  "
            print(f"{rector_icon} {doc.doc_id}")
            print(f"   📅 Año: {doc.año} | 🏛️  {doc.institucion} | 📋 #{doc.numero_oficial}")
            print(f"   📝 Tema: {doc.tema_principal}")
            print(f"   📄 Archivo: {doc.filename}")
            print(f"   📊 Contenido: {len(doc.content)} caracteres")
            print()
    
    # Estadísticas
    print("\n" + "="*80)
    print("📊 ESTADÍSTICAS")
    print("="*80)
    print(f"Total documentos: {len(documents)}")
    print(f"Documentos rectores: {len([d for d in documents if d.es_rector])}")
    print(f"Documentos operativos: {len([d for d in documents if not d.es_rector])}")
    
    print("\nPor tipo:")
    for tipo, count in db.query(Document.tipo, func.count(Document.id)).group_by(Document.tipo).all():
        print(f"  - {tipo}: {count}")
    
    print("\nPor alcance:")
    for alcance, count in db.query(Document.alcance, func.count(Document.id)).group_by(Document.alcance).all():
        print(f"  - {alcance}: {count}")
    
    db.close()

if __name__ == "__main__":
    view_documents()
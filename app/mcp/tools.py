"""Definiciones de herramientas MCP para Claude"""

TOOLS = [
    {
        "name": "read_document",
        "description": "Lee el contenido completo de un documento desde la base de datos por su ID. Útil para obtener el texto completo de leyes, reglamentos, políticas o directivas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "ID del documento. Ejemplos: 'LEY_PERU_31814_2023_IA_promocion_desarrollo', 'DIR_MRE_020_2024_correo_electronico'"
                },
                "section": {
                    "type": "string",
                    "description": "Sección específica a leer (opcional). Ejemplo: 'CAPÍTULO I', 'Artículo 5'"
                }
            },
            "required": ["doc_id"]
        }
    },
    {
        "name": "list_documents",
        "description": "Lista documentos disponibles en la base de datos con filtros opcionales. Útil para descubrir qué documentos existen antes de leerlos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {
                    "type": "string",
                    "enum": ["LEY", "REGL", "POL", "DIR", "ISO", "NTP"],
                    "description": "Filtrar por tipo de documento"
                },
                "es_rector": {
                    "type": "boolean",
                    "description": "Filtrar solo documentos rectores (true) u operativos (false)"
                },
                "institucion": {
                    "type": "string",
                    "description": "Filtrar por institución. Ejemplos: 'PERU', 'PCM', 'MRE'"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_document_hierarchy",
        "description": "Obtiene la jerarquía normativa de un documento, mostrando qué leyes, reglamentos y políticas superiores lo rigen. Esencial para identificar documentos rectores antes de analizar contradicciones.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "ID del documento del cual obtener su jerarquía"
                }
            },
            "required": ["doc_id"]
        }
    },
    {
        "name": "compare_documents",
        "description": "Compara dos documentos y extrae diferencias. Útil para análisis preliminar antes de detectar contradicciones.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doc1_id": {
                    "type": "string",
                    "description": "ID del primer documento"
                },
                "doc2_id": {
                    "type": "string",
                    "description": "ID del segundo documento"
                },
                "comparison_type": {
                    "type": "string",
                    "enum": ["full", "terminology", "numeric", "structure"],
                    "description": "Tipo de comparación: full (completa), terminology (términos), numeric (números/plazos/montos), structure (estructura)"
                }
            },
            "required": ["doc1_id", "doc2_id"]
        }
    },
    {
        "name": "detect_contradictions",
        "description": "Detecta contradicciones entre un documento objetivo y sus documentos rectores. Esta es la herramienta principal para análisis de cumplimiento normativo. Identifica conflictos en plazos, montos, obligaciones y terminología.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_doc_id": {
                    "type": "string",
                    "description": "ID del documento a analizar (directiva, política, etc.)"
                },
                "rector_doc_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de IDs de documentos rectores contra los cuales validar (leyes, reglamentos, políticas superiores)"
                },
                "sensitivity": {
                    "type": "string",
                    "enum": ["strict", "moderate", "flexible"],
                    "description": "Nivel de sensibilidad del análisis: strict (detecta cualquier diferencia), moderate (diferencias >10%), flexible (diferencias >20%)"
                }
            },
            "required": ["target_doc_id", "rector_doc_ids"]
        }
    },
    {
        "name": "extract_key_terms",
        "description": "Extrae términos clave y terminología importante de un documento. Útil para análisis terminológico y verificación de consistencia.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "ID del documento del cual extraer términos"
                },
                "term_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tipos de términos a extraer: 'technical', 'legal', 'definitions'"
                }
            },
            "required": ["doc_id"]
        }
    }
]

# Metadata de las herramientas para referencia
TOOL_METADATA = {
    "read_document": {
        "category": "data_access",
        "complexity": "simple",
        "typical_use": "Primer paso en cualquier análisis"
    },
    "list_documents": {
        "category": "discovery",
        "complexity": "simple",
        "typical_use": "Explorar documentos disponibles"
    },
    "get_document_hierarchy": {
        "category": "analysis",
        "complexity": "moderate",
        "typical_use": "Identificar documentos rectores para validación"
    },
    "compare_documents": {
        "category": "analysis",
        "complexity": "moderate",
        "typical_use": "Análisis comparativo preliminar"
    },
    "detect_contradictions": {
        "category": "analysis",
        "complexity": "complex",
        "typical_use": "Análisis principal de cumplimiento normativo"
    },
    "extract_key_terms": {
        "category": "analysis",
        "complexity": "moderate",
        "typical_use": "Análisis terminológico"
    }
}

# Workflow sugerido para análisis completo
RECOMMENDED_WORKFLOW = """
WORKFLOW RECOMENDADO PARA ANÁLISIS DE DOCUMENTOS:

1. list_documents (es_rector=True)
   → Identificar documentos rectores disponibles

2. get_document_hierarchy (doc_id=documento_a_analizar)
   → Identificar jerarquía normativa aplicable

3. read_document (doc_id=documento_objetivo)
   → Leer contenido completo del documento a analizar

4. read_document (doc_id=cada_documento_rector)
   → Leer documentos rectores identificados

5. detect_contradictions (target_doc_id, rector_doc_ids)
   → Detectar contradicciones principales

6. compare_documents (si se necesita análisis detallado)
   → Comparación granular cuando sea necesario

7. extract_key_terms (para análisis terminológico adicional)
   → Validar consistencia de términos
"""


# Testing de las definiciones
if __name__ == "__main__":
    print("\n📋 HERRAMIENTAS MCP DEFINIDAS\n")
    print("="*80)
    
    for i, tool in enumerate(TOOLS, 1):
        print(f"\n{i}. {tool['name']}")
        print(f"   Descripción: {tool['description'][:80]}...")
        print(f"   Parámetros requeridos: {tool['input_schema']['required']}")
        print(f"   Categoría: {TOOL_METADATA[tool['name']]['category']}")
        print(f"   Complejidad: {TOOL_METADATA[tool['name']]['complexity']}")
    
    print(f"\n{'='*80}")
    print(f"Total de herramientas: {len(TOOLS)}")
    print("\n📖 Workflow recomendado:")
    print(RECOMMENDED_WORKFLOW)
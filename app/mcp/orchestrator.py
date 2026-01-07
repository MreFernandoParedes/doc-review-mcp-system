"""Orquestador principal: Claude + MCP Tool Use Loop"""
from anthropic import Anthropic
from typing import List, Dict, Optional
import json
import os

# DESPUÉS (imports absolutos)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.mcp.tools import TOOLS
from app.mcp.servers.reader import DocumentReader
from app.mcp.servers.comparer import DocumentComparer
from app.mcp.servers.analyzer import ContradictionAnalyzer

class ClaudeOrchestrator:
    """
    Orquesta el análisis usando Claude + herramientas MCP
    Claude decide qué herramientas usar y en qué orden
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key or self.api_key == "tu_clave_aqui_temporalmente":
            print("⚠️  ADVERTENCIA: API key de Anthropic no configurada")
            print("   El sistema funcionará en modo DEMO sin Claude")
            self.client = None
        else:
            self.client = Anthropic(api_key=self.api_key)
        
        # Inicializar herramientas
        self.reader = DocumentReader()
        self.comparer = DocumentComparer()
        self.analyzer = ContradictionAnalyzer()
        
        self.max_iterations = 15
    
    def analyze_document(
        self,
        doc_id: str,
        rector_ids: Optional[List[str]] = None,
        analysis_type: str = "full"
    ) -> Dict:
        """
        Analiza un documento usando Claude + MCP
        
        Args:
            doc_id: ID del documento a analizar
            rector_ids: IDs de documentos rectores (opcional, se auto-detectan)
            analysis_type: Tipo de análisis (full, quick, deep)
        
        Returns:
            Dict con resultados del análisis
        """
        
        # Si no hay API key, hacer análisis sin Claude
        if not self.client:
            return self._analyze_without_claude(doc_id, rector_ids)
        
        # Preparar prompt para Claude
        messages = [{
            "role": "user",
            "content": self._build_analysis_prompt(doc_id, rector_ids, analysis_type)
        }]
        
        return self._run_tool_use_loop(messages, context={"doc_id": doc_id})
    
    def _build_analysis_prompt(
        self,
        doc_id: str,
        rector_ids: Optional[List[str]],
        analysis_type: str
    ) -> str:
        """Construye el prompt para Claude"""
        
        prompt = f"""Analiza el documento '{doc_id}' para detectar contradicciones con documentos rectores.

TIPO DE ANÁLISIS: {analysis_type}

INSTRUCCIONES:
1. Primero, usa 'get_document_hierarchy' para identificar los documentos rectores que aplican
2. Si no se especificaron documentos rectores, identifícalos tú mismo
3. Lee el documento objetivo con 'read_document'
4. Lee cada documento rector con 'read_document'
5. Usa 'detect_contradictions' para el análisis principal
6. Si encuentras contradicciones, usa 'compare_documents' para análisis más detallado

FORMATO DEL REPORTE FINAL:
Genera un reporte estructurado con:
- Resumen ejecutivo
- Contradicciones encontradas (listadas por severidad)
- Para cada contradicción:
  * Tipo y severidad
  * Qué dice el documento
  * Qué dice el documento rector
  * Recomendación de corrección
- Score de cumplimiento
- Recomendación general

USA LAS HERRAMIENTAS DISPONIBLES de manera inteligente."""

        if rector_ids:
            prompt += f"\n\nDOCUMENTOS RECTORES ESPECIFICADOS: {', '.join(rector_ids)}"
        
        return prompt
    

    def _run_tool_use_loop(self, messages: List[Dict], context: Dict) -> Dict:
    
        """
        Loop principal de tool use con Claude
        """
        iteration = 0
        tool_use_log = []
        
        print("\n🤖 Claude está analizando el documento...")
        print("="*80)
        
        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n🔄 Iteración {iteration}")
            
            try:
                # Llamar a Claude
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=8000,
                    tools=TOOLS,
                    messages=messages
                )
                
                # Log
                tool_use_log.append({
                    "iteration": iteration,
                    "stop_reason": response.stop_reason,
                    "input_tokens": response.usage.input_tokens if hasattr(response, 'usage') else 0,
                    "output_tokens": response.usage.output_tokens if hasattr(response, 'usage') else 0
                })
                
                print(f"   Stop reason: {response.stop_reason}")
                
                # Claude terminó
                if response.stop_reason == "end_turn":
                    final_response = self._extract_text(response.content)
                    
                    print("\n✅ Análisis completado")
                    print(f"📊 Total iteraciones: {iteration}")
                    print(f"📝 Tokens usados: {sum(log.get('input_tokens', 0) + log.get('output_tokens', 0) for log in tool_use_log)}")
                    
                    return {
                        "status": "completed",
                        "result": final_response,
                        "iterations": iteration,
                        "tool_use_log": tool_use_log,
                        "doc_id": context.get("doc_id")
                    }
                
                # Claude quiere usar herramientas
                if response.stop_reason == "tool_use":
                    # Agregar respuesta de Claude
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    
                    # Ejecutar herramientas
                    
                    tool_results = self._execute_tools(response.content)
                    
                    # Mostrar herramientas usadas
                    for result in tool_results:
                        tool_name = result.get('tool_name', 'unknown')
                        print(f"   🔧 Ejecutó: {tool_name}")
                    
                    # Devolver resultados a Claude
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                
            except Exception as e:
                print(f"\n❌ Error en iteración {iteration}: {str(e)}")
                return {
                    "status": "error",
                    "error": str(e),
                    "iterations": iteration,
                    "tool_use_log": tool_use_log
                }
        
        print("\n⚠️  Máximo de iteraciones alcanzado")
        return {
            "status": "max_iterations_reached",
            "iterations": iteration,
            "tool_use_log": tool_use_log
        }
    
    def _execute_tools(self, content: List) -> List[Dict]:
        """Ejecuta las herramientas solicitadas por Claude"""
        tool_results = []
        
        for block in content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                
                # Ejecutar herramienta
                result = self._dispatch_tool(tool_name, tool_input)
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False, indent=2)                    
                })
        
        return tool_results
    
    def _dispatch_tool(self, tool_name: str, tool_input: Dict) -> Dict:
        """Despacha la ejecución a la herramienta correcta"""
        
        try:
            if tool_name == "read_document":
                return self.reader.read_document(
                    doc_id=tool_input["doc_id"],
                    section=tool_input.get("section")
                )
            
            elif tool_name == "list_documents":
                return self.reader.list_documents(
                    tipo=tool_input.get("tipo"),
                    es_rector=tool_input.get("es_rector"),
                    institucion=tool_input.get("institucion")
                )
            
            elif tool_name == "get_document_hierarchy":
                return self.reader.get_document_hierarchy(
                    doc_id=tool_input["doc_id"]
                )
            
            elif tool_name == "compare_documents":
                # Leer ambos documentos
                doc1 = self.reader.read_document(tool_input["doc_id_1"])
                doc2 = self.reader.read_document(tool_input["doc_id_2"])
                
                if not doc1["success"] or not doc2["success"]:
                    return {"error": "No se pudieron leer los documentos"}
                
                return self.comparer.compare_documents(
                    doc1_content=doc1["content"],
                    doc2_content=doc2["content"],
                    doc1_id=tool_input["doc_id_1"],
                    doc2_id=tool_input["doc_id_2"],
                    comparison_type=tool_input.get("comparison_type", "full")
                )
            
            elif tool_name == "detect_contradictions":
                # Leer documento objetivo
                target_doc = self.reader.read_document(tool_input["target_doc_id"])
                
                if not target_doc["success"]:
                    return {"error": f"No se pudo leer el documento {tool_input['target_doc_id']}"}
                
                # Leer documentos rectores
                rector_contents = []
                for rector_id in tool_input["rector_doc_ids"]:
                    rector = self.reader.read_document(rector_id)
                    if rector["success"]:
                        rector_contents.append((rector["content"], rector["metadata"]))
                
                # Ejecutar análisis
                return self.analyzer.detect_contradictions(
                    target_content=target_doc["content"],
                    target_metadata=target_doc["metadata"],
                    rector_contents=rector_contents,
                    sensitivity=tool_input.get("sensitivity", "moderate")
                )
            
            elif tool_name == "extract_key_terms":
                doc = self.reader.read_document(tool_input["doc_id"])
                
                if not doc["success"]:
                    return {"error": "No se pudo leer el documento"}
                
                # Extraer términos (simplificado)
                import re
                terms = re.findall(r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*\b', 
                                 doc["content"])
                unique_terms = list(set(terms))[:30]
                
                return {
                    "success": True,
                    "doc_id": tool_input["doc_id"],
                    "key_terms": unique_terms,
                    "total_unique_terms": len(set(terms))
                }
            
            else:
                return {"error": f"Herramienta '{tool_name}' no implementada"}
        
        except Exception as e:
            return {"error": f"Error ejecutando {tool_name}: {str(e)}"}
    
    def _extract_text(self, content: List) -> str:
        """Extrae texto de la respuesta de Claude"""
        text_parts = []
        for block in content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "\n".join(text_parts)
    
    def _analyze_without_claude(self, doc_id: str, rector_ids: Optional[List[str]]) -> Dict:
        """Análisis sin Claude (modo demo)"""
        print("\n⚠️  MODO DEMO: Ejecutando análisis sin Claude")
        
        # Obtener jerarquía
        hierarchy = self.reader.get_document_hierarchy(doc_id)
        
        if not hierarchy["success"]:
            return {"status": "error", "error": hierarchy["error"]}
        
        # Si no hay rectores especificados, usar los de la jerarquía
        if not rector_ids:
            rector_ids = [doc["doc_id"] for doc in hierarchy["documentos_superiores"]]
        
        if not rector_ids:
            return {
                "status": "completed",
                "result": "No se encontraron documentos rectores para este documento.",
                "iterations": 1
            }
        
        # Leer documento objetivo
        target = self.reader.read_document(doc_id)
        
        if not target["success"]:
            return {"status": "error", "error": target["error"]}
        
        # Leer rectores
        rector_contents = []
        for rector_id in rector_ids:
            rector = self.reader.read_document(rector_id)
            if rector["success"]:
                rector_contents.append((rector["content"], rector["metadata"]))
        
        # Análisis
        analysis = self.analyzer.detect_contradictions(
            target_content=target["content"],
            target_metadata=target["metadata"],
            rector_contents=rector_contents,
            sensitivity="moderate"
        )
        
        # Formatear resultado
        result = f"""
ANÁLISIS DE CUMPLIMIENTO NORMATIVO (MODO DEMO)

Documento analizado: {doc_id}
Documentos rectores: {', '.join(rector_ids)}

RESULTADOS:
- Contradicciones encontradas: {analysis['contradictions_found']}
- Advertencias: {analysis['warnings_found']}
- Score de cumplimiento: {analysis['compliance_score']:.1%}

CONTRADICCIONES DETECTADAS:
"""
        
        for c in analysis['contradictions']:
            result += f"""
[{c['severity'].upper()}] {c['type']}
- {c['description']}
- Documento rector: {c['rector_doc']}
"""
        
        result += f"\n{analysis['analysis_summary']['recommendation']}"
        
        return {
            "status": "completed",
            "result": result,
            "iterations": 1,
            "contradictions_found": analysis['contradictions_found'],
            "compliance_score": analysis['compliance_score']
        }
    
    def close(self):
        """Cierra conexiones"""
        self.reader.close()


# Testing
if __name__ == "__main__":
    import asyncio
    
    async def test():
        orchestrator = ClaudeOrchestrator()
        
        print("\n🧪 TESTING ClaudeOrchestrator (MODO DEMO)\n")
        
        # Test: Analizar una directiva
        result = orchestrator.analyze_document(
            doc_id="DIR_MRE_020_2024_correo_electronico",
            analysis_type="full"
        )
        
        print("\n" + "="*80)
        print("📊 RESULTADO DEL ANÁLISIS")
        print("="*80)
        print(result["result"])
        
        orchestrator.close()
    
    asyncio.run(test())
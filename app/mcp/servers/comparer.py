"""MCP Server: Comparador de documentos"""
from difflib import SequenceMatcher
import re
from typing import Dict, List, Tuple

class DocumentComparer:
    """Compara dos documentos y extrae diferencias"""
    
    def compare_documents(
        self, 
        doc1_content: str,
        doc2_content: str,
        doc1_id: str = "Documento 1",
        doc2_id: str = "Documento 2",
        comparison_type: str = "full"
    ) -> dict:
        """
        Compara dos documentos según el tipo especificado
        
        Args:
            doc1_content: Contenido del primer documento
            doc2_content: Contenido del segundo documento
            doc1_id: ID del primer documento (para referencia)
            doc2_id: ID del segundo documento (para referencia)
            comparison_type: Tipo de comparación (full, terminology, numeric, structure)
        
        Returns:
            Dict con resultados de la comparación
        """
        
        if comparison_type == "terminology":
            return self._compare_terminology(doc1_content, doc2_content, doc1_id, doc2_id)
        elif comparison_type == "numeric":
            return self._compare_numeric_values(doc1_content, doc2_content, doc1_id, doc2_id)
        elif comparison_type == "structure":
            return self._compare_structure(doc1_content, doc2_content, doc1_id, doc2_id)
        else:  # full
            return self._compare_full(doc1_content, doc2_content, doc1_id, doc2_id)
    
    def _compare_terminology(self, doc1: str, doc2: str, id1: str, id2: str) -> dict:
        """
        Compara términos clave entre documentos
        Útil para detectar inconsistencias en nombres de conceptos
        """
        # Extraer términos importantes (mayúsculas, términos técnicos)
        pattern = r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*\b'
        
        terms1 = set(re.findall(pattern, doc1))
        terms2 = set(re.findall(pattern, doc2))
        
        # Filtrar términos muy comunes
        common_words = {'El', 'La', 'Los', 'Las', 'Un', 'Una', 'De', 'Del', 'En', 'Por', 'Para', 'Con'}
        terms1 = terms1 - common_words
        terms2 = terms2 - common_words
        
        unique_to_doc1 = list(terms1 - terms2)
        unique_to_doc2 = list(terms2 - terms1)
        common_terms = list(terms1 & terms2)
        
        similarity = len(common_terms) / max(len(terms1 | terms2), 1)
        
        return {
            "comparison_type": "terminology",
            "doc1_id": id1,
            "doc2_id": id2,
            "unique_to_doc1": unique_to_doc1[:20],  # Limitar a 20
            "unique_to_doc2": unique_to_doc2[:20],
            "common_terms": common_terms[:20],
            "terminology_similarity": round(similarity, 3),
            "total_unique_terms_doc1": len(terms1),
            "total_unique_terms_doc2": len(terms2),
            "analysis": f"Los documentos comparten {len(common_terms)} términos de {len(terms1 | terms2)} totales. Similitud terminológica: {similarity:.1%}"
        }
    
    def _compare_numeric_values(self, doc1: str, doc2: str, id1: str, id2: str) -> dict:
        """
        Compara valores numéricos entre documentos
        Útil para detectar contradicciones en plazos, montos, porcentajes
        """
        # Patrones para diferentes tipos de números
        patterns = {
            "dias": r'(\d+)\s*días?',
            "meses": r'(\d+)\s*meses?',
            "años": r'(\d+)\s*años?',
            "porcentajes": r'(\d+(?:\.\d+)?)\s*%',
            "montos": r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            "numeros_generales": r'\b(\d+)\b'
        }
        
        values1 = {}
        values2 = {}
        
        for category, pattern in patterns.items():
            values1[category] = re.findall(pattern, doc1, re.IGNORECASE)
            values2[category] = re.findall(pattern, doc2, re.IGNORECASE)
        
        # Detectar valores que aparecen en uno pero no en otro
        mismatches = {}
        for category in patterns.keys():
            if category == "numeros_generales":
                continue  # Muy genérico
            
            set1 = set(values1[category])
            set2 = set(values2[category])
            
            if set1 != set2:
                mismatches[category] = {
                    "solo_en_doc1": list(set1 - set2),
                    "solo_en_doc2": list(set2 - set1)
                }
        
        return {
            "comparison_type": "numeric",
            "doc1_id": id1,
            "doc2_id": id2,
            "values_doc1": {k: v[:10] for k, v in values1.items() if k != "numeros_generales"},
            "values_doc2": {k: v[:10] for k, v in values2.items() if k != "numeros_generales"},
            "mismatches": mismatches,
            "potential_contradictions": len(mismatches) > 0,
            "analysis": f"Se encontraron {len(mismatches)} categorías con valores numéricos diferentes"
        }
    
    def _compare_structure(self, doc1: str, doc2: str, id1: str, id2: str) -> dict:
        """
        Compara la estructura de los documentos
        Útil para verificar si siguen el mismo formato
        """
        lines1 = [l.strip() for l in doc1.split('\n') if l.strip()]
        lines2 = [l.strip() for l in doc2.split('\n') if l.strip()]
        
        # Detectar títulos/secciones (líneas que empiezan con números o están en mayúsculas)
        sections1 = [l for l in lines1 if re.match(r'^\d+\.', l) or l.isupper()]
        sections2 = [l for l in lines2 if re.match(r'^\d+\.', l) or l.isupper()]
        
        # Similitud general
        similarity = SequenceMatcher(None, lines1, lines2).ratio()
        
        return {
            "comparison_type": "structure",
            "doc1_id": id1,
            "doc2_id": id2,
            "doc1_lines": len(lines1),
            "doc2_lines": len(lines2),
            "doc1_sections": len(sections1),
            "doc2_sections": len(sections2),
            "structure_similarity": round(similarity, 3),
            "line_difference": abs(len(lines1) - len(lines2)),
            "sections_sample_doc1": sections1[:5],
            "sections_sample_doc2": sections2[:5],
            "analysis": f"Similitud estructural: {similarity:.1%}. Diferencia de {abs(len(lines1) - len(lines2))} líneas."
        }
    
    def _compare_full(self, doc1: str, doc2: str, id1: str, id2: str) -> dict:
        """
        Comparación completa: combina todos los análisis
        """
        terminology = self._compare_terminology(doc1, doc2, id1, id2)
        numeric = self._compare_numeric_values(doc1, doc2, id1, id2)
        structure = self._compare_structure(doc1, doc2, id1, id2)
        
        # Similitud de texto general
        text_similarity = SequenceMatcher(None, doc1, doc2).ratio()
        
        return {
            "comparison_type": "full",
            "doc1_id": id1,
            "doc2_id": id2,
            "text_similarity": round(text_similarity, 3),
            "length_doc1": len(doc1),
            "length_doc2": len(doc2),
            "terminology_analysis": terminology,
            "numeric_analysis": numeric,
            "structure_analysis": structure,
            "summary": {
                "similar_terminology": terminology["terminology_similarity"] > 0.5,
                "has_numeric_differences": numeric["potential_contradictions"],
                "similar_structure": structure["structure_similarity"] > 0.3,
                "overall_similarity": round(text_similarity, 3)
            }
        }
    
    def find_common_phrases(self, doc1: str, doc2: str, min_words: int = 5) -> List[str]:
        """
        Encuentra frases comunes entre dos documentos
        Útil para detectar texto copiado o referencias mutuas
        """
        words1 = doc1.lower().split()
        words2 = doc2.lower().split()
        
        common_phrases = []
        
        # Buscar secuencias comunes
        for i in range(len(words1) - min_words + 1):
            phrase = ' '.join(words1[i:i+min_words])
            if phrase in doc2.lower():
                common_phrases.append(phrase)
        
        # Eliminar duplicados y limitar
        return list(set(common_phrases))[:20]


# Testing
if __name__ == "__main__":
    comparer = DocumentComparer()
    
    print("\n🧪 TESTING DocumentComparer\n")
    
    # Textos de prueba
    doc1 = """
    La empresa otorga un plazo de 30 días para la respuesta.
    El monto máximo es de $5,000 dólares.
    Los usuarios deben cumplir con la Política de Seguridad.
    """
    
    doc2 = """
    La organización establece un plazo de 45 días para respuesta.
    El monto máximo autorizado es de $10,000 dólares.
    Los usuarios deben seguir la Política de Seguridad de Información.
    """
    
    # Test 1: Comparación terminológica
    print("Test 1: Comparación terminológica")
    result = comparer.compare_documents(doc1, doc2, "Doc1", "Doc2", "terminology")
    print(f"✅ Similitud terminológica: {result['terminology_similarity']:.1%}")
    print(f"   Términos únicos Doc1: {result['unique_to_doc1']}")
    print(f"   Términos únicos Doc2: {result['unique_to_doc2']}")
    
    # Test 2: Comparación numérica
    print("\nTest 2: Comparación de valores numéricos")
    result = comparer.compare_documents(doc1, doc2, "Doc1", "Doc2", "numeric")
    print(f"✅ Contradicciones detectadas: {result['potential_contradictions']}")
    if result['mismatches']:
        print(f"   Categorías con diferencias: {list(result['mismatches'].keys())}")
    
    # Test 3: Comparación completa
    print("\nTest 3: Comparación completa")
    result = comparer.compare_documents(doc1, doc2, "Doc1", "Doc2", "full")
    print(f"✅ Similitud general: {result['text_similarity']:.1%}")
    print(f"   Resumen: {result['summary']}")
"""MCP Server: Analizador de contradicciones"""
import re
from typing import List, Dict, Tuple
from datetime import datetime

class ContradictionAnalyzer:
    """
    Detecta contradicciones entre documentos basándose en:
    - Jerarquía (directiva no puede contradecir ley)
    - Patrones comunes (plazos, montos, obligaciones)
    - Terminología inconsistente
    """
    
    def __init__(self):
        # Patrones de elementos que pueden causar contradicciones
        self.contradiction_patterns = {
            # Patrones temporales
            "plazo_dias": r'(\d+)\s*días?',
            "plazo_meses": r'(\d+)\s*meses?',
            "plazo_años": r'(\d+)\s*años?',
            
            # Patrones monetarios
            "monto_soles": r'S/\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            "monto_dolares": r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            "porcentaje": r'(\d+(?:\.\d+)?)\s*%',
            
            # Patrones de obligaciones
            "obligacion": r'(debe|deberá|obligatorio|requerido|necesario|imperativo)',
            "prohibicion": r'(no debe|no deberá|prohibido|vedado|impedido)',
            "opcion": r'(puede|podrá|opcional|facultativo|discrecional)',
            
            # Patrones de autorización
            "autoriza": r'(autoriza|aprueba|permite|habilita)',
            "deniega": r'(deniega|rechaza|impide|prohíbe)',
        }
        
        # Niveles de severidad según tipo de contradicción
        self.severity_weights = {
            "plazo_dias": "high",
            "plazo_meses": "high", 
            "plazo_años": "high",
            "monto_soles": "high",
            "monto_dolares": "high",
            "porcentaje": "medium",
            "obligacion": "critical",
            "prohibicion": "critical",
            "opcion": "medium",
            "autoriza": "high",
            "deniega": "critical",
        }
    
    def detect_contradictions(
        self,
        target_content: str,
        target_metadata: dict,
        rector_contents: List[Tuple[str, dict]],  # [(content, metadata), ...]
        sensitivity: str = "moderate"
    ) -> dict:
        """
        Detecta contradicciones entre documento objetivo y rectores
        
        Args:
            target_content: Contenido del documento a revisar
            target_metadata: Metadata del documento objetivo
            rector_contents: Lista de (contenido, metadata) de documentos rectores
            sensitivity: Nivel de sensibilidad (strict, moderate, flexible)
        
        Returns:
            Dict con contradicciones encontradas y análisis
        """
        
        contradictions = []
        warnings = []
        
        print(f"\n🔍 Analizando: {target_metadata.get('doc_id', 'Documento')}")
        print(f"   Nivel jerárquico: {target_metadata.get('nivel_jerarquico', '?')}")
        print(f"   Documentos rectores a validar: {len(rector_contents)}")
        
        # Extraer datos del documento objetivo
        target_data = self._extract_data(target_content)
        
        # Comparar con cada documento rector
        for rector_content, rector_metadata in rector_contents:
            rector_data = self._extract_data(rector_content)
            
            print(f"\n   Comparando con: {rector_metadata.get('doc_id', 'Rector')}")
            print(f"   Nivel rector: {rector_metadata.get('nivel_jerarquico', '?')}")
            
            # Verificar cada tipo de patrón
            for pattern_type, target_values in target_data.items():
                if pattern_type not in rector_data:
                    continue
                
                rector_values = rector_data[pattern_type]
                
                # Comparar valores
                conflicts = self._compare_values(
                    target_values, 
                    rector_values,
                    pattern_type,
                    sensitivity
                )
                
                for conflict in conflicts:
                    severity = self._calculate_severity(
                        pattern_type,
                        target_metadata.get('nivel_jerarquico', 999),
                        rector_metadata.get('nivel_jerarquico', 1),
                        sensitivity
                    )
                    
                    contradiction = {
                        "type": pattern_type,
                        "severity": severity,
                        "target_value": conflict["target"],
                        "rector_value": conflict["rector"],
                        "rector_doc": rector_metadata.get('doc_id', 'Desconocido'),
                        "rector_level": rector_metadata.get('nivel_jerarquico', 1),
                        "context_target": conflict.get("context_target", ""),
                        "context_rector": conflict.get("context_rector", ""),
                        "description": self._generate_description(
                            pattern_type,
                            conflict["target"],
                            conflict["rector"],
                            rector_metadata.get('doc_id', 'Rector')
                        )
                    }
                    
                    if severity in ["critical", "high"]:
                        contradictions.append(contradiction)
                        print(f"      ❌ CONTRADICCIÓN {severity.upper()}: {pattern_type}")
                    else:
                        warnings.append(contradiction)
                        print(f"      ⚠️  Advertencia: {pattern_type}")
        
        # Calcular compliance score
        total_checks = len(target_data) * len(rector_contents)
        compliance_score = 1.0
        
        if total_checks > 0:
            # Penalizar según severidad
            penalty = 0
            for c in contradictions:
                if c["severity"] == "critical":
                    penalty += 0.2
                elif c["severity"] == "high":
                    penalty += 0.1
                else:
                    penalty += 0.05
            
            compliance_score = max(0, 1.0 - (penalty / max(total_checks, 1)))
        
        return {
            "success": True,
            "contradictions_found": len(contradictions),
            "warnings_found": len(warnings),
            "contradictions": contradictions,
            "warnings": warnings,
            "compliance_score": round(compliance_score, 3),
            "analysis_summary": {
                "critical_issues": len([c for c in contradictions if c["severity"] == "critical"]),
                "high_issues": len([c for c in contradictions if c["severity"] == "high"]),
                "medium_issues": len([c for c in contradictions if c["severity"] == "medium"]),
                "total_rectores_checked": len(rector_contents),
                "recommendation": self._generate_recommendation(contradictions, compliance_score)
            }
        }
    
    def _extract_data(self, content: str) -> Dict[str, List[Dict]]:
        """Extrae datos estructurados del documento según patrones"""
        data = {}
        
        for pattern_type, pattern in self.contradiction_patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            values = []
            
            for match in matches:
                # Capturar contexto (50 caracteres antes y después)
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                context = content[start:end].replace('\n', ' ').strip()
                
                values.append({
                    "value": match.group(1) if match.groups() else match.group(0),
                    "position": match.start(),
                    "context": context
                })
            
            if values:
                data[pattern_type] = values
        
        return data
    
    def _compare_values(
        self,
        target_values: List[Dict],
        rector_values: List[Dict],
        pattern_type: str,
        sensitivity: str
    ) -> List[Dict]:
        """Compara valores y detecta conflictos"""
        conflicts = []
        
        for target_val in target_values:
            for rector_val in rector_values:
                if self._values_conflict(
                    target_val["value"],
                    rector_val["value"],
                    pattern_type,
                    sensitivity
                ):
                    conflicts.append({
                        "target": target_val["value"],
                        "rector": rector_val["value"],
                        "context_target": target_val["context"],
                        "context_rector": rector_val["context"]
                    })
        
        return conflicts
    
    def _values_conflict(
        self,
        target_val: str,
        rector_val: str,
        pattern_type: str,
        sensitivity: str
    ) -> bool:
        """Determina si dos valores están en conflicto"""
        
        # Para valores numéricos
        if pattern_type in ["plazo_dias", "plazo_meses", "plazo_años", "porcentaje"]:
            try:
                t = float(target_val)
                r = float(rector_val)
                
                # Sensibilidad afecta el umbral de diferencia
                if sensitivity == "strict":
                    return t != r
                elif sensitivity == "moderate":
                    return abs(t - r) > (r * 0.1)  # >10% diferencia
                else:  # flexible
                    return abs(t - r) > (r * 0.2)  # >20% diferencia
            except:
                return False
        
        # Para montos
        if pattern_type in ["monto_soles", "monto_dolares"]:
            try:
                t = float(target_val.replace(',', ''))
                r = float(rector_val.replace(',', ''))
                
                if sensitivity == "strict":
                    return t != r
                else:
                    return abs(t - r) > (r * 0.05)  # >5% diferencia
            except:
                return False
        
        # Para obligaciones (conflictos lógicos)
        if pattern_type in ["obligacion", "prohibicion", "opcion"]:
            # Simplificado: detectar oposiciones semánticas
            opposites = {
                "debe": ["no debe", "puede"],
                "obligatorio": ["opcional", "prohibido"],
                "requerido": ["opcional"],
            }
            
            for key, vals in opposites.items():
                if key in target_val.lower():
                    for opp in vals:
                        if opp in rector_val.lower():
                            return True
        
        return False
    
    def _calculate_severity(
        self,
        pattern_type: str,
        target_level: int,
        rector_level: int,
        sensitivity: str
    ) -> str:
        """Calcula severidad de la contradicción"""
        
        base_severity = self.severity_weights.get(pattern_type, "medium")
        
        # Si es un documento de bajo nivel contradiciendo a uno superior
        # aumentar severidad
        level_diff = target_level - rector_level
        
        if level_diff > 2 and base_severity == "medium":
            base_severity = "high"
        
        if base_severity == "high" and sensitivity == "strict":
            base_severity = "critical"
        
        return base_severity
    
    def _generate_description(
        self,
        pattern_type: str,
        target_val: str,
        rector_val: str,
        rector_doc: str
    ) -> str:
        """Genera descripción legible de la contradicción"""
        
        descriptions = {
            "plazo_dias": f"El documento establece {target_val} días, pero {rector_doc} requiere {rector_val} días",
            "plazo_meses": f"El documento indica {target_val} meses, pero {rector_doc} establece {rector_val} meses",
            "monto_soles": f"El monto de S/ {target_val} difiere del monto en {rector_doc}: S/ {rector_val}",
            "monto_dolares": f"El monto de $ {target_val} difiere del monto en {rector_doc}: $ {rector_val}",
            "porcentaje": f"El porcentaje de {target_val}% difiere del establecido en {rector_doc}: {rector_val}%",
            "obligacion": f"Posible conflicto de obligaciones con {rector_doc}",
        }
        
        return descriptions.get(
            pattern_type,
            f"Diferencia detectada: '{target_val}' vs '{rector_val}' en {rector_doc}"
        )
    
    def _generate_recommendation(self, contradictions: List[Dict], score: float) -> str:
        """Genera recomendación basada en el análisis"""
        
        if score >= 0.9:
            return "✅ El documento cumple con los requisitos normativos"
        elif score >= 0.7:
            return "⚠️ El documento tiene algunas inconsistencias que deben revisarse"
        elif score >= 0.5:
            return "❌ El documento presenta contradicciones importantes que requieren corrección"
        else:
            return "🚨 El documento tiene contradicciones críticas y debe ser reescrito"


# Testing
if __name__ == "__main__":
    analyzer = ContradictionAnalyzer()
    
    print("\n🧪 TESTING ContradictionAnalyzer\n")
    
    # Documento objetivo (directiva)
    target = """
    La unidad otorga un plazo de 30 días para la respuesta.
    El presupuesto máximo autorizado es de $5,000 dólares.
    Los usuarios pueden opcionalmente usar autenticación multifactor.
    """
    
    target_meta = {
        "doc_id": "DIR_TEST_001",
        "nivel_jerarquico": 4,
        "tipo": "DIR"
    }
    
    # Documento rector (ley)
    rector = """
    Todas las entidades deben otorgar un plazo mínimo de 45 días.
    El presupuesto autorizado no debe exceder $10,000 dólares.
    La autenticación multifactor es obligatoria para todos los usuarios.
    """
    
    rector_meta = {
        "doc_id": "LEY_RECTOR_001",
        "nivel_jerarquico": 1,
        "tipo": "LEY"
    }
    
    # Ejecutar análisis
    result = analyzer.detect_contradictions(
        target_content=target,
        target_metadata=target_meta,
        rector_contents=[(rector, rector_meta)],
        sensitivity="moderate"
    )
    
    print("\n" + "="*80)
    print("📊 RESULTADOS DEL ANÁLISIS")
    print("="*80)
    print(f"Contradicciones encontradas: {result['contradictions_found']}")
    print(f"Advertencias: {result['warnings_found']}")
    print(f"Score de cumplimiento: {result['compliance_score']:.1%}")
    print(f"\n{result['analysis_summary']['recommendation']}")
    
    if result['contradictions']:
        print(f"\n🚨 CONTRADICCIONES CRÍTICAS/ALTAS:")
        for c in result['contradictions']:
            print(f"\n  [{c['severity'].upper()}] {c['type']}")
            print(f"  {c['description']}")
            print(f"  Contexto: ...{c['context_target'][:60]}...")
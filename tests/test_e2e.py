"""
DATAPOLIS v3.0 - Test End-to-End del Flujo Principal
=====================================================

Este test verifica el flujo completo:
M00 Expediente → M01 Ficha → M04 Valorización → M03 Scoring → M13 Garantías → M16 Basel IV

Ejecutar con: pytest tests/test_e2e.py -v
"""

import pytest
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import os

# Configuración
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
FASTAPI_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8001/api/v1")
TEST_EMAIL = os.getenv("TEST_EMAIL", "admin@datapolis.cl")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "admin123")


class TestDatapolisE2E:
    """Test End-to-End del flujo principal de DATAPOLIS"""
    
    token: Optional[str] = None
    expediente_id: Optional[int] = None
    propiedad_id: Optional[int] = None
    copropiedad_id: Optional[int] = None
    avaluo_id: Optional[int] = None
    score_result: Optional[dict] = None
    garantia_id: Optional[int] = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para cada test"""
        self.client = httpx.Client(timeout=30.0)
        yield
        self.client.close()
    
    # =========================================================================
    # 1. AUTENTICACIÓN
    # =========================================================================
    
    def test_01_login(self):
        """Test de login y obtención de token"""
        response = self.client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        
        TestDatapolisE2E.token = data["access_token"]
        print(f"✓ Login exitoso - Token: {self.token[:20]}...")
    
    def get_headers(self):
        """Retorna headers con autorización"""
        return {
            "Authorization": f"Bearer {TestDatapolisE2E.token}",
            "Content-Type": "application/json"
        }
    
    # =========================================================================
    # 2. M00 - CREAR EXPEDIENTE
    # =========================================================================
    
    def test_02_crear_expediente(self):
        """M00: Crear expediente inmobiliario"""
        response = self.client.post(
            f"{BASE_URL}/expedientes",
            headers=self.get_headers(),
            json={
                "titulo": "Expediente Test E2E",
                "tipo": "compraventa",
                "descripcion": "Expediente creado por test E2E automatizado",
                "fecha_inicio": datetime.now().isoformat(),
                "estado": "activo",
                "prioridad": "alta",
                "metadata": {
                    "test": True,
                    "created_by": "pytest"
                }
            }
        )
        
        assert response.status_code == 201, f"Crear expediente falló: {response.text}"
        
        data = response.json()
        assert "id" in data
        
        TestDatapolisE2E.expediente_id = data["id"]
        print(f"✓ Expediente creado - ID: {self.expediente_id}")
    
    # =========================================================================
    # 3. M01 - CREAR PROPIEDAD Y VINCULAR A EXPEDIENTE
    # =========================================================================
    
    def test_03_crear_propiedad(self):
        """M01: Crear ficha de propiedad"""
        response = self.client.post(
            f"{BASE_URL}/propiedades",
            headers=self.get_headers(),
            json={
                "rol": "123-456",
                "direccion": "Av. Test 1234",
                "comuna": "Providencia",
                "region": "Metropolitana",
                "tipo": "departamento",
                "superficie_total": 85.5,
                "superficie_util": 72.0,
                "dormitorios": 3,
                "banos": 2,
                "estacionamientos": 1,
                "bodega": True,
                "ano_construccion": 2015,
                "orientacion": "norte",
                "piso": 8,
                "estado_conservacion": "bueno",
                "coordenadas": {
                    "lat": -33.4256,
                    "lng": -70.6092
                }
            }
        )
        
        assert response.status_code == 201, f"Crear propiedad falló: {response.text}"
        
        data = response.json()
        TestDatapolisE2E.propiedad_id = data["id"]
        print(f"✓ Propiedad creada - ID: {self.propiedad_id}")
    
    def test_04_vincular_expediente_propiedad(self):
        """Vincular expediente con propiedad"""
        response = self.client.post(
            f"{BASE_URL}/expedientes/{TestDatapolisE2E.expediente_id}/vincular",
            headers=self.get_headers(),
            json={
                "propiedad_id": TestDatapolisE2E.propiedad_id,
                "tipo_vinculo": "principal"
            }
        )
        
        assert response.status_code in [200, 201], f"Vincular falló: {response.text}"
        print(f"✓ Expediente {self.expediente_id} vinculado a propiedad {self.propiedad_id}")
    
    # =========================================================================
    # 4. M04 - VALORIZACIÓN ML
    # =========================================================================
    
    def test_05_generar_avaluo_ml(self):
        """M04: Generar avalúo con modelo ML"""
        response = self.client.post(
            f"{FASTAPI_URL}/valorizacion/avaluo",
            headers=self.get_headers(),
            json={
                "propiedad_id": TestDatapolisE2E.propiedad_id,
                "metodo": "ml_ensemble",
                "include_comparables": True,
                "confidence_level": 0.95
            }
        )
        
        assert response.status_code == 200, f"Avalúo falló: {response.text}"
        
        data = response.json()
        assert "valor_uf" in data
        assert "confidence" in data
        assert data["valor_uf"] > 0
        assert 0 <= data["confidence"] <= 1
        
        TestDatapolisE2E.avaluo_id = data.get("id")
        print(f"✓ Avalúo generado - Valor: {data['valor_uf']} UF (confianza: {data['confidence']:.2%})")
    
    # =========================================================================
    # 5. M02 - CREAR COPROPIEDAD (para contexto)
    # =========================================================================
    
    def test_06_crear_copropiedad(self):
        """M02: Crear copropiedad para testing"""
        response = self.client.post(
            f"{BASE_URL}/copropiedades",
            headers=self.get_headers(),
            json={
                "nombre": "Edificio Test E2E",
                "rut": "76.999.999-9",
                "direccion": "Av. Test 1234",
                "comuna": "Providencia",
                "region": "Metropolitana",
                "total_unidades": 50,
                "prorrateo_type": "metros",
                "fecha_inscripcion": datetime.now().isoformat()
            }
        )
        
        assert response.status_code == 201, f"Crear copropiedad falló: {response.text}"
        
        data = response.json()
        TestDatapolisE2E.copropiedad_id = data["id"]
        print(f"✓ Copropiedad creada - ID: {self.copropiedad_id}")
    
    # =========================================================================
    # 6. M03 - CREDIT SCORING BASEL IV
    # =========================================================================
    
    def test_07_calcular_credit_score(self):
        """M03: Calcular Credit Score Basel IV"""
        response = self.client.post(
            f"{FASTAPI_URL}/creditscore/calculate",
            headers=self.get_headers(),
            json={
                "entity_type": "copropiedad",
                "entity_id": TestDatapolisE2E.copropiedad_id,
                "include_history": True,
                "calculate_components": True
            }
        )
        
        assert response.status_code == 200, f"Credit Score falló: {response.text}"
        
        data = response.json()
        assert "score" in data
        assert "grade" in data
        assert "pd" in data  # Probability of Default
        assert "lgd" in data  # Loss Given Default
        
        # Validar rangos
        assert 300 <= data["score"] <= 850
        assert data["grade"] in ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]
        assert 0 <= data["pd"] <= 1
        assert 0 <= data["lgd"] <= 1
        
        TestDatapolisE2E.score_result = data
        print(f"✓ Credit Score: {data['score']} ({data['grade']}) - PD: {data['pd']:.4f}")
    
    # =========================================================================
    # 7. M13 - REGISTRAR GARANTÍA
    # =========================================================================
    
    def test_08_registrar_garantia(self):
        """M13: Registrar garantía/colateral"""
        avaluo_valor = 5000  # UF por defecto si no hay avalúo
        if hasattr(self, 'avaluo_id') and self.avaluo_id:
            # Obtener valor del avalúo
            response = self.client.get(
                f"{FASTAPI_URL}/valorizacion/avaluo/{TestDatapolisE2E.avaluo_id}",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                avaluo_valor = response.json().get("valor_uf", 5000)
        
        response = self.client.post(
            f"{BASE_URL}/garantias",
            headers=self.get_headers(),
            json={
                "propiedad_id": TestDatapolisE2E.propiedad_id,
                "tipo": "hipoteca",
                "valor_uf": avaluo_valor,
                "ltv": 0.80,  # Loan-to-Value 80%
                "fecha_constitucion": datetime.now().isoformat(),
                "estado": "vigente",
                "acreedor": "Banco Test",
                "metadata": {
                    "expediente_id": TestDatapolisE2E.expediente_id
                }
            }
        )
        
        assert response.status_code == 201, f"Registrar garantía falló: {response.text}"
        
        data = response.json()
        TestDatapolisE2E.garantia_id = data["id"]
        print(f"✓ Garantía registrada - ID: {self.garantia_id}, LTV: 80%")
    
    # =========================================================================
    # 8. M16 - VALIDACIÓN BASEL IV
    # =========================================================================
    
    def test_09_validar_basel_iv(self):
        """M16: Validar cumplimiento Basel IV"""
        response = self.client.post(
            f"{FASTAPI_URL}/basel/validate",
            headers=self.get_headers(),
            json={
                "entity_type": "copropiedad",
                "entity_id": TestDatapolisE2E.copropiedad_id,
                "garantia_id": TestDatapolisE2E.garantia_id,
                "credit_score": TestDatapolisE2E.score_result,
                "exposure_amount": 4000,  # UF
                "validate_components": ["cr_sa", "output_floor", "capital_requirements"]
            }
        )
        
        assert response.status_code == 200, f"Validación Basel IV falló: {response.text}"
        
        data = response.json()
        assert "rwa" in data  # Risk Weighted Assets
        assert "capital_required" in data
        assert "compliant" in data
        
        print(f"✓ Basel IV Validado - RWA: {data['rwa']:.2f} UF, Cumple: {data['compliant']}")
    
    # =========================================================================
    # 9. M11 - ANÁLISIS PAE
    # =========================================================================
    
    def test_10_analisis_pae(self):
        """M11: Ejecutar análisis PAE (Precession Analysis Engine)"""
        response = self.client.post(
            f"{BASE_URL}/copropiedades/{TestDatapolisE2E.copropiedad_id}/pae/analyze",
            headers=self.get_headers(),
            json={
                "include_projections": True,
                "horizon_months": 12,
                "include_recommendations": True
            }
        )
        
        assert response.status_code == 200, f"PAE Analysis falló: {response.text}"
        
        data = response.json()
        assert "score_total" in data
        assert "scores" in data
        assert "alerts" in data
        
        # Validar score total
        assert 0 <= data["score_total"] <= 100
        
        # Validar scores por dimensión
        scores = data["scores"]
        for dimension in ["financial", "compliance", "operational", "risk", "governance"]:
            if dimension in scores:
                assert 0 <= scores[dimension] <= 100
        
        print(f"✓ PAE Score Total: {data['score_total']:.1f}/100")
        print(f"  - Financial: {scores.get('financial', 'N/A')}")
        print(f"  - Compliance: {scores.get('compliance', 'N/A')}")
        print(f"  - Alertas activas: {len(data.get('alerts', []))}")
    
    # =========================================================================
    # 10. VERIFICACIÓN FINAL
    # =========================================================================
    
    def test_11_verificacion_flujo_completo(self):
        """Verificar que todo el flujo se completó correctamente"""
        # Verificar que todos los IDs fueron creados
        assert TestDatapolisE2E.expediente_id is not None, "Expediente no creado"
        assert TestDatapolisE2E.propiedad_id is not None, "Propiedad no creada"
        assert TestDatapolisE2E.copropiedad_id is not None, "Copropiedad no creada"
        assert TestDatapolisE2E.score_result is not None, "Credit Score no calculado"
        assert TestDatapolisE2E.garantia_id is not None, "Garantía no registrada"
        
        print("\n" + "="*60)
        print("FLUJO E2E COMPLETADO EXITOSAMENTE")
        print("="*60)
        print(f"  Expediente ID: {self.expediente_id}")
        print(f"  Propiedad ID: {self.propiedad_id}")
        print(f"  Copropiedad ID: {self.copropiedad_id}")
        print(f"  Garantía ID: {self.garantia_id}")
        print(f"  Credit Score: {self.score_result['score']} ({self.score_result['grade']})")
        print("="*60)
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def test_99_cleanup(self):
        """Limpiar datos de prueba (opcional)"""
        # Solo ejecutar si se desea limpiar
        if os.getenv("CLEANUP_TEST_DATA", "false").lower() != "true":
            print("⚠ Cleanup saltado (set CLEANUP_TEST_DATA=true para limpiar)")
            return
        
        # Eliminar garantía
        if TestDatapolisE2E.garantia_id:
            self.client.delete(
                f"{BASE_URL}/garantias/{TestDatapolisE2E.garantia_id}",
                headers=self.get_headers()
            )
        
        # Eliminar copropiedad
        if TestDatapolisE2E.copropiedad_id:
            self.client.delete(
                f"{BASE_URL}/copropiedades/{TestDatapolisE2E.copropiedad_id}",
                headers=self.get_headers()
            )
        
        # Eliminar propiedad
        if TestDatapolisE2E.propiedad_id:
            self.client.delete(
                f"{BASE_URL}/propiedades/{TestDatapolisE2E.propiedad_id}",
                headers=self.get_headers()
            )
        
        # Eliminar expediente
        if TestDatapolisE2E.expediente_id:
            self.client.delete(
                f"{BASE_URL}/expedientes/{TestDatapolisE2E.expediente_id}",
                headers=self.get_headers()
            )
        
        print("✓ Datos de prueba eliminados")


# =========================================================================
# TESTS ADICIONALES DE HEALTH CHECK
# =========================================================================

class TestHealthChecks:
    """Tests de verificación de servicios"""
    
    def test_laravel_health(self):
        """Verificar que Laravel API está funcionando"""
        with httpx.Client() as client:
            response = client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "healthy"
            print(f"✓ Laravel API: {data}")
    
    def test_fastapi_health(self):
        """Verificar que FastAPI está funcionando"""
        with httpx.Client() as client:
            response = client.get(f"{FASTAPI_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "healthy"
            print(f"✓ FastAPI: {data}")
    
    def test_database_connection(self):
        """Verificar conexión a base de datos"""
        with httpx.Client() as client:
            response = client.get(f"{BASE_URL}/health/database")
            # Puede no existir este endpoint, pero si existe debe responder
            if response.status_code == 200:
                data = response.json()
                assert data.get("database") == "connected"
                print(f"✓ Database: {data}")
            else:
                print("⚠ Endpoint /health/database no disponible")


# =========================================================================
# EJECUCIÓN DIRECTA
# =========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

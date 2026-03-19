"""
================================================================================
MÓDULOS FINTECH ADICIONALES - DATAPOLIS ENTERPRISE
================================================================================

Módulos especializados para cumplimiento regulatorio financiero:
- M02: TNFD Nature Risk Framework
- M04: Basel IV Capital Requirements (CR-SA)
- M05: Supply Chain Finance ESG
- M06: Blockchain Condominios (estructura base)

Autor: DATAPOLIS SpA
Versión: 2.0.0
Fecha: Febrero 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from decimal import Decimal
import uuid


# ==============================================================================
# M02: TNFD NATURE RISK FRAMEWORK
# ==============================================================================
# Taskforce on Nature-related Financial Disclosures
# Framework LEAP: Locate, Evaluate, Assess, Prepare

class TNFDCategory(Enum):
    """Categorías de riesgo TNFD."""
    PHYSICAL = "physical"
    TRANSITION = "transition"
    SYSTEMIC = "systemic"

class TNFDAssetClass(Enum):
    """Clases de activos para análisis TNFD."""
    REAL_ESTATE = "real_estate"
    AGRICULTURE = "agriculture"
    FORESTRY = "forestry"
    INFRASTRUCTURE = "infrastructure"
    EXTRACTIVE = "extractive"

class TNFDDependency(Enum):
    """Dependencias de servicios ecosistémicos."""
    WATER_SUPPLY = "water_supply"
    POLLINATION = "pollination"
    SOIL_QUALITY = "soil_quality"
    CLIMATE_REGULATION = "climate_regulation"
    FLOOD_PROTECTION = "flood_protection"
    BIODIVERSITY = "biodiversity"

@dataclass
class TNFDAssessment:
    """Evaluación TNFD de un activo."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str = ""
    asset_type: TNFDAssetClass = TNFDAssetClass.REAL_ESTATE
    location_lat: float = 0.0
    location_lon: float = 0.0
    
    # LEAP Analysis
    dependencies: List[TNFDDependency] = field(default_factory=list)
    impacts: Dict[str, float] = field(default_factory=dict)
    
    # Risk Scores (0-100)
    physical_risk_score: float = 0.0
    transition_risk_score: float = 0.0
    systemic_risk_score: float = 0.0
    overall_nature_risk: float = 0.0
    
    # Metrics
    biodiversity_footprint: float = 0.0  # MSA (Mean Species Abundance)
    water_stress_index: float = 0.0
    deforestation_risk: float = 0.0
    
    assessment_date: datetime = field(default_factory=datetime.now)
    
    def calcular_riesgo_total(self) -> float:
        """Calcula el riesgo total TNFD."""
        self.overall_nature_risk = (
            self.physical_risk_score * 0.4 +
            self.transition_risk_score * 0.35 +
            self.systemic_risk_score * 0.25
        )
        return self.overall_nature_risk

class TNFDAnalyzer:
    """Analizador TNFD con framework LEAP."""
    
    def __init__(self):
        self._assessments: Dict[str, TNFDAssessment] = {}
        
    def locate_interface(
        self,
        lat: float,
        lon: float,
        asset_type: TNFDAssetClass
    ) -> Dict[str, Any]:
        """LEAP - Locate: Identifica interfaz con naturaleza."""
        # En producción: consultar capas GIS de áreas protegidas, biodiversidad, etc.
        return {
            "protected_area_proximity_km": 5.2,
            "biodiversity_hotspot": False,
            "watershed_sensitivity": "medium",
            "forest_cover_pct": 12.5,
            "wetland_proximity_km": 2.8
        }
    
    def evaluate_dependencies(
        self,
        asset_type: TNFDAssetClass,
        location_data: Dict[str, Any]
    ) -> List[TNFDDependency]:
        """LEAP - Evaluate: Evalúa dependencias ecosistémicas."""
        dependencies = []
        
        if asset_type == TNFDAssetClass.REAL_ESTATE:
            dependencies.extend([
                TNFDDependency.WATER_SUPPLY,
                TNFDDependency.FLOOD_PROTECTION,
                TNFDDependency.CLIMATE_REGULATION
            ])
        elif asset_type == TNFDAssetClass.AGRICULTURE:
            dependencies.extend([
                TNFDDependency.WATER_SUPPLY,
                TNFDDependency.POLLINATION,
                TNFDDependency.SOIL_QUALITY
            ])
        
        return dependencies
    
    def assess_risks(
        self,
        asset_id: str,
        asset_type: TNFDAssetClass,
        lat: float,
        lon: float
    ) -> TNFDAssessment:
        """LEAP - Assess: Evalúa riesgos y oportunidades."""
        
        # Locate
        location_data = self.locate_interface(lat, lon, asset_type)
        
        # Evaluate
        dependencies = self.evaluate_dependencies(asset_type, location_data)
        
        # Calculate risks
        physical_risk = self._calcular_riesgo_fisico(location_data)
        transition_risk = self._calcular_riesgo_transicion(asset_type, location_data)
        systemic_risk = self._calcular_riesgo_sistemico(dependencies)
        
        assessment = TNFDAssessment(
            asset_id=asset_id,
            asset_type=asset_type,
            location_lat=lat,
            location_lon=lon,
            dependencies=dependencies,
            physical_risk_score=physical_risk,
            transition_risk_score=transition_risk,
            systemic_risk_score=systemic_risk,
            water_stress_index=location_data.get("watershed_sensitivity", 0),
            biodiversity_footprint=0.85  # Simplificado
        )
        
        assessment.calcular_riesgo_total()
        self._assessments[assessment.id] = assessment
        
        return assessment
    
    def prepare_disclosure(
        self,
        assessment_id: str
    ) -> Dict[str, Any]:
        """LEAP - Prepare: Prepara disclosure TNFD."""
        
        if assessment_id not in self._assessments:
            return {"error": "Assessment not found"}
        
        assessment = self._assessments[assessment_id]
        
        return {
            "framework": "TNFD v1.0",
            "assessment_date": assessment.assessment_date.isoformat(),
            "asset_id": assessment.asset_id,
            "location": {
                "latitude": assessment.location_lat,
                "longitude": assessment.location_lon
            },
            "nature_interface": {
                "asset_class": assessment.asset_type.value,
                "dependencies": [d.value for d in assessment.dependencies]
            },
            "risk_assessment": {
                "physical_risk": round(assessment.physical_risk_score, 1),
                "transition_risk": round(assessment.transition_risk_score, 1),
                "systemic_risk": round(assessment.systemic_risk_score, 1),
                "overall_nature_risk": round(assessment.overall_nature_risk, 1)
            },
            "metrics": {
                "biodiversity_footprint_msa": assessment.biodiversity_footprint,
                "water_stress_index": assessment.water_stress_index
            },
            "recommendations": self._generar_recomendaciones(assessment)
        }
    
    def _calcular_riesgo_fisico(self, location_data: Dict[str, Any]) -> float:
        """Calcula riesgo físico basado en ubicación."""
        risk = 25.0  # Base
        
        if location_data.get("protected_area_proximity_km", 999) < 5:
            risk += 20
        if location_data.get("biodiversity_hotspot", False):
            risk += 25
        if location_data.get("forest_cover_pct", 0) < 10:
            risk += 15
            
        return min(risk, 100)
    
    def _calcular_riesgo_transicion(
        self,
        asset_type: TNFDAssetClass,
        location_data: Dict[str, Any]
    ) -> float:
        """Calcula riesgo de transición regulatoria."""
        risk = 30.0  # Base
        
        # Sectores con mayor riesgo de transición
        high_risk_sectors = [TNFDAssetClass.EXTRACTIVE, TNFDAssetClass.AGRICULTURE]
        if asset_type in high_risk_sectors:
            risk += 25
            
        return min(risk, 100)
    
    def _calcular_riesgo_sistemico(self, dependencies: List[TNFDDependency]) -> float:
        """Calcula riesgo sistémico basado en dependencias."""
        critical_deps = [
            TNFDDependency.WATER_SUPPLY,
            TNFDDependency.POLLINATION,
            TNFDDependency.BIODIVERSITY
        ]
        
        risk = 20.0
        for dep in dependencies:
            if dep in critical_deps:
                risk += 15
                
        return min(risk, 100)
    
    def _generar_recomendaciones(self, assessment: TNFDAssessment) -> List[str]:
        """Genera recomendaciones basadas en el assessment."""
        recomendaciones = []
        
        if assessment.overall_nature_risk > 70:
            recomendaciones.append("Implementar plan de mitigación de riesgos naturales prioritario")
        
        if TNFDDependency.WATER_SUPPLY in assessment.dependencies:
            recomendaciones.append("Desarrollar estrategia de gestión hídrica sostenible")
        
        if assessment.biodiversity_footprint < 0.7:
            recomendaciones.append("Considerar compensación de biodiversidad o restauración ecológica")
            
        return recomendaciones


# ==============================================================================
# M04: BASEL IV CAPITAL REQUIREMENTS (CR-SA)
# ==============================================================================
# Credit Risk - Standardised Approach

class AssetClass(Enum):
    """Clases de activo Basel IV."""
    SOVEREIGN = "sovereign"
    BANK = "bank"
    CORPORATE = "corporate"
    RETAIL = "retail"
    RESIDENTIAL_MORTGAGE = "residential_mortgage"
    COMMERCIAL_REAL_ESTATE = "commercial_real_estate"
    SPECIALIZED_LENDING = "specialized_lending"
    EQUITY = "equity"
    
class RatingCategory(Enum):
    """Categorías de rating externo."""
    AAA_AA = "AAA_to_AA"
    A = "A"
    BBB = "BBB"
    BB = "BB"
    B = "B"
    CCC_BELOW = "CCC_and_below"
    UNRATED = "unrated"

@dataclass
class BaselIVExposure:
    """Exposición crediticia bajo Basel IV."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    counterparty_id: str = ""
    counterparty_name: str = ""
    asset_class: AssetClass = AssetClass.CORPORATE
    rating: RatingCategory = RatingCategory.UNRATED
    
    # Montos
    exposure_gross: Decimal = Decimal("0")
    collateral_value: Decimal = Decimal("0")
    guarantee_value: Decimal = Decimal("0")
    
    # Para hipotecas
    ltv_ratio: float = 0.0  # Loan-to-Value
    property_value: Decimal = Decimal("0")
    
    # Calculados
    exposure_net: Decimal = Decimal("0")
    risk_weight: float = 0.0
    rwa: Decimal = Decimal("0")  # Risk-Weighted Assets
    
    def calcular_ead(self) -> Decimal:
        """Calcula Exposure at Default."""
        self.exposure_net = max(
            Decimal("0"),
            self.exposure_gross - self.collateral_value - self.guarantee_value
        )
        return self.exposure_net

@dataclass
class CapitalRequirement:
    """Requerimientos de capital Basel IV."""
    total_rwa: Decimal = Decimal("0")
    credit_risk_rwa: Decimal = Decimal("0")
    market_risk_rwa: Decimal = Decimal("0")
    operational_risk_rwa: Decimal = Decimal("0")
    
    # Ratios de capital
    cet1_ratio: float = 0.0
    tier1_ratio: float = 0.0
    total_capital_ratio: float = 0.0
    
    # Buffers
    capital_conservation_buffer: float = 2.5
    countercyclical_buffer: float = 0.0
    systemic_buffer: float = 0.0
    
    # Capital disponible
    cet1_capital: Decimal = Decimal("0")
    at1_capital: Decimal = Decimal("0")
    tier2_capital: Decimal = Decimal("0")

class BaselIVCalculator:
    """Calculadora de capital regulatorio Basel IV CR-SA."""
    
    # Ponderadores de riesgo por clase de activo y rating (Basel IV)
    RISK_WEIGHTS = {
        AssetClass.SOVEREIGN: {
            RatingCategory.AAA_AA: 0.0,
            RatingCategory.A: 0.20,
            RatingCategory.BBB: 0.50,
            RatingCategory.BB: 1.00,
            RatingCategory.B: 1.00,
            RatingCategory.CCC_BELOW: 1.50,
            RatingCategory.UNRATED: 1.00
        },
        AssetClass.BANK: {
            RatingCategory.AAA_AA: 0.20,
            RatingCategory.A: 0.30,
            RatingCategory.BBB: 0.50,
            RatingCategory.BB: 1.00,
            RatingCategory.B: 1.00,
            RatingCategory.CCC_BELOW: 1.50,
            RatingCategory.UNRATED: 0.50
        },
        AssetClass.CORPORATE: {
            RatingCategory.AAA_AA: 0.20,
            RatingCategory.A: 0.50,
            RatingCategory.BBB: 0.75,
            RatingCategory.BB: 1.00,
            RatingCategory.B: 1.50,
            RatingCategory.CCC_BELOW: 1.50,
            RatingCategory.UNRATED: 1.00
        },
        AssetClass.RETAIL: {
            RatingCategory.UNRATED: 0.75  # Retail siempre 75%
        },
        AssetClass.RESIDENTIAL_MORTGAGE: {
            # Basado en LTV - simplificado
            RatingCategory.UNRATED: 0.35  # LTV <= 80%
        }
    }
    
    # Ponderadores para hipotecas residenciales por LTV (Basel IV)
    MORTGAGE_RW_BY_LTV = {
        50: 0.20,   # LTV <= 50%
        60: 0.25,   # 50% < LTV <= 60%
        70: 0.30,   # 60% < LTV <= 70%
        80: 0.35,   # 70% < LTV <= 80%
        90: 0.40,   # 80% < LTV <= 90%
        100: 0.50,  # 90% < LTV <= 100%
        999: 0.70   # LTV > 100%
    }
    
    def __init__(self):
        self._exposures: Dict[str, BaselIVExposure] = {}
        
    def agregar_exposicion(self, exposure: BaselIVExposure) -> str:
        """Agrega una exposición al portfolio."""
        self._exposures[exposure.id] = exposure
        return exposure.id
    
    def calcular_risk_weight(self, exposure: BaselIVExposure) -> float:
        """Calcula el ponderador de riesgo para una exposición."""
        
        # Caso especial: hipotecas residenciales
        if exposure.asset_class == AssetClass.RESIDENTIAL_MORTGAGE:
            return self._calcular_rw_hipoteca(exposure)
        
        # Obtener RW de tabla
        asset_weights = self.RISK_WEIGHTS.get(exposure.asset_class, {})
        rw = asset_weights.get(exposure.rating, 1.0)
        
        exposure.risk_weight = rw
        return rw
    
    def _calcular_rw_hipoteca(self, exposure: BaselIVExposure) -> float:
        """Calcula RW para hipoteca residencial según LTV."""
        ltv = exposure.ltv_ratio * 100  # Convertir a porcentaje
        
        for ltv_threshold, rw in sorted(self.MORTGAGE_RW_BY_LTV.items()):
            if ltv <= ltv_threshold:
                exposure.risk_weight = rw
                return rw
        
        return 0.70  # Default para LTV muy alto
    
    def calcular_rwa(self, exposure: BaselIVExposure) -> Decimal:
        """Calcula RWA para una exposición."""
        
        # Calcular EAD
        exposure.calcular_ead()
        
        # Calcular RW
        rw = self.calcular_risk_weight(exposure)
        
        # RWA = EAD × RW
        exposure.rwa = exposure.exposure_net * Decimal(str(rw))
        
        return exposure.rwa
    
    def calcular_capital_portfolio(self) -> CapitalRequirement:
        """Calcula requerimientos de capital para el portfolio."""
        
        total_rwa = Decimal("0")
        
        for exposure in self._exposures.values():
            self.calcular_rwa(exposure)
            total_rwa += exposure.rwa
        
        req = CapitalRequirement(
            total_rwa=total_rwa,
            credit_risk_rwa=total_rwa
        )
        
        return req
    
    def calcular_ratio_capital(
        self,
        cet1_capital: Decimal,
        at1_capital: Decimal,
        tier2_capital: Decimal
    ) -> CapitalRequirement:
        """Calcula ratios de capital."""
        
        req = self.calcular_capital_portfolio()
        
        req.cet1_capital = cet1_capital
        req.at1_capital = at1_capital
        req.tier2_capital = tier2_capital
        
        if req.total_rwa > 0:
            req.cet1_ratio = float(cet1_capital / req.total_rwa) * 100
            req.tier1_ratio = float((cet1_capital + at1_capital) / req.total_rwa) * 100
            req.total_capital_ratio = float(
                (cet1_capital + at1_capital + tier2_capital) / req.total_rwa
            ) * 100
        
        return req
    
    def verificar_cumplimiento(self, req: CapitalRequirement) -> Dict[str, Any]:
        """Verifica cumplimiento de mínimos regulatorios."""
        
        # Mínimos Basel IV
        min_cet1 = 4.5
        min_tier1 = 6.0
        min_total = 8.0
        
        # Con buffer de conservación
        min_cet1_buffer = min_cet1 + req.capital_conservation_buffer
        
        return {
            "cet1_cumple": req.cet1_ratio >= min_cet1_buffer,
            "cet1_ratio": round(req.cet1_ratio, 2),
            "cet1_minimo": min_cet1_buffer,
            "cet1_exceso": round(req.cet1_ratio - min_cet1_buffer, 2),
            
            "tier1_cumple": req.tier1_ratio >= min_tier1,
            "tier1_ratio": round(req.tier1_ratio, 2),
            
            "total_cumple": req.total_capital_ratio >= min_total,
            "total_ratio": round(req.total_capital_ratio, 2),
            
            "total_rwa": float(req.total_rwa)
        }
    
    def output_floor_adjustment(
        self,
        irb_rwa: Decimal,
        floor_percentage: float = 0.725  # 72.5% Basel IV final
    ) -> Decimal:
        """Aplica output floor de Basel IV."""
        
        # Calcular RWA estándar
        std_req = self.calcular_capital_portfolio()
        
        # Floor = 72.5% del RWA estándar
        floor_rwa = std_req.total_rwa * Decimal(str(floor_percentage))
        
        # RWA final = max(IRB RWA, Floor)
        return max(irb_rwa, floor_rwa)


# ==============================================================================
# M05: SUPPLY CHAIN FINANCE + ESG
# ==============================================================================

class ESGRating(Enum):
    """Ratings ESG para proveedores."""
    A_PLUS = "A+"
    A = "A"
    B_PLUS = "B+"
    B = "B"
    C = "C"
    D = "D"
    NOT_RATED = "NR"

class Scope3Category(Enum):
    """Categorías de emisiones Scope 3 (GHG Protocol)."""
    PURCHASED_GOODS = "cat1_purchased_goods"
    CAPITAL_GOODS = "cat2_capital_goods"
    FUEL_ENERGY = "cat3_fuel_energy"
    UPSTREAM_TRANSPORT = "cat4_upstream_transport"
    WASTE = "cat5_waste"
    BUSINESS_TRAVEL = "cat6_business_travel"
    COMMUTING = "cat7_commuting"
    UPSTREAM_LEASED = "cat8_upstream_leased"
    DOWNSTREAM_TRANSPORT = "cat9_downstream_transport"
    PROCESSING = "cat10_processing"
    USE_OF_PRODUCT = "cat11_use_of_product"
    END_OF_LIFE = "cat12_end_of_life"
    DOWNSTREAM_LEASED = "cat13_downstream_leased"
    FRANCHISES = "cat14_franchises"
    INVESTMENTS = "cat15_investments"

@dataclass
class Supplier:
    """Proveedor en la cadena de suministro."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    rut: str = ""
    country: str = "CL"
    industry: str = ""
    
    # ESG Metrics
    esg_rating: ESGRating = ESGRating.NOT_RATED
    environmental_score: float = 0.0
    social_score: float = 0.0
    governance_score: float = 0.0
    
    # Carbon footprint
    scope1_emissions: float = 0.0  # tCO2e
    scope2_emissions: float = 0.0
    scope3_emissions: float = 0.0
    
    # Financial
    credit_limit: Decimal = Decimal("0")
    outstanding_invoices: Decimal = Decimal("0")
    payment_terms_days: int = 30
    
    # Risk
    financial_risk_score: float = 0.0
    esg_risk_score: float = 0.0
    combined_risk_score: float = 0.0

@dataclass
class Invoice:
    """Factura para financiamiento de cadena."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    supplier_id: str = ""
    buyer_id: str = ""
    amount: Decimal = Decimal("0")
    currency: str = "CLP"
    issue_date: datetime = field(default_factory=datetime.now)
    due_date: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=30))
    
    # Financing
    is_financed: bool = False
    discount_rate: float = 0.0
    financed_amount: Decimal = Decimal("0")
    esg_adjusted_rate: float = 0.0

class SupplyChainFinanceESG:
    """Sistema de Supply Chain Finance con integración ESG."""
    
    # Ajustes de tasa por rating ESG
    ESG_RATE_ADJUSTMENTS = {
        ESGRating.A_PLUS: -0.50,  # 50 bps descuento
        ESGRating.A: -0.30,
        ESGRating.B_PLUS: -0.15,
        ESGRating.B: 0.0,
        ESGRating.C: 0.25,
        ESGRating.D: 0.50,
        ESGRating.NOT_RATED: 0.10
    }
    
    def __init__(self):
        self._suppliers: Dict[str, Supplier] = {}
        self._invoices: Dict[str, Invoice] = {}
        
    def registrar_proveedor(self, supplier: Supplier) -> str:
        """Registra un proveedor."""
        self._suppliers[supplier.id] = supplier
        return supplier.id
    
    def evaluar_esg_proveedor(
        self,
        supplier_id: str,
        environmental_data: Dict[str, Any],
        social_data: Dict[str, Any],
        governance_data: Dict[str, Any]
    ) -> Supplier:
        """Evalúa métricas ESG de un proveedor."""
        
        supplier = self._suppliers.get(supplier_id)
        if not supplier:
            raise ValueError("Proveedor no encontrado")
        
        # Calcular scores (0-100)
        supplier.environmental_score = self._calcular_score_ambiental(environmental_data)
        supplier.social_score = self._calcular_score_social(social_data)
        supplier.governance_score = self._calcular_score_gobernanza(governance_data)
        
        # ESG Rating basado en promedio ponderado
        esg_score = (
            supplier.environmental_score * 0.40 +
            supplier.social_score * 0.30 +
            supplier.governance_score * 0.30
        )
        
        supplier.esg_rating = self._score_to_rating(esg_score)
        supplier.esg_risk_score = 100 - esg_score
        
        return supplier
    
    def calcular_scope3_emissions(
        self,
        purchases: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calcula emisiones Scope 3 de la cadena de suministro."""
        
        emissions_by_category = {}
        total_emissions = 0.0
        
        for purchase in purchases:
            supplier_id = purchase.get("supplier_id")
            amount = float(purchase.get("amount", 0))
            category = purchase.get("category", Scope3Category.PURCHASED_GOODS)
            
            supplier = self._suppliers.get(supplier_id)
            if not supplier:
                continue
            
            # Intensidad de carbono por unidad monetaria (simplificado)
            carbon_intensity = self._obtener_intensidad_carbono(supplier.industry)
            emissions = amount * carbon_intensity
            
            cat_key = category.value if isinstance(category, Scope3Category) else category
            emissions_by_category[cat_key] = emissions_by_category.get(cat_key, 0) + emissions
            total_emissions += emissions
        
        return {
            "total_scope3_tco2e": round(total_emissions, 2),
            "by_category": emissions_by_category
        }
    
    def financiar_factura(
        self,
        invoice: Invoice,
        base_rate: float = 0.08  # 8% anual base
    ) -> Dict[str, Any]:
        """Financia una factura con ajuste ESG en la tasa."""
        
        supplier = self._suppliers.get(invoice.supplier_id)
        if not supplier:
            return {"error": "Proveedor no encontrado"}
        
        # Ajuste ESG a la tasa
        esg_adjustment = self.ESG_RATE_ADJUSTMENTS.get(supplier.esg_rating, 0)
        adjusted_rate = base_rate + (esg_adjustment / 100)  # Convertir bps a %
        
        # Calcular días hasta vencimiento
        days_to_maturity = (invoice.due_date - datetime.now()).days
        if days_to_maturity <= 0:
            return {"error": "Factura vencida"}
        
        # Calcular descuento
        discount_factor = adjusted_rate * (days_to_maturity / 365)
        discount_amount = invoice.amount * Decimal(str(discount_factor))
        financed_amount = invoice.amount - discount_amount
        
        # Actualizar factura
        invoice.is_financed = True
        invoice.discount_rate = adjusted_rate
        invoice.esg_adjusted_rate = adjusted_rate
        invoice.financed_amount = financed_amount
        
        self._invoices[invoice.id] = invoice
        
        return {
            "invoice_id": invoice.id,
            "original_amount": float(invoice.amount),
            "financed_amount": float(financed_amount),
            "discount": float(discount_amount),
            "base_rate": base_rate,
            "esg_adjustment_bps": esg_adjustment * 100,
            "final_rate": adjusted_rate,
            "supplier_esg_rating": supplier.esg_rating.value,
            "days_to_maturity": days_to_maturity
        }
    
    def _calcular_score_ambiental(self, data: Dict[str, Any]) -> float:
        """Calcula score ambiental."""
        score = 50.0  # Base
        
        if data.get("has_iso14001", False):
            score += 15
        if data.get("renewable_energy_pct", 0) > 50:
            score += 20
        if data.get("carbon_neutral", False):
            score += 15
            
        return min(score, 100)
    
    def _calcular_score_social(self, data: Dict[str, Any]) -> float:
        """Calcula score social."""
        score = 50.0
        
        if data.get("has_iso45001", False):
            score += 15
        if data.get("diversity_index", 0) > 0.4:
            score += 15
        if data.get("fair_wage_certified", False):
            score += 20
            
        return min(score, 100)
    
    def _calcular_score_gobernanza(self, data: Dict[str, Any]) -> float:
        """Calcula score de gobernanza."""
        score = 50.0
        
        if data.get("independent_board_pct", 0) > 0.5:
            score += 15
        if data.get("anti_corruption_policy", False):
            score += 15
        if data.get("whistleblower_protection", False):
            score += 20
            
        return min(score, 100)
    
    def _score_to_rating(self, score: float) -> ESGRating:
        """Convierte score a rating."""
        if score >= 90:
            return ESGRating.A_PLUS
        elif score >= 80:
            return ESGRating.A
        elif score >= 70:
            return ESGRating.B_PLUS
        elif score >= 60:
            return ESGRating.B
        elif score >= 40:
            return ESGRating.C
        else:
            return ESGRating.D
    
    def _obtener_intensidad_carbono(self, industry: str) -> float:
        """Obtiene intensidad de carbono por industria (tCO2e/MUSD)."""
        # Simplificado - en producción usar datos EPA, GHG Protocol
        intensities = {
            "construccion": 0.45,
            "manufactura": 0.55,
            "servicios": 0.15,
            "transporte": 0.70,
            "energia": 0.85,
            "tecnologia": 0.12
        }
        return intensities.get(industry.lower(), 0.30)


# ==============================================================================
# INTEGRADOR DE MÓDULOS FINTECH
# ==============================================================================

class FinTechModulesIntegrator:
    """Integra todos los módulos FinTech adicionales."""
    
    def __init__(self):
        self.tnfd_analyzer = TNFDAnalyzer()
        self.basel_calculator = BaselIVCalculator()
        self.scf_esg = SupplyChainFinanceESG()
    
    def evaluar_activo_completo(
        self,
        asset_id: str,
        asset_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluación completa de un activo con todos los módulos."""
        
        resultado = {
            "asset_id": asset_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # 1. Evaluación TNFD (si tiene ubicación)
        if "latitude" in asset_data and "longitude" in asset_data:
            tnfd_assessment = self.tnfd_analyzer.assess_risks(
                asset_id=asset_id,
                asset_type=TNFDAssetClass.REAL_ESTATE,
                lat=asset_data["latitude"],
                lon=asset_data["longitude"]
            )
            resultado["tnfd"] = self.tnfd_analyzer.prepare_disclosure(tnfd_assessment.id)
        
        # 2. Cálculo Basel IV (si es exposición crediticia)
        if "exposure_amount" in asset_data:
            exposure = BaselIVExposure(
                counterparty_id=asset_id,
                asset_class=AssetClass[asset_data.get("asset_class", "CORPORATE")],
                rating=RatingCategory[asset_data.get("rating", "UNRATED")],
                exposure_gross=Decimal(str(asset_data["exposure_amount"])),
                ltv_ratio=asset_data.get("ltv", 0)
            )
            self.basel_calculator.agregar_exposicion(exposure)
            self.basel_calculator.calcular_rwa(exposure)
            
            resultado["basel_iv"] = {
                "exposure_net": float(exposure.exposure_net),
                "risk_weight": exposure.risk_weight,
                "rwa": float(exposure.rwa)
            }
        
        return resultado


# ==============================================================================
# DEMO
# ==============================================================================

def demo_fintech_modules():
    """Demuestra los módulos FinTech adicionales."""
    
    print("=" * 80)
    print("DEMO: MÓDULOS FINTECH ADICIONALES - DATAPOLIS")
    print("=" * 80)
    
    integrator = FinTechModulesIntegrator()
    
    # 1. Demo TNFD
    print("\n--- M02: TNFD NATURE RISK ---")
    tnfd_result = integrator.tnfd_analyzer.assess_risks(
        asset_id="PROP001",
        asset_type=TNFDAssetClass.REAL_ESTATE,
        lat=-33.4489,  # Santiago
        lon=-70.6693
    )
    print(f"✓ Assessment TNFD creado: {tnfd_result.id[:8]}...")
    print(f"  Riesgo total: {tnfd_result.overall_nature_risk:.1f}/100")
    
    # 2. Demo Basel IV
    print("\n--- M04: BASEL IV CAPITAL ---")
    exposure = BaselIVExposure(
        counterparty_id="CORP001",
        counterparty_name="Empresa ABC",
        asset_class=AssetClass.CORPORATE,
        rating=RatingCategory.BBB,
        exposure_gross=Decimal("100000000")  # 100M
    )
    integrator.basel_calculator.agregar_exposicion(exposure)
    integrator.basel_calculator.calcular_rwa(exposure)
    print(f"✓ Exposición calculada")
    print(f"  RW: {exposure.risk_weight*100:.0f}%")
    print(f"  RWA: ${float(exposure.rwa):,.0f}")
    
    # 3. Demo SCF ESG
    print("\n--- M05: SUPPLY CHAIN FINANCE ESG ---")
    supplier = Supplier(
        name="Proveedor Verde SpA",
        rut="76.123.456-7",
        industry="construccion"
    )
    integrator.scf_esg.registrar_proveedor(supplier)
    integrator.scf_esg.evaluar_esg_proveedor(
        supplier.id,
        environmental_data={"has_iso14001": True, "renewable_energy_pct": 60},
        social_data={"has_iso45001": True, "diversity_index": 0.45},
        governance_data={"independent_board_pct": 0.6, "anti_corruption_policy": True}
    )
    print(f"✓ Proveedor evaluado: {supplier.esg_rating.value}")
    
    invoice = Invoice(
        supplier_id=supplier.id,
        buyer_id="DATAPOLIS",
        amount=Decimal("50000000"),
        due_date=datetime.now() + timedelta(days=60)
    )
    financing = integrator.scf_esg.financiar_factura(invoice)
    print(f"✓ Factura financiada:")
    print(f"  Tasa ajustada ESG: {financing['final_rate']*100:.2f}%")
    print(f"  Monto financiado: ${financing['financed_amount']:,.0f}")
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETADA - MÓDULOS FINTECH OPERATIVOS")
    print("=" * 80)


if __name__ == "__main__":
    demo_fintech_modules()

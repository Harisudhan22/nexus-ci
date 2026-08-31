from app.services.adapters.base import BaseSourceAdapter, CommonInternalRecord
from app.services.adapters.cctns import MockCCTNSAdapter
from app.services.adapters.cdr import MockCDRAdapter
from app.services.adapters.financial import MockFinancialAdapter
from app.services.adapters.surveillance import MockSurveillanceAdapter
from app.services.adapters.criminal_history import MockCriminalHistoryAdapter
from app.services.adapters.intelligence import MockIntelligenceAdapter
from app.services.adapters.social import MockSocialIntelligenceAdapter
from app.services.adapters.vehicles import MockVehicleAdapter

ADAPTERS = {
    "cctns": MockCCTNSAdapter(),
    "cdr": MockCDRAdapter(),
    "financial": MockFinancialAdapter(),
    "surveillance": MockSurveillanceAdapter(),
    "criminal_history": MockCriminalHistoryAdapter(),
    "intelligence": MockIntelligenceAdapter(),
    "social": MockSocialIntelligenceAdapter(),
    "vehicles": MockVehicleAdapter(),
}

def get_adapter(name: str) -> BaseSourceAdapter:
    return ADAPTERS.get(name.lower(), ADAPTERS["cctns"])

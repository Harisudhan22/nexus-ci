import json
import datetime
from typing import Dict, Any, Optional
from app.services.adapters.base import BaseSourceAdapter, CommonInternalRecord

class MockCCTNSAdapter(BaseSourceAdapter):
    adapter_name: str = "mock_cctns"
    source_category: str = "FIR_POLICE_REPORTS"

    def normalize(self, raw_input: Dict[str, Any], case_id: Optional[str] = None) -> CommonInternalRecord:
        fir_no = raw_input.get("fir_number") or raw_input.get("fir_no") or f"FIR-{raw_input.get('id', 'UNKNOWN')}"
        ps = raw_input.get("police_station") or raw_input.get("ps", "Central Station")
        dt_str = raw_input.get("incident_date") or raw_input.get("date") or datetime.datetime.utcnow().isoformat()
        desc = raw_input.get("complaint_text") or raw_input.get("description") or raw_input.get("extracted_text") or ""
        suspects = raw_input.get("suspects", [])
        
        entities = []
        for s in suspects:
            if isinstance(s, dict):
                name = s.get("name")
                if name:
                    entities.append({"type": "person", "surface": name, "role": s.get("role", "suspect")})
                if s.get("phone"):
                    entities.append({"type": "phone", "surface": s.get("phone")})
                if s.get("vehicle"):
                    entities.append({"type": "vehicle", "surface": s.get("vehicle")})
            elif isinstance(s, str):
                entities.append({"type": "person", "surface": s, "role": "suspect"})

        raw_str = json.dumps(raw_input, default=str)
        sha = self.compute_sha256(raw_str)

        return CommonInternalRecord(
            source_adapter=self.adapter_name,
            source_record_id=fir_no,
            record_type="FIR",
            case_id=case_id or raw_input.get("case_id"),
            timestamp=datetime.datetime.utcnow(),
            sha256=sha,
            payload=raw_input,
            raw_text=f"First Information Report {fir_no} lodged at {ps}. Details: {desc}",
            extracted_entities=entities
        )

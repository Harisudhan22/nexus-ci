import json
import datetime
from typing import Dict, Any, Optional
from app.services.adapters.base import BaseSourceAdapter, CommonInternalRecord

class MockCDRAdapter(BaseSourceAdapter):
    adapter_name: str = "mock_cdr"
    source_category: str = "CDR"

    def normalize(self, raw_input: Dict[str, Any], case_id: Optional[str] = None) -> CommonInternalRecord:
        record_id = raw_input.get("call_id") or raw_input.get("id") or f"CDR-{datetime.datetime.utcnow().timestamp()}"
        caller = str(raw_input.get("caller") or raw_input.get("caller_msisdn") or "").strip()
        callee = str(raw_input.get("callee") or raw_input.get("callee_msisdn") or "").strip()
        duration = int(raw_input.get("duration", 0))
        tower = str(raw_input.get("cell_tower") or raw_input.get("location") or "Chennai Tower")
        ts_str = str(raw_input.get("timestamp") or datetime.datetime.utcnow().isoformat())

        entities = []
        if caller:
            entities.append({"type": "phone", "surface": caller, "role": "caller"})
        if callee:
            entities.append({"type": "phone", "surface": callee, "role": "callee"})
        if tower:
            entities.append({"type": "location", "surface": tower, "role": "cell_site"})

        rels = []
        if caller and callee:
            rels.append({
                "source": caller,
                "source_type": "phone",
                "target": callee,
                "target_type": "phone",
                "rel_type": "CALLS",
                "properties": {
                    "duration": duration,
                    "timestamp": ts_str,
                    "confidence": 95,
                    "suspicious": duration > 300
                }
            })

        raw_str = json.dumps(raw_input, default=str)
        sha = self.compute_sha256(raw_str)

        return CommonInternalRecord(
            source_adapter=self.adapter_name,
            source_record_id=str(record_id),
            record_type="CDR",
            case_id=case_id or raw_input.get("case_id"),
            timestamp=datetime.datetime.utcnow(),
            sha256=sha,
            payload=raw_input,
            raw_text=f"Call Detail Record: {caller} called {callee} for {duration} seconds at tower {tower} on {ts_str}.",
            extracted_entities=entities,
            extracted_relationships=rels
        )

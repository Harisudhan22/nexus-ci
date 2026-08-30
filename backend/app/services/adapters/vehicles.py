import json
import datetime
from typing import Dict, Any, Optional
from app.services.adapters.base import BaseSourceAdapter, CommonInternalRecord

class MockVehicleAdapter(BaseSourceAdapter):
    adapter_name: str = "mock_vehicles"
    source_category: str = "VEHICLE_RECORDS"

    def normalize(self, raw_input: Dict[str, Any], case_id: Optional[str] = None) -> CommonInternalRecord:
        reg_id = raw_input.get("plate_number") or raw_input.get("registration_no") or raw_input.get("id") or f"VEH-{datetime.datetime.utcnow().timestamp()}"
        owner = str(raw_input.get("owner_name") or raw_input.get("owner") or "").strip()
        model = str(raw_input.get("model") or "Sedan")
        color = str(raw_input.get("color") or "White")
        state = str(raw_input.get("state") or "Tamil Nadu")

        entities = []
        if reg_id:
            entities.append({"type": "vehicle", "surface": str(reg_id), "model": model, "color": color})
        if owner:
            entities.append({"type": "person", "surface": owner})

        rels = []
        if owner and reg_id:
            rels.append({
                "source": owner,
                "source_type": "person",
                "target": str(reg_id),
                "target_type": "vehicle",
                "rel_type": "OWNS",
                "properties": {
                    "confidence": 95,
                    "rationale": f"RTO registration record links vehicle {reg_id} to owner {owner}."
                }
            })

        raw_str = json.dumps(raw_input, default=str)
        sha = self.compute_sha256(raw_str)

        return CommonInternalRecord(
            source_adapter=self.adapter_name,
            source_record_id=str(reg_id),
            record_type="VEHICLE_RECORD",
            case_id=case_id or raw_input.get("case_id"),
            timestamp=datetime.datetime.utcnow(),
            sha256=sha,
            payload=raw_input,
            raw_text=f"RTO Vehicle Record: Plate {reg_id}, Model {model} ({color}), Registered Owner: {owner}, State: {state}.",
            extracted_entities=entities,
            extracted_relationships=rels
        )

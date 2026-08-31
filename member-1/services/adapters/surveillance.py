import json
import datetime
from typing import Dict, Any, Optional
from app.services.adapters.base import BaseSourceAdapter, CommonInternalRecord

class MockSurveillanceAdapter(BaseSourceAdapter):
    adapter_name: str = "mock_surveillance"
    source_category: str = "SURVEILLANCE"

    def normalize(self, raw_input: Dict[str, Any], case_id: Optional[str] = None) -> CommonInternalRecord:
        log_id = raw_input.get("log_id") or raw_input.get("sighting_id") or f"SRV-{datetime.datetime.utcnow().timestamp()}"
        location = str(raw_input.get("location") or raw_input.get("camera_location") or "Central Junction")
        subject = str(raw_input.get("subject_name") or raw_input.get("person") or "").strip()
        vehicle = str(raw_input.get("vehicle_plate") or raw_input.get("vehicle") or "").strip()
        desc = str(raw_input.get("notes") or raw_input.get("description") or "Visual observation logged.")
        ts_str = str(raw_input.get("timestamp") or datetime.datetime.utcnow().isoformat())

        entities = []
        if subject:
            entities.append({"type": "person", "surface": subject})
        if vehicle:
            entities.append({"type": "vehicle", "surface": vehicle})
        if location:
            entities.append({"type": "location", "surface": location})

        rels = []
        if subject and location:
            rels.append({
                "source": subject,
                "source_type": "person",
                "target": location,
                "target_type": "location",
                "rel_type": "SEEN_AT",
                "properties": {
                    "timestamp": ts_str,
                    "confidence": 85,
                    "suspicious": True
                }
            })
        if vehicle and location:
            rels.append({
                "source": vehicle,
                "source_type": "vehicle",
                "target": location,
                "target_type": "location",
                "rel_type": "SEEN_AT",
                "properties": {
                    "timestamp": ts_str,
                    "confidence": 90,
                    "suspicious": False
                }
            })

        raw_str = json.dumps(raw_input, default=str)
        sha = self.compute_sha256(raw_str)

        return CommonInternalRecord(
            source_adapter=self.adapter_name,
            source_record_id=str(log_id),
            record_type="SURVEILLANCE",
            case_id=case_id or raw_input.get("case_id"),
            timestamp=datetime.datetime.utcnow(),
            sha256=sha,
            payload=raw_input,
            raw_text=f"Surveillance report {log_id}: Sighting of {subject or 'unidentified subject'} with vehicle {vehicle or 'N/A'} at {location}. Notes: {desc}",
            extracted_entities=entities,
            extracted_relationships=rels
        )

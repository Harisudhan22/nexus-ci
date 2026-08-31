import json
import datetime
from typing import Dict, Any, Optional
from app.services.adapters.base import BaseSourceAdapter, CommonInternalRecord

class MockCriminalHistoryAdapter(BaseSourceAdapter):
    adapter_name: str = "mock_criminal_history"
    source_category: str = "CRIMINAL_HISTORY"

    def normalize(self, raw_input: Dict[str, Any], case_id: Optional[str] = None) -> CommonInternalRecord:
        dossier_id = raw_input.get("dossier_id") or raw_input.get("id") or f"DOSSIER-{datetime.datetime.utcnow().timestamp()}"
        name = str(raw_input.get("name") or "").strip()
        aliases = raw_input.get("aliases", [])
        charges = raw_input.get("prior_charges", [])
        associated_orgs = raw_input.get("organizations", [])
        phone = raw_input.get("known_phone")
        vehicle = raw_input.get("known_vehicle")

        entities = []
        if name:
            entities.append({"type": "person", "surface": name, "aliases": aliases})
        for a in aliases:
            entities.append({"type": "person", "surface": a, "is_alias": True})
        for org in associated_orgs:
            entities.append({"type": "org", "surface": org})
        if phone:
            entities.append({"type": "phone", "surface": phone})
        if vehicle:
            entities.append({"type": "vehicle", "surface": vehicle})

        rels = []
        for org in associated_orgs:
            if name:
                rels.append({
                    "source": name,
                    "source_type": "person",
                    "target": org,
                    "target_type": "org",
                    "rel_type": "WORKS_FOR",
                    "properties": {
                        "confidence": 85,
                        "rationale": "Historical criminal intelligence dossier record."
                    }
                })
        if name and phone:
            rels.append({
                "source": name,
                "source_type": "person",
                "target": phone,
                "target_type": "phone",
                "rel_type": "OWNS",
                "properties": {"confidence": 90, "rationale": "Registered phone number in criminal history dossier."}
            })
        if name and vehicle:
            rels.append({
                "source": name,
                "source_type": "person",
                "target": vehicle,
                "target_type": "vehicle",
                "rel_type": "OWNS",
                "properties": {"confidence": 90, "rationale": "Registered vehicle in dossier."}
            })

        raw_str = json.dumps(raw_input, default=str)
        sha = self.compute_sha256(raw_str)

        charges_str = ", ".join(charges) if charges else "None recorded"
        return CommonInternalRecord(
            source_adapter=self.adapter_name,
            source_record_id=str(dossier_id),
            record_type="DOSSIER",
            case_id=case_id or raw_input.get("case_id"),
            timestamp=datetime.datetime.utcnow(),
            sha256=sha,
            payload=raw_input,
            raw_text=f"Criminal History Dossier {dossier_id}: Target {name} (Aliases: {', '.join(aliases)}). Known charges: {charges_str}. Phone: {phone}. Vehicle: {vehicle}.",
            extracted_entities=entities,
            extracted_relationships=rels
        )

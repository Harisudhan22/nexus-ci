import json
import datetime
from typing import Dict, Any, Optional
from app.services.adapters.base import BaseSourceAdapter, CommonInternalRecord

class MockSocialIntelligenceAdapter(BaseSourceAdapter):
    adapter_name: str = "mock_social"
    source_category: str = "SOCIAL_MEDIA_OSINT"

    def normalize(self, raw_input: Dict[str, Any], case_id: Optional[str] = None) -> CommonInternalRecord:
        post_id = raw_input.get("post_id") or raw_input.get("id") or f"SOC-{datetime.datetime.utcnow().timestamp()}"
        handle = str(raw_input.get("handle") or raw_input.get("username") or "").strip()
        platform = str(raw_input.get("platform") or "Telegram")
        content = str(raw_input.get("content") or raw_input.get("text") or "")
        linked_person = str(raw_input.get("linked_person") or "").strip()

        entities = []
        if handle:
            entities.append({"type": "account", "surface": handle, "platform": platform})
        if linked_person:
            entities.append({"type": "person", "surface": linked_person})

        rels = []
        if linked_person and handle:
            rels.append({
                "source": linked_person,
                "source_type": "person",
                "target": handle,
                "target_type": "account",
                "rel_type": "USES",
                "properties": {
                    "confidence": 80,
                    "rationale": f"OSINT link between individual and {platform} handle {handle}."
                }
            })

        raw_str = json.dumps(raw_input, default=str)
        sha = self.compute_sha256(raw_str)

        return CommonInternalRecord(
            source_adapter=self.adapter_name,
            source_record_id=str(post_id),
            record_type="SOCIAL_INTEL",
            case_id=case_id or raw_input.get("case_id"),
            timestamp=datetime.datetime.utcnow(),
            sha256=sha,
            payload=raw_input,
            raw_text=f"Social Intelligence ({platform}) from {handle}: {content}",
            extracted_entities=entities,
            extracted_relationships=rels
        )

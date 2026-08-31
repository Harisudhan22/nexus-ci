import json
import datetime
from typing import Dict, Any, Optional
from app.services.adapters.base import BaseSourceAdapter, CommonInternalRecord

class MockIntelligenceAdapter(BaseSourceAdapter):
    adapter_name: str = "mock_intelligence"
    source_category: str = "INTELLIGENCE_REPORTS"

    def normalize(self, raw_input: Dict[str, Any], case_id: Optional[str] = None) -> CommonInternalRecord:
        report_id = raw_input.get("report_id") or raw_input.get("id") or f"INTEL-{datetime.datetime.utcnow().timestamp()}"
        title = raw_input.get("title", "Special Branch Intelligence Report")
        body = raw_input.get("content") or raw_input.get("summary") or ""
        entities_list = raw_input.get("named_entities", [])
        
        entities = []
        for e in entities_list:
            if isinstance(e, dict):
                entities.append({"type": e.get("type", "person"), "surface": e.get("name") or e.get("label")})
            elif isinstance(e, str):
                entities.append({"type": "person", "surface": e})

        raw_str = json.dumps(raw_input, default=str)
        sha = self.compute_sha256(raw_str)

        return CommonInternalRecord(
            source_adapter=self.adapter_name,
            source_record_id=str(report_id),
            record_type="INTEL_REPORT",
            case_id=case_id or raw_input.get("case_id"),
            timestamp=datetime.datetime.utcnow(),
            sha256=sha,
            payload=raw_input,
            raw_text=f"Intelligence Report {report_id} - {title}: {body}",
            extracted_entities=entities
        )

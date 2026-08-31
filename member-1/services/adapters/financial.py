import json
import datetime
from typing import Dict, Any, Optional
from app.services.adapters.base import BaseSourceAdapter, CommonInternalRecord

class MockFinancialAdapter(BaseSourceAdapter):
    adapter_name: str = "mock_financial"
    source_category: str = "FINANCIAL_TRANSACTIONS"

    def normalize(self, raw_input: Dict[str, Any], case_id: Optional[str] = None) -> CommonInternalRecord:
        tx_id = raw_input.get("tx_id") or raw_input.get("transaction_id") or f"TX-{datetime.datetime.utcnow().timestamp()}"
        sender_acc = str(raw_input.get("sender_account") or raw_input.get("sender") or "").strip()
        receiver_acc = str(raw_input.get("receiver_account") or raw_input.get("receiver") or "").strip()
        amount = float(raw_input.get("amount", 0.0))
        currency = raw_input.get("currency", "INR")
        bank = raw_input.get("bank", "SBI")
        ts_str = str(raw_input.get("timestamp") or datetime.datetime.utcnow().isoformat())

        entities = []
        if sender_acc:
            entities.append({"type": "account", "surface": sender_acc, "bank": bank})
        if receiver_acc:
            entities.append({"type": "account", "surface": receiver_acc, "bank": bank})

        rels = []
        if sender_acc and receiver_acc:
            rels.append({
                "source": sender_acc,
                "source_type": "account",
                "target": receiver_acc,
                "target_type": "account",
                "rel_type": "TRANSFERS",
                "properties": {
                    "amount": amount,
                    "currency": currency,
                    "timestamp": ts_str,
                    "confidence": 100,
                    "suspicious": amount >= 100000
                }
            })

        raw_str = json.dumps(raw_input, default=str)
        sha = self.compute_sha256(raw_str)

        return CommonInternalRecord(
            source_adapter=self.adapter_name,
            source_record_id=str(tx_id),
            record_type="TRANSACTION",
            case_id=case_id or raw_input.get("case_id"),
            timestamp=datetime.datetime.utcnow(),
            sha256=sha,
            payload=raw_input,
            raw_text=f"Financial transaction {tx_id}: Transfer of {currency} {amount} from account {sender_acc} to account {receiver_acc} at {bank}.",
            extracted_entities=entities,
            extracted_relationships=rels
        )

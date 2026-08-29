import re
import spacy
from typing import List, Dict, Any, Tuple

# Precompile regular expressions for deterministic entities
PHONE_REGEX = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
# Indian plates or generic vehicle plates, e.g. TN01AB1234, DL 3C AB 1234
VEHICLE_REGEX = re.compile(r"\b[A-Z]{2}\s?[0-9]{2}\s?[A-Z]{1,2}\s?[0-9]{4}\b", re.IGNORECASE)
# Account numbers, e.g. Account A101, ACC-101, 10-12 digit numbers
ACCOUNT_REGEX = re.compile(r"\b(?:Account\s+)?(?:ACC-)?([A-Z]\d{3,6}|\d{8,12})\b", re.IGNORECASE)
# Case IDs
CASE_ID_REGEX = re.compile(r"\bCASE-\d{3,5}\b", re.IGNORECASE)

class EntityExtractor:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except Exception:
            print("spaCy model 'en_core_web_sm' not found. Using regex and rule-based fallback.")
            self.nlp = None

    def extract(self, text: str, case_id: str, doc_id: str) -> List[Dict[str, Any]]:
        """
        Extracts mentions of entities from text.
        Each extracted mention has: surface, type, document ID, case ID.
        """
        mentions = []
        if not text:
            return mentions

        # 1. Regex Extraction
        # Phones
        for match in PHONE_REGEX.finditer(text):
            val = match.group().strip()
            mentions.append({
                "surface": val,
                "type": "phone",
                "evidence_id": doc_id,
                "case_id": case_id
            })

        # Vehicles
        for match in VEHICLE_REGEX.finditer(text):
            val = match.group().strip().upper()
            mentions.append({
                "surface": val,
                "type": "vehicle",
                "evidence_id": doc_id,
                "case_id": case_id
            })

        # Accounts
        for match in ACCOUNT_REGEX.finditer(text):
            val = match.group().strip()
            # Clean up prefix if any
            clean_val = val.replace("Account", "").replace("account", "").strip()
            mentions.append({
                "surface": clean_val,
                "type": "account",
                "evidence_id": doc_id,
                "case_id": case_id
            })

        # Cases
        for match in CASE_ID_REGEX.finditer(text):
            val = match.group().strip().upper()
            mentions.append({
                "surface": val,
                "type": "case",
                "evidence_id": doc_id,
                "case_id": case_id
            })

        # 2. spaCy Named Entity Recognition (NER)
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                ent_type = None
                if ent.label_ == "PERSON":
                    ent_type = "person"
                elif ent.label_ in ["GPE", "LOC"]:
                    ent_type = "location"
                elif ent.label_ in ["ORG"]:
                    ent_type = "org"
                elif ent.label_ in ["DATE", "TIME"]:
                    ent_type = "event"

                if ent_type:
                    surface_clean = ent.text.strip()
                    # Filter out short or noisy extractions
                    if len(surface_clean) > 2:
                        mentions.append({
                            "surface": surface_clean,
                            "type": ent_type,
                            "evidence_id": doc_id,
                            "case_id": case_id
                        })
        else:
            # Fallback Capitalized Name Extraction for Person/Location/Organization
            # Find capitalized words that aren't starting a sentence
            words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
            for word in words:
                if len(word) > 2 and word.lower() not in ["the", "this", "case", "station", "police", "report", "evidence"]:
                    # Default fallback type is person or org depending on length/words
                    ent_type = "org" if "bank" in word.lower() or "inc" in word.lower() or "co" in word.lower() else "person"
                    mentions.append({
                        "surface": word,
                        "type": ent_type,
                        "evidence_id": doc_id,
                        "case_id": case_id
                    })

        # Remove exact duplicates of same entity in the same document
        unique_mentions = []
        seen = set()
        for m in mentions:
            key = (m["surface"].lower(), m["type"])
            if key not in seen:
                seen.add(key)
                unique_mentions.append(m)

        return unique_mentions

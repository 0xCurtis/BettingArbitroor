import json
import requests
from typing import Dict, List, Tuple

from logger import error_logger

class MarketMatcher:
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3"):
        self.ollama_url = ollama_url
        self.model = model

    def find_matches(self, polymarket_data: List[Dict], kalshi_data: List[Dict]) -> List[Tuple[Dict, Dict, float]]:
        """
        Compare markets and return a list of matches with confidence scores.
        Returns: List of (PolymarketDict, KalshiDict, ConfidenceScore)
        """
        matches = []
        
        # Direct Cross-Product (No Pre-filter)
        total_pairs = len(polymarket_data) * len(kalshi_data)
        print(f"  Checking all {total_pairs} pairs with LLM (Pre-filter bypassed)...")

        count = 0
        for poly in polymarket_data:
            for kalshi in kalshi_data:
                count += 1
                # Simple optimization: Skip empty events
                if not poly.get("event") or not kalshi.get("event"):
                    continue
            
                print(f"Checking Event {count} of {total_pairs}")
                confidence, reason = self._verify_match_with_llm(poly, kalshi)
                
                if confidence > 0.7: # Store anything plausible
                    print(f"  ✅ MATCH FOUND!")
                    print(f"     Poly: {poly.get('url', 'No URL')}")
                    print(f"     Kalshi: {kalshi.get('url', 'No URL')}")
                    print(f"     Confidence: {confidence:.2f}")
                    print(f"     Reason: {reason}")
                    matches.append((poly, kalshi, confidence))
                else:
                    print("")
                    print(f"     Poly: {poly.get('url', 'No URL')}")
                    print(f"     Kalshi: {kalshi.get('url', 'No URL')}")
                    print(f"     Confidence: {confidence:.2f}")
                    print(f"     Reason: {reason}")

        return matches

    def _verify_match_with_llm(self, poly: Dict, kalshi: Dict) -> Tuple[float, str]:
        """
        Ask Ollama if these two markets represent the same event.
        """
        # Construct rich context including descriptions/rules if available
        poly_text = f"Title: {poly['event']}\nDescription: {poly.get('description', 'N/A')}"
        kalshi_text = f"Title: {kalshi['event']}\nRules: {kalshi.get('description', 'N/A')}"

        prompt = f"""
        Compare these two prediction market events. Your goal is to determine if they are the EXACT SAME betting market.
        
        === Market A (Polymarket) ===
        {poly_text}
        
        === Market B (Kalshi) ===
        {kalshi_text}
        
        CRITERIA FOR MATCH:
        1. SAME Event (e.g. same election, same game).
        2. SAME Condition (e.g. both ask if X wins, or if X > 100).
        3. SAME Entities (e.g. Bitcoin vs Bitcoin, not Bitcoin vs Ethereum).
        4. SAME Dates/Numbers (if year is 2024 in A and 2025 in B, it is NOT a match).
        
        IMPORTANT:
        - Ignore phrasing differences (e.g. "Will X happen?" vs "If X happens...").
        - Look for the CORE outcome. If Market A asks "Will X happen?" and Market B says "If X happens, Yes", they are a MATCH.
        
        If they are different in ANY critical way (dates, teams, logic), return "match": false.
        Be skeptical. Most pairs are NOT matches.
        
        Reply ONLY with a JSON object:
        {{
            "reason": "short explanation of why they match or not",
            "match": boolean,
            "confidence": float (0.0 to 1.0)
        }}
        """
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            import json
            content = json.loads(result["response"])
            
            reason = content.get("reason", "No reason provided")
            confidence = float(content.get("confidence", 0.0))
            is_match = content.get("match", False)

            if is_match:
                return confidence, reason
            return 0.0, reason
            
        except Exception as e:
            # Fallback or error logging
            error_logger.log_error(e, context="LLM verification")
            return 0.0, "Error verifying match with LLM"

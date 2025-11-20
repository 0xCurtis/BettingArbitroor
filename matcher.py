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
                    
                confidence = self._verify_match_with_llm(poly, kalshi)
                
                if confidence > 0.7: # Store anything plausible
                    print(f"  ✅ MATCH FOUND!")
                    print(f"     Poly: {poly.get('url', 'No URL')}")
                    print(f"     Kalshi: {kalshi.get('url', 'No URL')}")
                    matches.append((poly, kalshi, confidence))

        return matches

    def _verify_match_with_llm(self, poly: Dict, kalshi: Dict) -> float:
        """
        Ask Ollama if these two markets represent the same event.
        """
        prompt = f"""
        Compare these two prediction market events. Your goal is to determine if they are the EXACT SAME betting market.
        
        Market A (Polymarket): "{poly['event']}"
        Market B (Kalshi): "{kalshi['event']}"
        
        CRITERIA FOR MATCH:
        1. SAME Event (e.g. same election, same game).
        2. SAME Condition (e.g. both ask if X wins, or if X > 100).
        3. SAME Entities (e.g. Bitcoin vs Bitcoin, not Bitcoin vs Ethereum).
        4. SAME Dates/Numbers (if year is 2024 in A and 2025 in B, it is NOT a match).
        
        If they are different in ANY way (dates, teams, logic), return "match": false.
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
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            import json
            content = json.loads(result["response"])
            
            reason = content.get("reason", "No reason provided")
            confidence = float(content.get("confidence", 0.0))
            is_match = content.get("match", False)

            # Always print reasoning for debugging
            p_title_short = poly['event'][:20] + "..."
            k_title_short = kalshi['event'][:20] + "..."
            print(f"  Rx: {p_title_short} vs {k_title_short} | Match: {is_match} ({confidence:.2f}) | {reason[:60]}...")

            if is_match:
                return confidence
            return 0.0
            
        except Exception as e:
            # Fallback or error logging
            error_logger.log_error(e, context="LLM verification")
            return 0.0

from matcher import MarketMatcher

def test_matcher_demo():
    matcher = MarketMatcher()
    
    print("--- Starting LLM Matcher Test (Exact JSON Structure) ---")

    # 1. Fed Rate Hike (Strong Match)
    # Polymarket Structure: 'events' list inside market
    poly1 = {
        "id": "516706",
        "question": "Fed rate hike in 2025?",
        "description": "This market will resolve to “Yes” if the upper bound...",
        "slug": "fed-rate-hike-in-2025",
        "events": [
            {
                "id": "16084",
                "title": "Fed rate hike in 2025?",
                "description": "This market will resolve to “Yes” if...",
                "end_date": "2025-12-10T12:00:00Z"
            }
        ]
    }

    # Kalshi Structure: Flat, generic title + specific rules
    # Note: I'm creating a hypothetical Kalshi entry that SHOULD match Poly1
    kalshi1 = {
        "title": "Fed Rate Hike 2025", 
        "rules_primary": "If the target federal funds rate increases...",
        "ticker": "KXFEDHIKE-25",
        "slug": None
    }

    # 2. The Pope Match (Tricky - "Who" vs "If Person X")
    poly2 = {
        "id": "999999", # Synthetic ID
        "question": "Will Pierbattista Pizzaballa be elected the next Pope?",
        "description": "This market resolves to Yes if Pierbattista Pizzaballa...",
        "slug": "pope-pizzaballa",
        "events": [
            {
                "id": "888888",
                "title": "Will Pierbattista Pizzaballa be elected the next Pope?",
                "description": "Resolves if...",
                "end_date": "2070-01-01T00:00:00Z"
            }
        ]
    }
    
    # Kalshi Structure (Exact copy from your file example)
    kalshi2 = {
        "close_time": "2070-01-01T15:00:00Z",
        "created_time": "2025-07-18T08:05:49.322772Z",
        "early_close_condition": "This market will close and expire early if the event occurs.",
        "rules_primary": "If Pierbattista Pizzaballa becomes the first person elected Pope before Jan 1, 2070, then the market resolves to Yes.",
        "rules_secondary": "",
        "slug": None,
        "title": "Who will the next Pope be?",
        "ticker": "KXNEWPOPE-70-PPIZ"
    }

    # 3. Mismatch: Nuclear vs Warming
    poly3 = {
        "id": "516717",
        "question": "Nuclear weapon detonation in 2025?",
        "description": "This market will resolve to \"Yes\" if a nuclear weapon...",
        "slug": "nuclear-weapon-detonation-in-2025",
        "events": [
            {
                "id": "16106",
                "title": "Nuclear weapon detonation in 2025?",
                "description": "...",
                "end_date": "2025-12-31T12:00:00Z"
            }
        ]
    }
    
    kalshi3 = {
        "close_time": "2050-01-01T04:59:00Z",
        "created_time": "2025-06-05T16:28:27.496599Z",
        "early_close_condition": "This market will close...",
        "rules_primary": "If the annual global mean surface temperature anomaly...",
        "rules_secondary": "At least two of the Source Agencies...",
        "slug": None,
        "title": "Will the world pass 2 degrees Celsius over pre-industrial levels before 2050?",
        "ticker": "KXWARMING-50"
    }
    
    # --- IMPORTANT ---
    # The Matcher expects NORMALIZED dictionaries (event, source, url), 
    # NOT raw JSON blobs.
    # So we must simulate the Scraper's normalization step here.
    
    def normalize_poly(raw):
        if "events" in raw and raw["events"]:
             # Use the specific event title
             title = raw["events"][0]["title"]
        else:
             title = raw["question"]
             
        return {
            "event": title,
            "source": "Polymarket",
            "url": f"https://polymarket.com/event/{raw.get('slug', '')}",
            # Pass description to LLM if matcher supports it (it doesn't yet, but good for future)
            "description": raw.get("description", "") 
        }

    def normalize_kalshi(raw):
        # Simulate a smart scraper: Combine Title + Rule if title is generic
        title = raw.get("title", "")
        rule = raw.get("rules_primary", "")
        
        # Heuristic: If title is generic "Who will be X?", append rule
        if "Who" in title or len(title) < 20:
             combined = f"{title} ({rule})"
        else:
             combined = title
             
        return {
            "event": combined,
            "source": "Kalshi",
            "url": f"https://kalshi.com/markets/{raw.get('ticker', '')}",
            "description": rule
        }

    poly_list = [normalize_poly(poly1), normalize_poly(poly2), normalize_poly(poly3)]
    kalshi_list = [normalize_kalshi(kalshi1), normalize_kalshi(kalshi2), normalize_kalshi(kalshi3)]
    
    matches = matcher.find_matches(poly_list, kalshi_list)
    
    print(f"\n--- Test Complete ---")
    print(f"Total Matches Found: {len(matches)} (Expected 2)")

if __name__ == "__main__":
    test_matcher_demo()

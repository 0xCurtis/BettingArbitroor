import json
import re
import subprocess
from typing import Dict, List, Set, Tuple

import requests
from matcher.retrieval import Retriever

from config import (
    AUTO_ACCEPT_THRESHOLD,
    AUTO_REJECT_THRESHOLD,
    JACCARD_MIN_FOR_AUTO_ACCEPT,
    MIN_SIMILARITY,
    OLLAMA_CLI,
    OLLAMA_MODEL,
    OLLAMA_OPTIONS,
    OLLAMA_URL,
    TOP_K_CANDIDATES,
)
from logger import error_logger


def _normalize_poly_item(raw: Dict) -> Dict:
    title = None
    if isinstance(raw.get("events"), list) and raw["events"]:
        ev0 = raw["events"][0]
        title = ev0.get("title") or raw.get("question")
    else:
        title = raw.get("question") or raw.get("event")

    desc = raw.get("description", "")
    slug = raw.get("slug") or raw.get("url", "").split("/")[-1]
    return {
        "event": title or "",
        "description": desc or "",
        "source": raw.get("source", "Polymarket"),
        "url": f"https://polymarket.com/event/{slug}" if slug else raw.get("url", ""),
    }


def _normalize_kalshi_item(raw: Dict) -> Dict:
    title = raw.get("title", "")
    rule = raw.get("rules_primary", "")
    combined = title
    if ("who will" in title.lower()) or (len(title) < 20):
        combined = f"{title} ({rule})".strip()
    return {
        "event": combined or raw.get("event", ""),
        "description": rule or raw.get("description", ""),
        "source": raw.get("source", "Kalshi"),
        "ticker": raw.get("ticker", ""),
        "url": f"https://kalshi.com/markets/{raw.get('ticker', '')}",
    }


class MarketMatcher:
    def __init__(
        self,
        ollama_url: str = OLLAMA_URL,
        model: str = OLLAMA_MODEL,
        top_k: int = TOP_K_CANDIDATES,
        min_similarity: float = MIN_SIMILARITY,
        use_vector_retrieval: bool = True,
        greedy: bool = True,
    ):
        self.ollama_url = ollama_url
        self.model = model
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.use_vector_retrieval = use_vector_retrieval
        self.greedy = greedy
        self.llm_enabled = True
        self._llm_error_count = 0
        self._llm_error_limit = 3
        self._last_llm_failed = False
        self.auto_accept_threshold = AUTO_ACCEPT_THRESHOLD
        self.auto_reject_threshold = AUTO_REJECT_THRESHOLD
        self.jaccard_min_for_auto_accept = JACCARD_MIN_FOR_AUTO_ACCEPT
        self.ALIAS_MAP = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "sol": "solana",
            "rep": "republican",
            "dem": "democrat",
            "gop": "republican",
            "dems": "democrat",
            "fed": "federal",
            "rate": "rates",
        }

    def _normalize_inputs(
        self, polymarket_data: List[Dict], kalshi_data: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        def is_normalized(it: Dict) -> bool:
            return "event" in it

        poly_norm = [
            _normalize_poly_item(it) if not is_normalized(it) else it for it in polymarket_data
        ]
        kalshi_norm = [
            _normalize_kalshi_item(it) if not is_normalized(it) else it for it in kalshi_data
        ]
        return poly_norm, kalshi_norm

    def find_matches(
        self, polymarket_data: List[Dict], kalshi_data: List[Dict]
    ) -> List[Tuple[Dict, Dict, float]]:
        """
        Retrieval + Greedy LLM verification pipeline.
        Returns: List of (PolyDict, KalshiDict, LLM_Confidence)
        """
        poly_list, kalshi_list = self._normalize_inputs(polymarket_data, kalshi_data)

        if not poly_list or not kalshi_list:
            return []

        retriever = Retriever(top_k=self.top_k)
        retriever.index(kalshi_list)

        retrieval = retriever.search(poly_list, k=self.top_k)

        candidates: List[Tuple[float, int, int]] = []
        for p_idx in range(len(poly_list)):
            for rank in range(self.top_k):
                score = retrieval.distances[p_idx][rank]
                k_idx = retrieval.indices[p_idx][rank]
                if k_idx == -1:
                    continue
                candidates.append((float(score), p_idx, int(k_idx)))

        candidates.sort(key=lambda x: x[0], reverse=True)

        seen_poly: set[int] = set[int]()
        seen_kalshi: set[int] = set[int]()
        matches: List[Tuple[Dict, Dict, float]] = []

        saved_calls = 0
        for score, p_idx, k_idx in candidates:
            if p_idx in seen_poly or k_idx in seen_kalshi:
                saved_calls += 1
                continue

            if score < self.auto_reject_threshold:
                saved_calls += 1
                continue

            poly_item = poly_list[p_idx]
            kalshi_item = kalshi_list[k_idx]

            if not self._strict_heuristic_check(poly_item, kalshi_item):
                p_title = poly_item.get("event", "")[:30]
                k_title = kalshi_item.get("event", "")[:30]
                print(f"Bouncer blocked: {p_title}... vs {k_title}...")
                saved_calls += 1
                continue

            if score >= self.auto_accept_threshold:
                p_txt = f"{poly_item.get('event','')} {poly_item.get('description','')}"
                k_txt = f"{kalshi_item.get('event','')} {kalshi_item.get('description','')}"
                jacc = self._calculate_jaccard(p_txt, k_txt)
                if jacc >= self.jaccard_min_for_auto_accept:
                    print(
                        f"Fast Lane Match: {poly_item.get('event','')} "
                        f"(Score: {score:.2f}, Jaccard: {jacc:.2f})"
                    )
                    matches.append((poly_item, kalshi_item, score))
                    seen_poly.add(p_idx)
                    seen_kalshi.add(k_idx)
                    saved_calls += 1
                    continue

            print(f"Judge required (Score: {score:.2f}) for: {poly_item.get('event','')}")
            confidence, reason = self._verify_match_with_llm(poly_item, kalshi_item)
            if (not self.llm_enabled or self._last_llm_failed) and confidence < 0.7:
                f_conf, f_reason = self._cheap_verify(poly_item, kalshi_item, score)
                if f_conf >= 0.7:
                    confidence, reason = f_conf, f_reason
                    print("MATCH (fallback)")
                    print(f"     Poly: {poly_item.get('url', 'No URL')}")
                    print(f"     Kalshi: {kalshi_item.get('url', 'No URL')}")
                    print(f"     Vector score: {score:.2f} | Fallback: {confidence:.2f}")
                    print(f"     Reason: {reason}")

            if confidence >= 0.7:
                print("MATCH FOUND!")
                print(f"     Poly: {poly_item.get('url', 'No URL')}")
                print(f"     Kalshi: {kalshi_item.get('url', 'No URL')}")
                print(f"     Vector score: {score:.2f} | LLM: {confidence:.2f}")
                print(f"     Reason: {reason}")
                matches.append((poly_item, kalshi_item, confidence))
                seen_poly.add(p_idx)
                seen_kalshi.add(k_idx)

        if saved_calls:
            print(f"Total time saved: Skipped {saved_calls} expensive LLM calls.")

        return matches

    def _verify_match_with_llm(self, poly: Dict, kalshi: Dict) -> Tuple[float, str]:
        """
        Ask Ollama if these two markets represent the same event.
        """
        if not self.llm_enabled:
            self._last_llm_failed = True
            return 0.0, "LLM disabled"
        poly_text = f"Title: {poly.get('event','')}\nDescription: {poly.get('description', 'N/A')}"
        kalshi_text = f"Title: {kalshi.get('event','')}\nRules: {kalshi.get('description', 'N/A')}"

        user_prompt = f"""
        Compare these two prediction market events. Your goal is to determine if they
        are the EXACT SAME betting market.

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
        - Look for the CORE outcome. If Market A asks "Will X happen?" and Market B
          says "If X happens, Yes", they are a MATCH.

        If they are different in ANY critical way (dates, teams, logic), return "match": false.
        Be skeptical. Most pairs are NOT matches.

        Reply ONLY with a JSON object:
        {{
            "reason": "short explanation of why they match or not",
            "match": boolean,
            "confidence": float (0.0 to 1.0)
        }}
        """
        system_prompt = (
            "You are a strict JSON judge. Respond ONLY with a valid JSON object "
            "matching the schema."
        )

        try:
            chat_payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "format": "json",
                "stream": False
            }
            chat_resp = requests.post(f"{self.ollama_url}/ollama/v1/generate", json=chat_payload, timeout=60)

            chat_resp.raise_for_status()
            chat_data = chat_resp.json()

            content_str = (
                (chat_data.get("message") or {}).get("content") or chat_data.get("response") or ""
            )
            content = self._parse_llm_json(content_str)
            reason = content.get("reason", "No reason provided")
            confidence = float(content.get("confidence", 0.0))
            is_match = content.get("match", False)
            # Treat empty/invalid JSON as LLM failure to enable fallback
            if reason in ("Empty LLM response", "Invalid JSON response"):
                self._last_llm_failed = True
                return 0.0, reason
            self._last_llm_failed = False
            if is_match:
                return confidence, reason
            return 0.0, reason
        except Exception as e1:
            # Try generate endpoint as fallback
            error_logger.log_error(e1, context="LLM verification (/api/chat)")
            try:
                gen_payload = {
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\n{user_prompt}",
                    "format": "json",
                    "stream": False,
                }
                gen_resp = requests.post(
                    f"{self.ollama_url}/ollama/v1/generate", json=gen_payload, timeout=60
                )
                gen_resp.raise_for_status()
                gen_data = gen_resp.json()
                content_str = gen_data.get("response", "")
                content = self._parse_llm_json(content_str)
                reason = content.get("reason", "No reason provided")
                confidence = float(content.get("confidence", 0.0))
                is_match = content.get("match", False)
                if reason in ("Empty LLM response", "Invalid JSON response"):
                    self._last_llm_failed = True
                    return 0.0, reason
                self._last_llm_failed = False
                if is_match:
                    return confidence, reason
                return 0.0, reason
            except Exception as e2:
                error_logger.log_error(e2, context="LLM verification (/api/generate)")
                try:
                    oai_payload = {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    }
                    oai_resp = requests.post(
                        f"{self.ollama_url}/ollama/v1/generate",
                        json=oai_payload,
                        timeout=60,
                    )
                    if oai_resp.status_code == 404:
                        raise RuntimeError("/v1/chat/completions not found; trying /v1/completions")
                    oai_resp.raise_for_status()
                    oai_data = oai_resp.json()
                    msg = (oai_data.get("choices") or [{}])[0].get("message") or {}
                    content_str = msg.get("content", "")
                    content = self._parse_llm_json(content_str)
                    reason = content.get("reason", "No reason provided")
                    confidence = float(content.get("confidence", 0.0))
                    is_match = content.get("match", False)
                    if reason in ("Empty LLM response", "Invalid JSON response"):
                        self._last_llm_failed = True
                        return 0.0, reason
                    self._last_llm_failed = False
                    if is_match:
                        return confidence, reason
                    return 0.0, reason
                except Exception as e3:
                    error_logger.log_error(e3, context="LLM verification (/v1/chat/completions)")
                    try:
                        comp_payload = {
                            "model": self.model,
                            "prompt": f"{system_prompt}\n\n{user_prompt}",
                        }
                        comp_resp = requests.post(
                            f"{self.ollama_url}/v1/completions",
                            json=comp_payload,
                            timeout=60,
                        )
                        comp_resp.raise_for_status()
                        comp_data = comp_resp.json()
                        content_str = comp_data.get("choices", [{}])[0].get("text", "")
                        content = self._parse_llm_json(content_str)
                        reason = content.get("reason", "No reason provided")
                        confidence = float(content.get("confidence", 0.0))
                        is_match = content.get("match", False)
                        if reason in ("Empty LLM response", "Invalid JSON response"):
                            self._last_llm_failed = True
                            return 0.0, reason
                        self._last_llm_failed = False
                        if is_match:
                            return confidence, reason
                        return 0.0, reason
                    except Exception as e4:
                        error_logger.log_error(e4, context="LLM verification (/v1/completions)")
                        try:
                            base_prompt = (
                                "You are a strict JSON judge. Respond ONLY with a JSON object."
                            )
                            full_prompt = f"{base_prompt}\n\n{user_prompt}"
                            proc = subprocess.run(
                                [OLLAMA_CLI, "run", self.model],
                                input=full_prompt.encode("utf-8"),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                timeout=60,
                                check=True,
                            )
                            out = proc.stdout.decode("utf-8", errors="ignore")
                            content = self._parse_llm_json(out)
                            reason = content.get("reason", "No reason provided")
                            confidence = float(content.get("confidence", 0.0))
                            is_match = content.get("match", False)
                            self._last_llm_failed = False
                            if is_match:
                                return confidence, reason
                            return 0.0, reason
                        except Exception as e5:
                            error_logger.log_error(e5, context="LLM verification (ollama CLI)")
                            self._llm_error_count += 1
                            self._last_llm_failed = True
                            if self._llm_error_count >= self._llm_error_limit:
                                print(
                                    "LLM repeatedly failing (>=3 errors). "
                                    "Disabling LLM for this run."
                                )
                                self.llm_enabled = False
                            return 0.0, "Error verifying match with LLM"

    def _parse_llm_json(self, text: str) -> Dict:
        try:
            return json.loads(text)
        except Exception:
            pass
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return {
                    "match": False,
                    "confidence": 0.0,
                    "reason": "Invalid JSON response",
                }
        return {"match": False, "confidence": 0.0, "reason": "Empty LLM response"}

    def _cheap_verify(self, poly: Dict, kalshi: Dict, sim_score: float) -> Tuple[float, str]:
        p_text_raw = f"{poly.get('event','')} {poly.get('description','')}".strip()
        k_text_raw = f"{kalshi.get('event','')} {kalshi.get('description','')}".strip()
        p_text = p_text_raw.lower()
        k_text = k_text_raw.lower()
        if not p_text or not k_text:
            return 0.0, "Insufficient text for fallback"

        def norm_text(s: str) -> str:
            s = re.sub(r"federal\s+funds?\s+rate", "fedfundsrate", s)
            s = re.sub(r"\bfed(?:eral)?\s+rate\b", "fedfundsrate", s)
            s = re.sub(r"\bincrease(?:s|d)?\b", "hike", s)
            s = re.sub(r"\braise(?:s|d)?\b", "hike", s)
            s = re.sub(r"\bhike(?:s|d)?\b", "hike", s)
            return s

        def toks(s: str) -> List[str]:
            return re.findall(r"[a-z0-9]+", s)

        stop = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "to",
            "of",
            "in",
            "on",
            "and",
            "or",
            "will",
            "be",
            "if",
            "for",
            "with",
            "by",
            "at",
            "as",
            "this",
            "that",
            "it",
            "next",
        }
        p_norm = norm_text(p_text)
        k_norm = norm_text(k_text)
        pt = [t for t in toks(p_norm) if t not in stop]
        kt = [t for t in toks(k_norm) if t not in stop]
        pset, kset = set(pt), set(kt)
        inter = pset & kset
        union = pset | kset
        jacc = (len(inter) / len(union)) if union else 0.0

        p_years = set(re.findall(r"\b(19\d{2}|20\d{2})\b", p_text))
        k_years = set(re.findall(r"\b(19\d{2}|20\d{2})\b", k_text))
        if p_years and k_years and p_years.isdisjoint(k_years):
            return 0.0, "Year mismatch"

        key = {
            "fed",
            "federal",
            "fedfundsrate",
            "funds",
            "rate",
            "hike",
            "increase",
            "interest",
            "cut",
            "raise",
        }
        domain_overlap = len((pset & kset) & key)

        if (
            (p_years and k_years and not p_years.isdisjoint(k_years))
            and domain_overlap >= 2
            and sim_score >= 0.55
            and jacc >= 0.25
        ):
            year_boost = 0.1
            conf = min(0.92, 0.72 + 0.2 * (sim_score - 0.55) / 0.45 + year_boost)
            return (
                conf,
                f"Fallback accepted (domain+year, jacc={jacc:.2f}, sim={sim_score:.2f})",
            )

        # Default stricter acceptance
        if jacc >= 0.36 and sim_score >= 0.62:
            year_boost = 0.05 if (p_years and k_years and not p_years.isdisjoint(k_years)) else 0.0
            conf = min(0.9, 0.7 + 0.2 * (sim_score - 0.62) / 0.38 + year_boost)
            return conf, f"Fallback accepted (jacc={jacc:.2f}, sim={sim_score:.2f})"

        return 0.0, f"Fallback rejected (jacc={jacc:.2f}, sim={sim_score:.2f})"

    def _extract_years(self, text: str) -> Set[str]:
        return set(re.findall(r"\b(20\d{2})\b", text))

    def _strict_heuristic_check(self, poly: Dict, kalshi: Dict) -> bool:
        p_text = f"{poly.get('event','')} {poly.get('description','')}".lower()
        k_text = f"{kalshi.get('event','')} {kalshi.get('description','')}".lower()
        p_years = self._extract_years(p_text)
        k_years = self._extract_years(k_text)
        if p_years and k_years and p_years.isdisjoint(k_years):
            return False
        p_toks = self._normalize_tokens(p_text)
        k_toks = self._normalize_tokens(k_text)
        critical_groups = [
            {"bitcoin", "ethereum", "solana"},
            {"trump", "harris", "biden"},
            {"republican", "democrat"},
            {"nfl", "nba", "mlb"},
        ]
        for group in critical_groups:
            p_has = p_toks & group
            k_has = k_toks & group
            if p_has and k_has and p_has.isdisjoint(k_has):
                return False

        return True

    def _normalize_tokens(self, text: str) -> Set[str]:
        raw_toks = re.findall(r"[a-z0-9]+", text.lower())
        norm_toks: Set[str] = set()
        for t in raw_toks:
            norm_toks.add(self.ALIAS_MAP.get(t, t))
        return norm_toks

    def _calculate_jaccard(self, text1: str, text2: str) -> float:
        s1 = self._normalize_tokens(text1)
        s2 = self._normalize_tokens(text2)
        if not s1 or not s2:
            return 0.0
        return len(s1 & s2) / len(s1 | s2)

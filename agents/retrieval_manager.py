"""
Retrieval Manager — multi-candidate KB retrieval with domain grouping and
score-gap analysis.

Responsibilities:
  • Retrieves top-K KB candidates (default 8) instead of just top 1.
  • Groups candidates by likely system/domain/topic.
  • Calculates score gap between top candidates.
  • Detects when multiple different systems compete closely.
  • Provides structured retrieval analysis for the decision engine.

"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from rag_manager import get_embed_model
import database

log = logging.getLogger("RetrievalManager")

# CONSTANTS

DEFAULT_TOP_K = 8  # retrieve more candidates for analysis

# Score-gap thresholds (cosine distance, lower = better)
HIGH_CONFIDENCE_THRESHOLD = 0.45     # distance below this → high KB confidence
MEDIUM_CONFIDENCE_THRESHOLD = 0.60   # distance below this → medium
SCORE_GAP_THRESHOLD = 0.08          # if gap between #1 and #2 < this → ambiguous
MULTI_DOMAIN_GAP_THRESHOLD = 0.12   # if best scores across domains are within this → multi-domain ambiguity

# Domain keywords for auto-classification of KB articles
DOMAIN_KEYWORDS = {
    "windows": ["windows", "active directory", "ad ", "gpo", "group policy",
                "domain", "ntlm", "kerberos", "logon", "winlogon"],
    "sap": ["sap", "sap gui", "fiori", "hana", "transaction", "tcode",
            "abap", "basis", "s/4hana"],
    "outlook": ["outlook", "email", "mailbox", "owa", "exchange",
                "calendar", "meeting invite", "pst", "ost"],
    "vpn": ["vpn", "anyconnect", "cisco", "globalprotect", "remote access",
            "tunnel", "split tunnel"],
    "teams": ["teams", "microsoft teams", "teams meeting", "teams chat"],
    "sharepoint": ["sharepoint", "onedrive", "document library", "site collection"],
    "network": ["network", "dns", "dhcp", "proxy", "firewall", "wifi",
                "wi-fi", "ethernet", "switch", "router"],
    "hardware": ["hardware", "laptop", "desktop", "monitor", "keyboard",
                 "mouse", "printer", "scanner", "docking station"],
    "oracle": ["oracle", "oracle db", "plsql", "tns", "listener"],
    "browser": ["chrome", "edge", "firefox", "browser", "internet explorer"],
    "office": ["excel", "word", "powerpoint", "office 365", "microsoft 365"],
    "citrix": ["citrix", "xenapp", "xendesktop", "storefront", "receiver"],
    "storage": ["storage", "disk space", "quota", "backup", "restore",
                "onedrive", "file server"],
}


# MAIN CLASS

class RetrievalManager:
    """
    Multi-candidate KB retrieval with domain analysis.
    """

    # Public: retrieve_and_analyze

    def retrieve_and_analyze(self, query: str, top_k: int = DEFAULT_TOP_K, 
                             preferred_domain: str = None, strict_domain: bool = False) -> dict:
        """
        Retrieves top-k KB candidates and performs domain analysis.

        Parameters
        ----------
        query : str
            The search query (may be raw user message or refined query).
        top_k : int
            Number of candidates to retrieve.

        Returns
        -------
        dict
            {
                "candidates":       list[dict],   # raw KB hits with domain tags
                "domain_groups":    dict,          # domain → list of candidates
                "top_distance":     float|None,    # best candidate distance
                "score_gap":        float|None,    # gap between #1 and #2
                "is_multi_domain":  bool,          # multiple domains compete?
                "competing_domains": list[str],    # which domains are close
                "kb_confidence":    str,           # "high", "medium", "low"
                "analysis_summary": str,           # human-readable summary
            }
        """
        log.info("Multi-candidate retrieval started: query=%d chars, top_k=%d",
                 len(query), top_k)

        result = {
            "candidates": [],
            "domain_groups": {},
            "top_distance": None,
            "score_gap": None,
            "is_multi_domain": False,
            "competing_domains": [],
            "kb_confidence": "low",
            "analysis_summary": "No KB results found.",
        }

        try:
            query_vector = get_embed_model().encode(query)
            candidates = database.search_kb_vectors(query_vector, n_results=top_k)
        except Exception as e:
            log.error("KB vector search error: %s", e)
            return result

        if not candidates:
            log.info("No KB candidates returned")
            return result

        for c in candidates:
            c["_domain"] = self._classify_domain(c)

        result["candidates"] = candidates

        if strict_domain and preferred_domain:
            pref = preferred_domain.lower()
            candidates = [c for c in candidates if c["_domain"] == pref or pref in c["_domain"]]
            if not candidates:
                log.info("No candidates left after strict domain filtering (pref: %s)", pref)
                return result

        result["candidates"] = candidates
        result["domain_groups"] = self._group_by_domain(candidates)

        if preferred_domain:
            pref = preferred_domain.lower()
            for c in candidates:
                # If candidate domain matches preferred, boost it (lower distance)
                if c["_domain"] == pref or pref in c["_domain"]:
                    c["distance"] = max(0.0, c["distance"] - 0.15)
            # Re-sort after boosting
            candidates.sort(key=lambda x: x.get("distance", 1.0))

        result["top_distance"] = candidates[0].get("distance", 1.0)

        if len(candidates) >= 2:
            d1 = candidates[0].get("distance", 1.0)
            d2 = candidates[1].get("distance", 1.0)
            result["score_gap"] = round(d2 - d1, 4)
        else:
            result["score_gap"] = 1.0  # only one result, gap is large

        competing = self._find_competing_domains(result["domain_groups"])
        result["competing_domains"] = competing
        result["is_multi_domain"] = len(competing) > 1

        result["kb_confidence"] = self._determine_kb_confidence(
            result["top_distance"], result["score_gap"],
            result["is_multi_domain"]
        )

        result["analysis_summary"] = self._build_analysis_summary(result)

        log.info(
            "Retrieval analysis: top_dist=%.4f gap=%.4f multi_domain=%s "
            "competing=%s confidence=%s",
            result["top_distance"] or 0, result["score_gap"] or 0,
            result["is_multi_domain"], result["competing_domains"],
            result["kb_confidence"],
        )

        return result

    # Public: build_refined_query

    @staticmethod
    def build_refined_query(issue_fields: dict) -> str:
        """
        Builds a refined KB query from structured issue fields plus relevant
        situational context.

        Example:
            issue_fields = {system: "windows", symptom: "account_locked", 
                          action_attempted: "after reset password"}
            → "Windows account locked after reset password"
        """
        parts = []

        system = issue_fields.get("system")
        application = issue_fields.get("application")
        if system:
            parts.append(system.title())
        if application and application != system:
            parts.append(application.upper() if application.lower() == "sap"
                         else application.title())

        symptom = issue_fields.get("symptom", "")
        if symptom:
            parts.append(symptom.replace("_", " "))
        elif issue_fields.get("issue_type"):
            parts.append(issue_fields.get("issue_type").replace("_", " "))

        action = issue_fields.get("action_attempted")
        if action:
            parts.append(action)

        env = issue_fields.get("environmental_context")
        if env:
            parts.append(env)

        error_code = issue_fields.get("error_code")
        if error_code:
            parts.append(f"error {error_code}")

        device = issue_fields.get("device")
        if device:
            parts.append(device)

        # Fallback: if nothing useful extracted, use a cleaned raw message
        if not parts:
            raw = issue_fields.get("raw_message", "")
            return raw

        # Compact but informative
        query = " ".join(parts).strip()
        log.info("Refined query built: '%s'", query)
        return query

    # Private helpers

    @staticmethod
    def _classify_domain(candidate: dict) -> str:
        """Classifies a KB candidate into a domain based on title+content keywords."""
        title = (candidate.get("title") or "").lower()
        content = (candidate.get("content") or "").lower()[:500]  # only check start
        combined = f"{title} {content}"

        best_domain = "unknown"
        best_count = 0

        for domain, keywords in DOMAIN_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in combined)
            if count > best_count:
                best_count = count
                best_domain = domain

        return best_domain

    @staticmethod
    def _group_by_domain(candidates: list) -> dict:
        """Groups candidates by their _domain tag."""
        groups = {}
        for c in candidates:
            domain = c.get("_domain", "unknown")
            if domain not in groups:
                groups[domain] = []
            groups[domain].append(c)
        return groups

    @staticmethod
    def _find_competing_domains(domain_groups: dict) -> list:
        """
        Finds domains that have candidates with close distances,
        suggesting the query is ambiguous across multiple systems.
        """
        if len(domain_groups) <= 1:
            return list(domain_groups.keys())

        # Get best distance per domain
        domain_best = {}
        for domain, candidates in domain_groups.items():
            if candidates:
                best_dist = min(c.get("distance", 1.0) for c in candidates)
                domain_best[domain] = best_dist

        if not domain_best:
            return []

        # Sort by distance
        sorted_domains = sorted(domain_best.items(), key=lambda x: x[1])
        best_distance = sorted_domains[0][1]

        # Find domains within the multi-domain gap threshold
        # If the matches are all poor (> 0.72), don't suggest competing domains 
        # as they are likely random keyword hits in unrelated KB articles.
        if best_distance > 0.72:
            log.info("Best match too weak (%.4f) to trust competing domains", best_distance)
            return []

        competing = []
        for domain, dist in sorted_domains:
            if dist - best_distance <= MULTI_DOMAIN_GAP_THRESHOLD:
                competing.append(domain)

        return competing

    @staticmethod
    def _determine_kb_confidence(top_distance: float, score_gap: float,
                                  is_multi_domain: bool) -> str:
        """
        Determines KB confidence considering distance, gap, and domain spread.
        """
        if top_distance is None:
            return "low"

        # High confidence: good distance AND clear winner
        if (top_distance < HIGH_CONFIDENCE_THRESHOLD
                and score_gap > SCORE_GAP_THRESHOLD
                and not is_multi_domain):
            return "high"

        # Medium: decent distance but maybe not decisive
        if top_distance < MEDIUM_CONFIDENCE_THRESHOLD:
            if is_multi_domain or score_gap <= SCORE_GAP_THRESHOLD:
                return "medium"  # good match but ambiguous domain
            return "high"  # good match, clear domain

        # Low: nothing close enough
        return "low"

    @staticmethod
    def _build_analysis_summary(result: dict) -> str:
        """Builds a human-readable summary of the retrieval analysis."""
        parts = []
        top_dist = result.get("top_distance")
        if top_dist is not None:
            parts.append(f"Best match distance: {top_dist:.4f}")
        parts.append(f"Score gap: {result.get('score_gap', 0):.4f}")
        parts.append(f"Domains found: {list(result.get('domain_groups', {}).keys())}")
        if result["is_multi_domain"]:
            parts.append(f"⚠ Multiple competing domains: {result['competing_domains']}")
        parts.append(f"KB confidence: {result['kb_confidence']}")
        return " | ".join(parts)

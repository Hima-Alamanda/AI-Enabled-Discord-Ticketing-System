"""
Knowledge Agent — owns KB retrieval orchestration and confidence scoring.

Responsibilities (Phase 2 + Phase 3):
  • Executes vector search against the KB store (via database + rag_manager).
  • Searches past resolved tickets for similar issues.
  • Scores and filters past tickets by keyword relevance to avoid noise.
  • Merges KB articles (primary) and past tickets (supplementary) into
    a ranked context block for the RAG prompt.
  • Determines confidence using KB-first logic:
      - KB hit below distance threshold → "high"
      - No KB hit but strong past-ticket match → "medium"
      - Neither → "low"

Low-level utilities (get_embed_model, database.search_kb_vectors, etc.)
remain in their original modules.  This agent only orchestrates the
retrieval flow.
"""

import logging
import database
from rag_manager import get_embed_model

log = logging.getLogger("KnowledgeAgent")

# CONSTANTS

# Cosine distance threshold — below this the KB match is "high" confidence
KB_CONFIDENCE_THRESHOLD = 0.55

# How many KB vector results to fetch / include in context
KB_TOP_K = 8
KB_CONTEXT_LIMIT = 5

# Past-ticket retrieval limits
PAST_TICKET_SEARCH_LIMIT = 5          # fetch more so we can filter
PAST_TICKET_CONTEXT_LIMIT = 2         # max tickets in prompt context

# Minimum keyword-overlap ratio for a past ticket to be considered relevant
# e.g. if the query has 5 keywords, at least 2 must match (0.4 * 5 = 2)
PAST_TICKET_MIN_RELEVANCE = 0.30

# Minimum description length to consider a past ticket useful
PAST_TICKET_MIN_DESC_LEN = 30


class KnowledgeAgent:
    """
    Lightweight agent that orchestrates Knowledge Base retrieval
    with intelligent merge of KB articles and past tickets.
    """

    def search(self, query: str) -> dict:
        """
        Main entry point.  Searches the KB vector store and past resolved
        tickets, scores confidence, and assembles a merged context string
        for the RAG prompt.

        Parameters
        ----------
        query : str
            The search query (may be enriched by ContinuityAgent).

        Returns
        -------
        dict
            {
                "kb_results":   list[dict],   # raw vector hits
                "past_tickets": list[dict],   # filtered + scored past tickets
                "confidence":   "high"|"medium"|"low",
                "sources":      list[str],    # de-duped source names
                "context_text": str           # merged text block for the prompt
            }
        """
        log.info("KB search started (%d chars)", len(query))

        results = {
            "kb_results":   [],
            "past_tickets": [],
            "confidence":   "low",
            "sources":      [],
            "context_text": ""
        }

        kb_distance = None
        try:
            query_vector = get_embed_model().encode(query)
            kb_hits = database.search_kb_vectors(query_vector, n_results=KB_TOP_K)

            if kb_hits:
                results["kb_results"] = kb_hits
                results["sources"] = list(set(r["source"] for r in kb_hits))
                kb_distance = kb_hits[0].get("distance", 1.0)
                log.info("KB best distance: %.4f | threshold: < %.2f",
                         kb_distance, KB_CONFIDENCE_THRESHOLD)
            else:
                log.info("KB returned 0 hits")

        except Exception as e:
            log.error("KB vector search error: %s", e)

        try:
            raw_tickets = self._search_past_tickets(query)
            scored = self._score_past_tickets(raw_tickets, query)
            results["past_tickets"] = scored
            if scored:
                log.info("Past tickets: %d found → %d after relevance filter",
                         len(raw_tickets), len(scored))
        except Exception as e:
            log.error("Past ticket search error: %s", e)

        results["confidence"] = self._determine_confidence(
            kb_distance, results["kb_results"], results["past_tickets"]
        )

        results["context_text"] = self._build_context_text(
            results["kb_results"],
            results["past_tickets"],
            results["confidence"]
        )

        log.info("KB search complete: confidence=%s sources=%d past_tickets=%d",
                 results["confidence"], len(results["sources"]),
                 len(results["past_tickets"]))
        return results

    # Confidence logic

    @staticmethod
    def _determine_confidence(kb_distance, kb_results, scored_tickets) -> str:
        """
        KB-first confidence rules:
          1. KB distance < threshold            → "high"
          2. No strong KB, but relevant tickets  → "medium"
          3. Neither                             → "low"

        "medium" means: we don't have a documented KB fix, but similar
        issues have been resolved before — the LLM should mention this
        context without presenting it as a verified solution.
        """
        # Rule 1: KB has a concrete documented match
        if kb_results and kb_distance is not None and kb_distance < KB_CONFIDENCE_THRESHOLD:
            return "high"

        # Rule 2: No strong KB, but we have relevant past tickets
        if scored_tickets:
            # At least one ticket with decent relevance qualifies as "medium"
            best_score = max(t.get("_relevance_score", 0) for t in scored_tickets)
            if best_score >= 0.5:
                return "medium"

        # Rule 3: Nothing useful
        return "low"

    # Past-ticket scoring / filtering

    def _score_past_tickets(self, tickets: list, query: str) -> list:
        """
        Scores each past ticket by keyword-overlap relevance and filters
        out noisy / weak matches.

        Each surviving ticket gets a '_relevance_score' field (0.0–1.0)
        and a '_matched_keywords' field for logging.
        """
        if not tickets:
            return []

        # Build keyword set from query (words ≥ 3 chars, lowered)
        query_keywords = set(
            w.lower() for w in query.split() if len(w) >= 3
        )
        # Remove very common stop-words that cause false positives
        stop_words = {
            "the", "and", "for", "with", "not", "can", "how", "does",
            "this", "that", "from", "what", "when", "have", "has", "are",
            "was", "were", "been", "will", "its", "but", "about"
        }
        query_keywords -= stop_words

        if not query_keywords:
            log.debug("No meaningful keywords extracted — skipping ticket scoring")
            return []

        scored = []
        for ticket in tickets:
            subject = (ticket.get("subject") or "").lower()
            description = (ticket.get("description") or "").lower()
            combined_text = f"{subject} {description}"

            # Skip tickets with tiny descriptions (likely noise)
            if len(description.strip()) < PAST_TICKET_MIN_DESC_LEN:
                continue

            # Count keyword matches
            matched = set()
            for kw in query_keywords:
                if kw in combined_text:
                    matched.add(kw)

            if not matched:
                continue

            relevance = len(matched) / len(query_keywords)

            # Filter: must meet minimum relevance threshold
            if relevance < PAST_TICKET_MIN_RELEVANCE:
                continue

            ticket["_relevance_score"] = round(relevance, 2)
            ticket["_matched_keywords"] = list(matched)
            scored.append(ticket)

        # Sort by relevance descending
        scored.sort(key=lambda t: t["_relevance_score"], reverse=True)

        log.debug("Ticket scoring: %d/%d survived (threshold=%.0f%%)",
                  len(scored), len(tickets), PAST_TICKET_MIN_RELEVANCE * 100)
        return scored

    # Past-ticket DB lookup

    @staticmethod
    def _search_past_tickets(query: str) -> list:
        """Searches closed/resolved tickets similar to the query."""
        try:
            return database.search_similar_resolved_tickets(
                query, limit=PAST_TICKET_SEARCH_LIMIT
            )
        except Exception as e:
            log.error("Past ticket DB search error: %s", e)
            return []

    # Context assembly (merged, ranked)

    @staticmethod
    def _build_context_text(kb_results: list, past_tickets: list,
                            confidence: str) -> str:
        """
        Assembles the combined context block for the RAG prompt.

        Merge strategy:
          • KB articles are ALWAYS presented first as the primary source.
          • Past tickets appear in a separate, clearly-labeled section
            with a trust annotation so the LLM treats them as
            supplementary evidence, not as verified fixes.
          • When confidence is "high" (strong KB match), past tickets get
            a shorter allowance to avoid prompt pollution.
        """
        context_parts = []

        if kb_results:
            context_parts.append("=== VERIFIED TECHNICAL PROCEDURES (Primary) ===")
            for r in kb_results[:KB_CONTEXT_LIMIT]:
                context_parts.append(
                    f"[Procedure: {r.get('title', 'Untitled')}]\n"
                    f"{r.get('content', '')[:600]}"
                )

        if past_tickets:
            # When KB confidence is high, include fewer ticket details
            # to avoid the LLM weighting unverified ticket patterns
            # over the documented fix.
            ticket_limit = 1 if confidence == "high" else PAST_TICKET_CONTEXT_LIMIT
            desc_limit = 150 if confidence == "high" else 250
            res_limit = 200 if confidence == "high" else 350

            context_parts.append(
                "\n=== HISTORICAL MATCHES (Supplementary — Patterns only) ==="
            )
            for t in past_tickets[:ticket_limit]:
                relevance_pct = int(t.get("_relevance_score", 0) * 100)
                context_parts.append(
                    f"[Reference {t.get('ticket_id', '?')}] "
                    f"{t.get('subject', '')} "
                    f"(relevance: {relevance_pct}%)\n"
                    f"Problem: {t.get('description', '')[:desc_limit]}\n"
                    f"Resolution: {t.get('resolution', 'No resolution logged.')[:res_limit]}"
                )

        if context_parts:
            return "\n\n".join(context_parts)
        return "No confirmed procedures or matches found."

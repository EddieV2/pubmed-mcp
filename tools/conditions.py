"""Symptom → disease tools.

The headline capability: standardize free-text symptoms into HPO terms, then rank candidate
diseases with Monarch's semantic-similarity engine. Best suited to rare & genetic disease.

These are decision-support tools (information retrieval over curated knowledge bases), NOT a
diagnostic device. Results are framed accordingly.
"""

import re
from typing import Any, Dict, List, Tuple

from clients.base import UpstreamError

_HP_CODE = re.compile(r"^HP:\d{7}$", re.IGNORECASE)
_XREF_PREFIXES = {
    "OMIM", "ORPHANET", "ORPHA", "MONDO", "DOID", "UMLS",
    "MESH", "ICD10", "ICD10CM", "ICD11", "NCIT", "MEDGEN",
}
_DISCLAIMER = (
    "Decision-support only: these are candidate conditions ranked by phenotype similarity "
    "from the Monarch knowledge graph, not a diagnosis. Confirm with a qualified clinician."
)


def _map_symptoms_to_hpo(hpo, symptoms: List[str]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Resolve each free-text symptom (or HP: code) to an HPO term.

    Returns (termset, mapping) where mapping is transparent about how each input resolved.
    """
    termset: List[str] = []
    mapping: List[Dict[str, Any]] = []
    for raw in symptoms:
        text = (raw or "").strip()
        if not text:
            continue
        if _HP_CODE.match(text):
            code = text.upper()
            termset.append(code)
            mapping.append({"input": text, "matched_id": code, "matched_name": None, "source": "direct"})
            continue
        hits = hpo.search(text, max_list=5)
        if hits:
            top = hits[0]
            termset.append(top["id"])
            mapping.append({
                "input": text,
                "matched_id": top["id"],
                "matched_name": top["name"],
                "alternatives": hits[1:4],
                "source": "hpo_autocomplete",
            })
        else:
            mapping.append({"input": text, "matched_id": None, "unmatched": True, "source": "hpo_autocomplete"})
    return termset, mapping


def _collect_xrefs(entity: Dict[str, Any]) -> List[str]:
    """Pull useful disease cross-references (OMIM/Orphanet/ICD/...) from a Monarch entity."""
    raw: List[Any] = []
    for key in ("xref", "mappings"):
        val = entity.get(key)
        if isinstance(val, list):
            raw.extend(val)
    out: List[str] = []
    seen = set()
    for item in raw:
        if isinstance(item, str):
            curie = item
        elif isinstance(item, dict):
            curie = item.get("id") or item.get("curie")
        else:
            curie = None
        if not curie or ":" not in curie:
            continue
        if curie.split(":", 1)[0].upper() in _XREF_PREFIXES and curie not in seen:
            seen.add(curie)
            out.append(curie)
    return out[:15]


def _names(items: Any) -> List[str]:
    """Normalize a list of gene/term objects (dicts or strings) to display names."""
    if not items:
        return []
    if not isinstance(items, list):
        items = [items]
    out = []
    for it in items:
        if isinstance(it, dict):
            out.append(it.get("name") or it.get("label") or it.get("id"))
        elif it is not None:
            out.append(str(it))
    return [x for x in out if x]


def _find_conditions(monarch, hpo, symptoms: List[str], max_results: int, metric: str) -> Dict[str, Any]:
    termset, mapping = _map_symptoms_to_hpo(hpo, symptoms)
    if not termset:
        return {
            "error": "None of the provided symptoms could be mapped to HPO terms.",
            "symptom_mapping": mapping,
            "hint": "Try simpler clinical terms (e.g. 'seizures', 'short stature') or pass HP: codes directly.",
        }
    try:
        results = monarch.semsim_search(termset, group="Human Diseases", metric=metric, limit=max_results)
    except UpstreamError as e:
        # Upstream timed out / was unreachable even after the longer budget + retry. The HPO
        # mapping still succeeded, so hand it back with an actionable, retryable message rather
        # than discarding the work.
        return {
            "error": f"Condition ranking is temporarily unavailable: {e}",
            "detail": (
                "Monarch's semantic-similarity service is compute-heavy and occasionally slow or "
                "briefly unreachable. Your symptoms mapped to HPO terms successfully — retry shortly."
            ),
            "query_symptoms": symptoms,
            "hpo_terms_used": termset,
            "symptom_mapping": mapping,
            "ranked_conditions": [],
        }

    ranked: List[Dict[str, Any]] = []
    for r in results:
        subject = r.get("subject", {}) or {}
        score = r.get("score")
        description = (subject.get("description") or "").strip()
        ranked.append({
            "id": subject.get("id"),
            "name": subject.get("name"),
            "score": round(score, 4) if isinstance(score, (int, float)) else score,
            "cross_references": _collect_xrefs(subject),
            "description": (description[:280] + "…") if len(description) > 280 else (description or None),
        })

    return {
        "query_symptoms": symptoms,
        "hpo_terms_used": termset,
        "symptom_mapping": mapping,
        "metric": metric,
        "result_count": len(ranked),
        "ranked_conditions": ranked,
        "source": "Monarch Initiative semsim (api-v3.monarchinitiative.org)",
        "disclaimer": _DISCLAIMER,
    }


def _enrich_disease(xrefs: List[str], orphanet, medlineplus, omim) -> Dict[str, Any]:
    """Best-effort multi-source enrichment keyed off a disease's cross-references.

    Each source is optional and isolated: a failure or a missing client degrades that one
    field, never the whole card.
    """
    enrichment: Dict[str, Any] = {}

    if orphanet:
        orpha = next((x for x in xrefs if x.upper().startswith(("ORPHANET:", "ORPHA:"))), None)
        if orpha:
            try:
                ent = orphanet.get_clinical_entity(orpha.split(":", 1)[1])
                enrichment["orphanet"] = {
                    "orphacode": ent.get("ORPHAcode"),
                    "preferred_term": ent.get("Preferred term"),
                    "definition": ent.get("Definition"),
                    "url": ent.get("Orphanet URL"),
                }
            except Exception as e:
                enrichment["orphanet"] = {"error": str(e)}

    if medlineplus:
        icd = next((x for x in xrefs if x.upper().startswith("ICD10CM:")), None)
        if icd:
            try:
                topics = medlineplus.connect_by_icd10cm(icd.split(":", 1)[1])
                if topics:
                    enrichment["patient_info"] = topics[:3]
            except Exception as e:
                enrichment["patient_info"] = {"error": str(e)}

    if omim:
        mim = next((x for x in xrefs if x.upper().startswith("OMIM:")), None)
        if mim:
            try:
                enrichment["omim"] = omim.get_entry(mim.split(":", 1)[1])
            except Exception as e:
                enrichment["omim"] = {"error": str(e)}

    return enrichment


def _get_disease_info(
    monarch, disease_id: str, *, orphanet=None, medlineplus=None, omim=None, enrich: bool = True
) -> Dict[str, Any]:
    entity = monarch.get_entity(disease_id)
    inheritance = entity.get("inheritance")
    if isinstance(inheritance, dict):
        inheritance = inheritance.get("name") or inheritance.get("label") or inheritance.get("id")

    xrefs = _collect_xrefs(entity)
    phenotypes = entity.get("has_phenotype_label") or []
    card: Dict[str, Any] = {
        "id": entity.get("id"),
        "name": entity.get("name"),
        "category": entity.get("category"),
        "description": entity.get("description"),
        "inheritance": inheritance,
        "causal_genes": list(dict.fromkeys(_names(entity.get("causal_gene"))))[:20],
        "phenotypes": phenotypes[:40] if isinstance(phenotypes, list) else phenotypes,
        "phenotype_count": entity.get("has_phenotype_count"),
        "cross_references": xrefs,
        "association_counts": entity.get("association_counts"),
        "sources": ["Monarch Initiative"],
        "disclaimer": _DISCLAIMER,
    }

    if enrich:
        extra = _enrich_disease(xrefs, orphanet, medlineplus, omim)
        if extra:
            card["enrichment"] = extra
            if isinstance(extra.get("orphanet"), dict) and "error" not in extra["orphanet"]:
                card["sources"].append("Orphanet")
            if isinstance(extra.get("patient_info"), list):
                card["sources"].append("MedlinePlus")
            if isinstance(extra.get("omim"), dict) and extra["omim"].get("found"):
                card["sources"].append("OMIM")
    return card


def register(mcp, monarch, hpo, orphanet=None, medlineplus=None, omim=None) -> None:
    """Attach symptom→disease tools to the MCP server."""

    @mcp.tool()
    def lookup_hpo_terms(symptoms: List[str]) -> dict:
        """Map free-text symptom descriptions to standardized Human Phenotype Ontology (HPO) terms.

        Useful for inspecting or disambiguating how symptoms will be interpreted before ranking
        conditions. Accepts plain descriptions (e.g. "seizures", "webbed neck") or HP: codes.

        Returns:
            Dictionary with hpo_terms (the chosen HP: codes), a per-symptom mapping (including
            alternative matches), and count.
        """
        try:
            if not symptoms:
                return {"error": "Provide at least one symptom."}
            termset, mapping = _map_symptoms_to_hpo(hpo, symptoms)
            return {"hpo_terms": termset, "mapping": mapping, "count": len(termset)}
        except Exception as e:
            return {"error": f"HPO lookup failed: {e}"}

    @mcp.tool()
    def find_conditions_by_symptoms(
        symptoms: List[str],
        max_results: int = 10,
        metric: str = "ancestor_information_content",
    ) -> dict:
        """Find candidate diseases ranked by how well they match a set of symptoms.

        Standardizes the symptoms to HPO terms, then uses the Monarch Initiative's
        phenotype semantic-similarity engine to rank candidate conditions. Strongest for
        rare and genetic diseases. This is decision-support, NOT a diagnosis.

        Args:
            symptoms: Free-text symptoms (e.g. ["arachnodactyly", "ectopia lentis", "tall stature"])
                or HP: codes (e.g. "HP:0001166"). Provide several for better ranking.
            max_results: Number of candidate conditions to return (1-50, default 10).
            metric: Similarity metric — "ancestor_information_content" (default),
                "jaccard_similarity", or "phenodigm_score".

        Returns:
            Dictionary with ranked_conditions (each: MONDO id, name, score, cross_references,
            description), the hpo_terms_used, the symptom_mapping, and a disclaimer.
        """
        try:
            if not symptoms:
                return {"error": "Provide at least one symptom."}
            max_results = max(1, min(int(max_results), 50))
            return _find_conditions(monarch, hpo, symptoms, max_results, metric)
        except Exception as e:
            return {"error": f"Condition search failed: {e}"}

    @mcp.tool()
    def get_disease_info(disease_id: str, enrich: bool = True) -> dict:
        """Get a structured, multi-source summary for a disease by ontology ID.

        Args:
            disease_id: A disease CURIE, preferably MONDO (e.g. "MONDO:0007947"). OMIM/Orphanet
                IDs (e.g. "OMIM:154700") also resolve where Monarch has a mapping.
            enrich: If true (default), add Orphanet (rare-disease definition), MedlinePlus
                (patient-friendly info via ICD-10-CM), and OMIM (if an academic key is configured).

        Returns:
            Dictionary with name, description, inheritance, causal_genes, characteristic phenotypes,
            cross_references (OMIM/Orphanet/ICD/...), association_counts, and — when enriched — an
            `enrichment` block plus the list of `sources` consulted.
        """
        try:
            if not disease_id or not disease_id.strip():
                return {"error": "disease_id is required (e.g. MONDO:0007947)."}
            return _get_disease_info(
                monarch, disease_id.strip(),
                orphanet=orphanet, medlineplus=medlineplus, omim=omim, enrich=enrich,
            )
        except Exception as e:
            return {"error": f"Disease lookup failed: {e}"}

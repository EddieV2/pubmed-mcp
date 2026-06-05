"""Genetics tools — gene → clinically-relevant variants via NCBI ClinVar.

Completes the rare-disease chain: `find_conditions_by_symptoms` → `get_disease_info`
(returns causal genes) → `find_genetic_variants` (variants for a gene).
"""

from typing import Any, Dict


def _format_variant(rec: Dict[str, Any]) -> Dict[str, Any]:
    gc = rec.get("germline_classification") or {}
    conditions = []
    for trait in gc.get("trait_set") or []:
        name = trait.get("trait_name")
        if name and name.lower() not in ("not provided", "not specified"):
            conditions.append(name)
    variation = (rec.get("variation_set") or [{}])[0]
    locs = variation.get("variation_loc") or []
    grch38 = next((l for l in locs if l.get("assembly_name") == "GRCh38"), locs[0] if locs else {})
    location = None
    if grch38.get("chr"):
        location = f"GRCh38 chr{grch38.get('chr')}:{grch38.get('start')}-{grch38.get('stop')}"
    return {
        "accession": rec.get("accession"),
        "name": rec.get("title"),
        "type": rec.get("obj_type"),
        "gene": rec.get("gene_sort"),
        "clinical_significance": gc.get("description"),
        "review_status": gc.get("review_status"),
        "last_evaluated": gc.get("last_evaluated"),
        "protein_change": rec.get("protein_change") or None,
        "conditions": conditions[:6],
        "location": location,
    }


def _find_variants(ncbi, gene: str, clinical_significance: str, max_results: int) -> Dict[str, Any]:
    term = f"{gene}[gene]"
    cs = (clinical_significance or "").strip().lower()
    if cs and cs != "any":
        term += f' AND "{cs}"[clinsig]'
    found = ncbi.search("clinvar", term, retmax=max_results)
    ids = found["ids"]
    variants = []
    if ids:
        data = ncbi.esummary_json("clinvar", ids)
        result = data.get("result", {}) or {}
        for uid in result.get("uids", []):
            variants.append(_format_variant(result[uid]))
    return {
        "gene": gene,
        "clinical_significance_filter": cs or "any",
        "total_matches": found["total_count"],
        "returned": len(variants),
        "variants": variants,
        "source": "NCBI ClinVar (E-utilities)",
        "disclaimer": "Classifications are submitter-provided and may conflict; verify in ClinVar before any clinical use.",
    }


def register(mcp, ncbi) -> None:
    """Attach genetics tools."""

    @mcp.tool()
    def find_genetic_variants(
        gene: str, clinical_significance: str = "pathogenic", max_results: int = 15
    ) -> dict:
        """Find clinically-relevant variants for a gene from NCBI ClinVar.

        Pairs with `get_disease_info`: take a disease's causal gene and list its reported variants.

        Args:
            gene: Gene symbol (e.g. "FBN1").
            clinical_significance: Filter — "pathogenic" (default), "likely pathogenic",
                "benign", "likely benign", "uncertain significance", or "any".
            max_results: Number of variants (1-50, default 15).

        Returns:
            Dictionary with total_matches and variants (each: accession, name/HGVS, type, gene,
            clinical_significance, review_status, protein_change, associated conditions, location).
        """
        try:
            if not gene.strip():
                return {"error": "Gene symbol is required (e.g. FBN1)."}
            max_results = max(1, min(int(max_results), 50))
            return _find_variants(ncbi, gene.strip(), clinical_significance, max_results)
        except Exception as e:
            return {"error": f"Variant search failed: {e}"}

"""Smoke test for the Biomed MCP server.

Verifies tool registration and exercises each client against the live upstream APIs
(Monarch, HPO, NCBI/ClinVar, Europe PMC, ClinicalTrials.gov, MedlinePlus, Orphanet). Run:

    venv/bin/python test_smoke.py

Exits non-zero if any check fails. Requires network access. OMIM is skipped unless OMIM_API_KEY is set.
"""

import asyncio
import sys

import server
from clients.base import UpstreamUnavailable
from tools.conditions import _find_conditions, _get_disease_info, _map_symptoms_to_hpo
from tools.genetics import _find_variants

EXPECTED_TOOLS = {
    "search_articles", "download_article", "download_articles_batch", "get_article_summaries",
    "lookup_hpo_terms", "find_conditions_by_symptoms", "get_disease_info",
    "find_genetic_variants", "search_literature", "search_clinical_trials",
}

# Classic Marfan syndrome phenotypes — used as a ground-truth sanity check.
MARFAN_SYMPTOMS = ["arachnodactyly", "ectopia lentis", "aortic root aneurysm", "tall stature"]


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")
    return bool(cond)


def main() -> int:
    r = []

    # 1) Tools register on the FastMCP instance.
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    r.append(check("tools registered", EXPECTED_TOOLS <= names,
                   f"{len(names)} tools: {', '.join(sorted(names))}"))

    # 2) HPO mapping: free text -> HP: codes.
    termset, _ = _map_symptoms_to_hpo(server.hpo, MARFAN_SYMPTOMS)
    r.append(check("hpo mapping", len(termset) >= 3 and all(t.startswith("HP:") for t in termset),
                   f"{len(termset)}/{len(MARFAN_SYMPTOMS)} -> {termset}"))

    # 3) Symptom -> disease ranking returns Marfan-spectrum conditions.
    res = _find_conditions(server.monarch, server.hpo, MARFAN_SYMPTOMS, 8, "ancestor_information_content")
    ranked = res.get("ranked_conditions", [])
    blob = " ".join((c.get("name") or "").lower() for c in ranked)
    r.append(check("find_conditions_by_symptoms",
                   bool(ranked) and any(k in blob for k in ("marfan", "ectopia lentis", "mass syndrome", "loeys")),
                   f"top: {ranked[0]['name']} ({ranked[0]['id']})" if ranked else "no results"))

    # 4) Disease card + multi-source enrichment (Monarch + Orphanet + MedlinePlus).
    info = _get_disease_info(server.monarch, "MONDO:0007947", orphanet=server.orphanet,
                             medlineplus=server.medlineplus, omim=server.omim, ols=server.ols)
    genes = [g.upper() for g in info.get("causal_genes", [])]
    enr = info.get("enrichment", {})
    orpha_ok = isinstance(enr.get("orphanet"), dict) and bool(enr["orphanet"].get("definition"))
    r.append(check("get_disease_info + enrichment",
                   info.get("name") == "Marfan syndrome" and "FBN1" in genes and orpha_ok,
                   f"genes={info.get('causal_genes')}, sources={info.get('sources')}, "
                   f"patient_info={'yes' if enr.get('patient_info') else 'no'}"))

    # 4b) Orphanet redundancy: force the primary API to fail; OLS/ORDO must fill the definition.
    class _BoomOrphanet:
        def get_clinical_entity(self, code):
            raise UpstreamUnavailable("forced failure (fallback regression test)")

    fb_info = _get_disease_info(server.monarch, "MONDO:0019759", orphanet=_BoomOrphanet(),
                                medlineplus=None, omim=None, ols=server.ols)
    fb = fb_info.get("enrichment", {}).get("orphanet", {})
    r.append(check("orphanet fallback -> OLS/ORDO",
                   bool(fb.get("definition")) and fb.get("source") == "EBI OLS (ORDO)",
                   f"source={fb.get('source')}, term={fb.get('preferred_term')}"))

    # 5) Gene -> ClinVar variants (the disease->gene->variant chain).
    var = _find_variants(server.ncbi, "FBN1", "pathogenic", 5)
    vs = var.get("variants", [])
    r.append(check("find_genetic_variants (ClinVar)",
                   bool(vs) and bool(vs[0].get("clinical_significance")),
                   f"{var.get('total_matches')} matches; e.g. [{vs[0]['clinical_significance']}] {vs[0]['name'][:46]}" if vs else "none"))

    # 6) Europe PMC literature search.
    epmc = server.europepmc.search("Marfan syndrome FBN1", page_size=3)
    epmc_n = len((epmc.get("resultList") or {}).get("result", []))
    r.append(check("europe pmc search", epmc_n > 0 and int(epmc.get("hitCount", 0)) > 0,
                   f"{epmc_n} results, hitCount {epmc.get('hitCount')}"))

    # 7) ClinicalTrials.gov v2 search.
    tr = server.trials.search(condition="Marfan syndrome", page_size=3)
    studies = tr.get("studies", [])
    nct = studies[0]["protocolSection"]["identificationModule"].get("nctId") if studies else None
    r.append(check("clinical trials search (v2)", len(studies) > 0, f"{len(studies)} studies; e.g. {nct}"))

    # 8) PubMed search still works through the generalized NCBI client.
    pm = server.ncbi.search("pubmed", "Marfan syndrome FBN1", retmax=3)
    r.append(check("pubmed search (ncbi db=)", bool(pm["ids"]) and pm["total_count"] > 0,
                   f"{len(pm['ids'])} ids, total {pm['total_count']}"))

    print()
    passed = sum(r)
    print(f"{passed}/{len(r)} checks passed" + ("" if server.omim else "  (OMIM enrichment skipped — no OMIM_API_KEY)"))
    return 0 if passed == len(r) else 1


if __name__ == "__main__":
    sys.exit(main())

# Biomed MCP — Build TODO

**Goal:** grow this PubMed server into a multi-source **rare & genetic disease** MCP whose
headline capability is **symptom → candidate-illness** lookup. Personal/academic use.
**Architecture:** modular monolith — one server, one client module per source, few task-shaped tools.
**Blueprint:** BioMCP (genomoncology/biomcp, MIT). Full source stack saved in project memory.

> **Status:** Phase 0–3 complete and verified (`test_smoke.py` → 8/8, live APIs). 10 tools across 8 sources. OMIM is optional (needs an academic key). Remaining ideas under "Later".

### Verified API contracts (probed live this session)
- **HPO autocomplete:** `GET clinicaltables.nlm.nih.gov/api/hpo/v3/search?terms=&maxList=` → `[n,[codes],null,[[code,label]]]`
- **Monarch search:** `GET api-v3.monarchinitiative.org/v3/api/search?q=&category=biolink:Disease` → `{items:[{id,name,…}]}`
- **Monarch semsim:** `POST /v3/api/semsim/search {termset:[HP:…],group:"Human Diseases",metric,limit}` → `[{subject:{id,name,xref,…},score}]`
- **Monarch entity:** `GET /v3/api/entity/{MONDO:id}` → `{name,description,inheritance,causal_gene,mappings,has_phenotype_label,…}`
- **NCBI E-utils:** `eutils.ncbi.nlm.nih.gov/entrez/eutils` — ONE shared rate limit (10/s key, 3/s none) across every `db=`

---

## Phase 0 — Refactor for growth ✅
- [x] `clients/` package with `base.py` (shared HTTP session + per-client rate limiting + retry)
- [x] Generalize `pubmed_client.py` → `clients/ncbi_client.py` (`db=` param; one shared limiter) — unlocks ClinVar/Gene/MeSH (verified)
- [x] `tools/` package; move PubMed tools to `tools/literature.py` (behavior unchanged)
- [x] Rewire `server.py` to build shared clients + register tool modules
- [x] Smoke test: server imports, 7 tools register, PubMed search + efetch still work

## Phase 1 — Symptom → disease core (headline capability) ✅
- [x] `clients/hpo_client.py` — free-text symptom → `HP:` code (autocomplete)
- [x] `clients/monarch_client.py` — `search` / `semsim_search` / `get_entity`
- [x] Tool `lookup_hpo_terms(symptoms)` — transparent symptom→HPO mapping
- [x] Tool `find_conditions_by_symptoms(symptoms, max_results)` — HPO → Monarch semsim → ranked MONDO diseases + provenance
- [x] Tool `get_disease_info(disease_id)` — Monarch entity → curated disease card (desc, inheritance, genes, xrefs incl. OMIM/Orphanet)
- [x] Smoke test: Marfan phenotypes rank Marfan-spectrum; `get_disease_info(MONDO:0007947)` → FBN1, AD inheritance, OMIM:154700

## Phase 2 — Enrich genetics ✅
- [x] `clients/orphanet_client.py` (api.orphacode.org) + `clients/medlineplus_client.py` + `clients/omim_client.py` (optional, academic key)
- [x] Tool `find_genetic_variants` (ClinVar) — completes symptom→disease→gene→variant chain (genes come from `get_disease_info.causal_genes`)
- [x] Merge Orphanet + MedlinePlus (+ OMIM if key) into `get_disease_info` enrichment — verified: Marfan → Orphanet definition + MedlinePlus patient info

## Phase 3 — Evidence + breadth ✅
- [x] `clients/europepmc_client.py` (`search_literature`) + `clients/clinicaltrials_client.py` v2 (`search_clinical_trials`)
- [~] Optional ICD-11 codes — deferred (not needed for current scope; see Later)

## Cross-cutting
- [x] Update README (scope, new tools, config)
- [~] Keep total tool count lean (~≤10) — now at **10/~10**; future additions must consolidate or move to on-demand tool loading, not add a flat 11th tool

## Later (optional, not blocking)
- [ ] Add an OMIM API key (`OMIM_API_KEY`) to activate OMIM enrichment in `get_disease_info`
- [ ] Orphanet/HOOM phenotype associations beyond the code lookup (bulk Orphadata)
- [ ] ICD-11 (WHO) structured codes; UMLS CUI normalization
- [ ] Rename repo dir `pubmed-mcp` → `biomed-mcp` (cosmetic; server already self-IDs as "biomed")

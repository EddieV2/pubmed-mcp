"""Biomed MCP Server.

Biomedical research + rare/genetic **symptom → candidate-illness** lookup over the
Model Context Protocol. Sources: NCBI E-utilities (PubMed, ClinVar, ...), the Monarch
Initiative knowledge graph, the Human Phenotype Ontology, Orphanet, MedlinePlus,
Europe PMC, ClinicalTrials.gov, and (optionally) OMIM.

Architecture: a modular monolith — one server, one client module per source
(``clients/``), and a small set of task-oriented tools grouped by capability (``tools/``).
See TODO.md for the roadmap.
"""

import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from clients.clinicaltrials_client import ClinicalTrialsClient
from clients.europepmc_client import EuropePMCClient
from clients.hpo_client import HPOClient
from clients.medlineplus_client import MedlinePlusClient
from clients.monarch_client import MonarchClient
from clients.ncbi_client import NCBIClient
from clients.ols_client import OLSClient
from clients.omim_client import OMIMClient
from clients.orphanet_client import OrphanetClient
from tools import conditions, evidence, genetics, literature

# Load environment variables (NCBI_API_KEY, NCBI_EMAIL, OMIM_API_KEY — all optional).
load_dotenv()

mcp = FastMCP("biomed")

# Shared clients. One NCBIClient instance => one shared E-utilities rate limiter across
# every Entrez database (PubMed, ClinVar, ...). Monarch/HPO/Orphanet/MedlinePlus/EuropePMC/
# ClinicalTrials need no credentials.
ncbi = NCBIClient(api_key=os.getenv("NCBI_API_KEY"), email=os.getenv("NCBI_EMAIL"))
monarch = MonarchClient()
hpo = HPOClient()
orphanet = OrphanetClient()
ols = OLSClient()
medlineplus = MedlinePlusClient()
europepmc = EuropePMCClient()
trials = ClinicalTrialsClient()

# OMIM is optional and academic-only — wired in only when a key is configured.
_omim_key = os.getenv("OMIM_API_KEY")
omim = OMIMClient(api_key=_omim_key) if _omim_key else None

# Register capability modules (task-oriented tools grouped by capability).
literature.register(mcp, ncbi)                  # search_articles, download_article(s), get_article_summaries
evidence.register(mcp, europepmc, trials)       # search_literature, search_clinical_trials
genetics.register(mcp, ncbi)                    # find_genetic_variants
conditions.register(mcp, monarch, hpo, orphanet, medlineplus, omim, ols)  # lookup_hpo_terms, find_conditions_by_symptoms, get_disease_info


if __name__ == "__main__":
    mcp.run()

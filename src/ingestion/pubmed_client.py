# src/ingestion/pubmed_client.py

import requests
import xml.etree.ElementTree as ET


class PubMedClient:
    """Cliente para la API E-utilities de PubMed."""

    BASE_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    BASE_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def search_papers(self, query: str, max_results: int = 10) -> list[dict]:
        """Busca papers en PubMed y devuelve metadatos básicos."""

        # 1. Obtener PMIDs
        resp = requests.get(self.BASE_SEARCH, params={
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
        }, timeout=15)
        resp.raise_for_status()
        pmids = resp.json().get("esearchresult", {}).get("idlist", [])
        if not pmids:
            return []

        # 2. Obtener detalles
        resp = requests.get(self.BASE_FETCH, params={
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        }, timeout=15)
        resp.raise_for_status()

        return self._parse_xml(resp.text)

    def _parse_xml(self, xml_text: str) -> list[dict]:
        root = ET.fromstring(xml_text)
        papers = []

        for article in root.findall(".//PubmedArticle"):
            pmid = article.findtext(".//PMID", default="")

            title_el = article.find(".//ArticleTitle")
            title = "".join(title_el.itertext()) if title_el is not None else ""

            abstract_el = article.find(".//Abstract")
            abstract = "".join(abstract_el.itertext()) if abstract_el is not None else ""

            journal = article.findtext(".//Journal/Title", default="")

            year_el = article.find(".//PubDate/Year")
            if year_el is None:
                medline = article.findtext(".//PubDate/MedlineDate", default="")
                year = medline[:4] if medline else ""
            else:
                year = year_el.text or ""

            papers.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "journal": journal,
                "year": year,
            })

        return papers


if __name__ == "__main__":
    client = PubMedClient()
    results = client.search_papers("Olaparib breast cancer", max_results=3)
    for p in results:
        print(f"[{p['pmid']}] {p['title']} ({p['year']}, {p['journal']})")
        print(f"  Abstract: {p['abstract'][:120]}...\n")
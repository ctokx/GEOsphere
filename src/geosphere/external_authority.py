from __future__ import annotations

from urllib.parse import quote_plus, urlparse

import requests


def verify_entity_presence(brand_name: str, domain: str, social_links: dict[str, list[str]], timeout: int, user_agent: str) -> dict:
    headers = {"User-Agent": user_agent}
    report = {
        "wikipedia": {"present": False, "title": "", "results": 0, "error": ""},
        "wikidata": {"present": False, "id": "", "description": "", "results": 0, "error": ""},
        "github": {"present": False, "profile": "", "followers": None, "public_repos": None, "error": ""},
        "hackernews": {"mentions": 0, "error": ""},
        "reddit": {"mentions": 0, "error": ""},
        "orcid": {"present": False},
        "linkedin": {"present": bool(social_links.get("linkedin")), "profiles": social_links.get("linkedin", [])},
        "youtube": {"present": bool(social_links.get("youtube")), "profiles": social_links.get("youtube", [])},
        "github_links": social_links.get("github", []),
    }
    try:
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(brand_name)}&format=json"
        wiki_response = requests.get(wiki_url, timeout=timeout, headers=headers)
        if wiki_response.status_code == 200:
            payload = wiki_response.json()
            results = payload.get("query", {}).get("search", [])
            report["wikipedia"]["results"] = len(results)
            if results:
                title = results[0].get("title", "")
                report["wikipedia"]["title"] = title
                report["wikipedia"]["present"] = brand_name.lower() in title.lower()
    except Exception as exc:
        report["wikipedia"]["error"] = str(exc)
    try:
        wikidata_url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={quote_plus(brand_name)}&language=en&format=json"
        wikidata_response = requests.get(wikidata_url, timeout=timeout, headers=headers)
        if wikidata_response.status_code == 200:
            payload = wikidata_response.json()
            results = payload.get("search", [])
            report["wikidata"]["results"] = len(results)
            if results:
                top = results[0]
                report["wikidata"]["present"] = True
                report["wikidata"]["id"] = top.get("id", "")
                report["wikidata"]["description"] = top.get("description", "")
    except Exception as exc:
        report["wikidata"]["error"] = str(exc)
    github_profile = social_links.get("github", [""])
    github_profile = github_profile[0] if github_profile else ""
    if github_profile:
        report["github"]["profile"] = github_profile
        path = urlparse(github_profile).path.strip("/").split("/")
        if path and path[0]:
            try:
                api_url = f"https://api.github.com/users/{path[0]}"
                github_response = requests.get(api_url, timeout=timeout, headers=headers)
                if github_response.status_code == 200:
                    payload = github_response.json()
                    report["github"]["present"] = True
                    report["github"]["followers"] = payload.get("followers")
                    report["github"]["public_repos"] = payload.get("public_repos")
            except Exception as exc:
                report["github"]["error"] = str(exc)
    try:
        hn_url = f"https://hn.algolia.com/api/v1/search?query={quote_plus(domain)}"
        hn_response = requests.get(hn_url, timeout=timeout, headers=headers)
        if hn_response.status_code == 200:
            payload = hn_response.json()
            report["hackernews"]["mentions"] = int(payload.get("nbHits", 0))
    except Exception as exc:
        report["hackernews"]["error"] = str(exc)
    try:
        reddit_url = f"https://www.reddit.com/search.json?q={quote_plus(domain)}&limit=5&sort=relevance"
        reddit_response = requests.get(reddit_url, timeout=timeout, headers=headers)
        if reddit_response.status_code == 200:
            payload = reddit_response.json()
            report["reddit"]["mentions"] = len(payload.get("data", {}).get("children", []))
    except Exception as exc:
        report["reddit"]["error"] = str(exc)
    report["orcid"]["present"] = any("orcid.org" in item for item in social_links.get("x", []) + social_links.get("linkedin", []) + social_links.get("github", []))
    report["direct_profile_count"] = sum(len(value) for value in social_links.values())
    report["has_independent_anchor"] = report["wikipedia"]["present"] or report["wikidata"]["present"] or report["hackernews"]["mentions"] > 0 or report["reddit"]["mentions"] > 0
    report["domain"] = domain
    return report

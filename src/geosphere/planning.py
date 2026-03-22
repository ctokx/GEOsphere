from __future__ import annotations

from geosphere.contracts import ModuleScore


def build_action_plan(modules: list[ModuleScore]) -> dict:
    quick_wins: list[dict[str, str]] = []
    medium_term: list[dict[str, str]] = []
    strategic: list[dict[str, str]] = []
    seen: set[str] = set()
    for module in sorted(modules, key=lambda item: item.score):
        for finding in module.findings:
            severity = finding.get("severity", "medium")
            title = finding.get("title", "")
            detail = finding.get("detail", "")
            recommendation = _match_recommendation(module.recommendations, title)
            action = recommendation or f"Resolve {title.lower()}."
            if action in seen:
                continue
            seen.add(action)
            item = {
                "module": module.name,
                "severity": severity,
                "title": title,
                "action": action,
                "reason": detail,
            }
            if severity in {"critical", "high"}:
                quick_wins.append(item)
            elif severity == "medium":
                medium_term.append(item)
            else:
                strategic.append(item)
        for recommendation in module.recommendations:
            if recommendation in seen:
                continue
            seen.add(recommendation)
            target = strategic if module.name in {"entity", "platforms"} else medium_term
            target.append(
                {
                    "module": module.name,
                    "severity": "planned",
                    "title": f"{module.name.title()} improvement",
                    "action": recommendation,
                    "reason": f"Lift the {module.name} score beyond {module.score}/100.",
                }
            )
    return {
        "quick_wins": quick_wins[:8],
        "medium_term": medium_term[:10],
        "strategic": strategic[:10],
    }


def _match_recommendation(recommendations: list[str], title: str) -> str:
    title_words = {item.lower() for item in title.split() if len(item) > 3}
    best = ""
    best_score = 0
    for recommendation in recommendations:
        score = sum(1 for word in title_words if word in recommendation.lower())
        if score > best_score:
            best = recommendation
            best_score = score
    return best

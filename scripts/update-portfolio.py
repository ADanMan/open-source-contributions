"""Refresh public PRs for the portfolio owner using the authenticated GitHub CLI."""
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHOR = "ADanMan"


def refresh():
    raw = subprocess.check_output([
        "gh", "api", "--paginate", "--slurp", "-X", "GET", "search/issues",
        "-f", f"q=author:{AUTHOR} is:pr is:public", "-f", "per_page=100",
    ])
    pages = json.loads(raw)
    groups = defaultdict(list)
    seen = set()
    for page in pages:
        if page["incomplete_results"]:
            raise RuntimeError("Incomplete GitHub search")
        for pr in page["items"]:
            url = pr["html_url"]
            if pr["user"]["login"].casefold() != AUTHOR.casefold() or url in seen:
                raise RuntimeError("Unexpected author or duplicate PR")
            seen.add(url)
            repo = pr["repository_url"].split("/repos/")[1]
            state = ("принят" if pr["pull_request"]["merged_at"] else
                     "закрыт без merge" if pr["state"] == "closed" else
                     "черновик" if pr.get("draft") else "открыт")
            title = " ".join(pr["title"].split()).replace("[", "［").replace("]", "］")
            groups[repo].append((pr["number"], f"- [#{pr['number']} {title}]({url}) · {state}"))
    if len(seen) != pages[0]["total_count"]:
        raise RuntimeError("Partial search result; keeping previous snapshot")
    date = datetime.now(timezone.utc).date().isoformat()
    lines = ["# Публичные pull requests", "", f"Автор @{AUTHOR}. На {date} в поиске GitHub — {len(seen)} PR.", ""]
    for owned, heading in [(False, "Внешние проекты"), (True, "Личные репозитории")]:
        lines.extend([f"## {heading}", ""])
        for repo in sorted(groups, key=str.casefold):
            if (repo.split("/")[0].casefold() == AUTHOR.casefold()) == owned:
                lines.extend([f"### {repo}", ""])
                lines.extend(line for _, line in sorted(groups[repo], reverse=True))
                lines.append("")
    (ROOT / "pull-requests.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    refresh()

#!/usr/bin/env python3
"""Refresh the 'recent open source contributions' list in README.md.

Lists your latest pull requests to repositories you don't own:
merged ones and open ones still in review. Closed-unmerged PRs are skipped.
No dependencies beyond the Python standard library.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime

USER = os.environ.get("GH_USER", "florianpunz")
LIMIT = int(os.environ.get("LIMIT", "5"))
README = os.environ.get("README", "README.md")
START, END = "<!-- contributions:start -->", "<!-- contributions:end -->"


def fetch_prs():
    query = f"is:pr is:public author:{USER} -user:{USER}"
    url = "https://api.github.com/search/issues?" + urllib.parse.urlencode(
        {"q": query, "sort": "created", "order": "desc", "per_page": 50}
    )
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["items"]


def md_escape(text):
    return re.sub(r"([\[\]])", r"\\\1", text)


def fmt_date(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%b %Y")


def render(items):
    lines = []
    for pr in items:
        merged_at = (pr.get("pull_request") or {}).get("merged_at")
        if merged_at:
            status = f"merged {fmt_date(merged_at)}"
        elif pr["state"] == "open" and not pr.get("draft"):
            status = "in review"
        else:
            continue  # closed without merge, or draft
        repo = pr["repository_url"].split("/repos/", 1)[1]
        lines.append(
            f"- [{repo}](https://github.com/{repo}) · "
            f"[{md_escape(pr['title'])}]({pr['html_url']}) · {status}"
        )
        if len(lines) >= LIMIT:
            break
    return "\n".join(lines) or "_Nothing public yet._"


def main():
    with open(README, encoding="utf-8") as f:
        readme = f.read()
    block = f"{START}\n{render(fetch_prs())}\n{END}"
    updated = re.sub(
        re.escape(START) + r".*?" + re.escape(END), lambda _: block, readme, flags=re.S
    )
    if updated != readme:
        with open(README, "w", encoding="utf-8") as f:
            f.write(updated)
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()

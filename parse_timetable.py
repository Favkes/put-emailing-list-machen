from __future__ import annotations

from bs4 import BeautifulSoup
from pathlib import Path
from pprint import pprint

from urllib.parse import unquote
import re


def parse_plan(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    result = []

    for entry in soup.select("timetable-entry"):
        subject = entry.get("name", "").strip()

        type_link = entry.select_one('[slot="dialog-info"] a')
        class_type = type_link.get_text(" ", strip=True) if type_link else None

        lecturers = []

        for person_link in entry.select('[slot="dialog-person"] a[href]'):
            lecturers.append(
                {
                    "name": person_link.get_text(" ", strip=True),
                    "url": person_link["href"],
                }
            )

        result.append(
            {
                "subject": subject,
                "class_type": class_type,
                "lecturers": lecturers,
            }
        )

    return result


def parse_lecturer_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title = None
    email = None

    # Stopnie i tytuły
    attrs_panel = soup.select_one("#user-attrs-id")

    if attrs_panel:
        for row in attrs_panel.select(".uwb-clearfix"):
            cells = row.find_all("div", recursive=False)

            if len(cells) < 2:
                continue

            label = cells[0].get_text(" ", strip=True)
            value = cells[1].get_text(" ", strip=True)

            if label == "Stopnie i tytuły":
                title = value
                break

    # E-mail — najpierw próbujemy zwykłego mailto:
    email_link = soup.select_one('#plaintext_email a[href^="mailto:"]')

    if email_link:
        email = email_link["href"].removeprefix("mailto:").strip()

    # Fallback, gdyby link nie był widoczny w HTML-u i został tylko skrypt
    if not email:
        script = soup.select_one("#plaintext_email script")

        if script:
            decoded = unquote(script.get_text())

            match = re.search(r'mailto:([^"\']+)', decoded)

            if match:
                email = match.group(1).strip()

    return {
        "title": title,
        "email": email,
    }



if __name__=="__main__":
    html = Path("plan.html").read_text(encoding="utf-8")
    items = parse_plan(html)

    pprint(items)

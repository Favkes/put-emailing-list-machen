from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from parse_timetable import parse_plan, parse_lecturer_page
from pprint import pprint

import csv


load_dotenv()


PLAN_URL = (
    "https://usosweb.put.poznan.pl/kontroler.php"
    "?_action=home/plan"
    "&plan_week_sel_week=2026-10-05"
    "&plan_division=week"
)

OUTPUT_FILE = Path("plan.html")
DEBUG_FILE = Path("login-result.html")

CLASS_TYPE_SHORTS = {
    "Laboratorium": "LAB",
    "Wykład": "WYKŁ",
    "Ćwiczenia": "ĆW",
    "Projekt": "PROJ"
}


def get_semester_code():
    code = os.getenv("SEMESTER_CODE")
    if not code:
        code = input("Semester code: ").strip()
    return code


def create_contact(name, surname, title, email, notes, category_tag) -> dict:
    return {
        "FirstName": name,
        "LastName": surname,
        "JobTitle": title,
        "EmailAddress": email,
        "Notes": notes,
        "Categories": category_tag
    }


def save_contact_list(contacts:list[dict]):
    with open("contects-generated.csv", "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=[
                "FirstName",
                "LastName",
                "JobTitle",
                "EmailAddress",
                "Notes",
                "Categories"
            ]
        )
        writer.writeheader()
        writer.writerows(contacts)


def remove_gateway(url: str) -> str:
    parts = urlsplit(url)

    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != "gateway"
    ]

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )


def get_credentials() -> tuple[str, str]:
    username = os.getenv("PUT_USERNAME")
    password = os.getenv("PUT_PASSWORD")

    if not username:
        username = input("E-mail PUT: ").strip()

    if not password:
        password = getpass.getpass("Hasło PUT: ")

    if not username or not password:
        raise RuntimeError("Nie podano loginu lub hasła.")

    return username, password


def print_history(response: requests.Response) -> None:
    print("\nHistoria przekierowań:")

    if not response.history:
        print("  brak")

    for item in response.history:
        location = item.headers.get("location")
        print(f"  {item.status_code} {item.url}")
        if location:
            print(f"      -> {location}")

    print(f"  {response.status_code} {response.url}")


def contains_login_form(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")

    return (
        soup.find("input", {"name": "login"}) is not None
        and soup.find("input", {"name": "password"}) is not None
    )


def page_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    return "(brak tytułu)"


def main() -> int:
    login, password = get_credentials()

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/139.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.7,en;q=0.6",
        }
    )

    # 1. Pobieramy przekierowanie z USOS-a do eLogin.
    first_response = session.get(
        PLAN_URL,
        timeout=30,
        allow_redirects=False,
    )
    first_response.raise_for_status()

    login_url = first_response.headers.get("location")

    if not login_url:
        raise RuntimeError(
            "USOS nie przekierował do eLogin. "
            f"Status: {first_response.status_code}"
        )

    # gateway=true tylko sprawdza istniejącą sesję i nie pokazuje formularza.
    login_url = remove_gateway(login_url)

    # 2. Pobieramy formularz logowania i token CSRF.
    form_response = session.get(
        login_url,
        timeout=30,
        allow_redirects=True,
        headers={
            "Referer": PLAN_URL,
        },
    )
    form_response.raise_for_status()

    print("Formularz logowania:")
    print("  URL:", form_response.url)
    print("  tytuł:", page_title(form_response.text))

    soup = BeautifulSoup(form_response.text, "html.parser")
    form = soup.find("form")

    if form is None:
        raise RuntimeError("Nie znaleziono formularza logowania.")

    csrf_input = form.find("input", {"name": "csrf_token"})

    if csrf_input is None or not csrf_input.get("value"):
        raise RuntimeError("Nie znaleziono tokenu CSRF.")

    csrf_token = csrf_input["value"]

    form_action = form.get("action")

    if form_action:
        submit_url = urljoin(form_response.url, form_action)
    else:
        submit_url = form_response.url

    payload = {
        "csrf_token": csrf_token,
        "login": login,
        "password": password,
        "send": ""
    }

    # 3. Wysyłamy formularz. Ta operacja powinna przejść przez CAS
    # i wrócić do USOS-a z ticketem.
    login_response = session.post(
        submit_url,
        data=payload,
        timeout=30,
        allow_redirects=True,
        headers={
            "Referer": form_response.url,
            "Origin": "https://elogin.put.poznan.pl",
        },
    )

    print_history(login_response)

    DEBUG_FILE.write_text(login_response.text, encoding="utf-8")

    result_soup = BeautifulSoup(login_response.text, "html.parser")

    print("\nKomunikaty ze strony:")

    found_message = False

    selectors = (
        ".alert",
        ".error",
        ".errors",
        ".message",
        ".notification",
        ".flash",
        "[role='alert']",
        ".form-error",
        ".invalid-feedback",
    )

    for selector in selectors:
        for element in result_soup.select(selector):
            text = element.get_text(" ", strip=True)

            if text:
                print(f"  [{selector}] {text}")
                found_message = True

    if not found_message:
        print("  Nie znaleziono komunikatu przez typowe selektory.")

    print("\nTekst formularza:")
    result_form = result_soup.find("form")

    if result_form:
        print(result_form.get_text(" ", strip=True))
    else:
        print("  Brak formularza.")

    print("\nPo logowaniu:")
    print("  status:", login_response.status_code)
    print("  URL:", login_response.url)
    print("  tytuł:", page_title(login_response.text))

    if contains_login_form(login_response.text):
        print(
            "\nNadal otrzymaliśmy formularz logowania. "
            "Najprawdopodobniej login lub hasło są niepoprawne."
        )
        print(f"Odpowiedź zapisana do: {DEBUG_FILE.resolve()}")
        return 1

    # 4. Pobieramy plan jeszcze raz z uwierzytelnioną sesją.
    plan_response = session.get(
        PLAN_URL,
        timeout=30,
        allow_redirects=True,
        headers={
            "Referer": login_response.url,
        },
    )

    print_history(plan_response)

    print("\nPobieranie planu:")
    print("  status:", plan_response.status_code)
    print("  URL:", plan_response.url)
    print("  tytuł:", page_title(plan_response.text))

    OUTPUT_FILE.write_text(plan_response.text, encoding="utf-8")

    if plan_response.status_code == 403:
        print("\nUSOS nadal zwraca 403 — sesja nie została uwierzytelniona.")
        print(f"Odpowiedź zapisana do: {OUTPUT_FILE.resolve()}")
        return 1

    plan_response.raise_for_status()

    if contains_login_form(plan_response.text):
        print("\nZamiast planu ponownie otrzymaliśmy formularz logowania.")
        return 1

    if "Wymagane zalogowanie" in plan_response.text:
        print("\nUSOS nadal uważa, że użytkownik nie jest zalogowany.")
        return 1

    print(f"\nGitara. HTML planu zapisany do: {OUTPUT_FILE.resolve()}")


    # ============================================================================

    print("\nRequesting each lecturer's details:")

    html = Path("plan.html").read_text(encoding="utf-8")
    items = parse_plan(html)

    # pprint(items)

    contacts = []
    semester_code = get_semester_code()

    for item in items:
        subject = item["subject"]
        class_type = item["class_type"]

        for lecturer in item["lecturers"]:
            lecturer_name:str = lecturer["name"]
            lecturer_url:str = lecturer["url"]

            try:
                response = session.get(
                    lecturer_url
                )

                lecturer_details = parse_lecturer_page(response.text)

                name, surname = lecturer_name.strip().split(' ')
                title = lecturer_details["title"]
                email = lecturer_details["email"]

                class_name = subject
                class_name_abbrev = ''.join(word[0].upper() for word in class_name.split(' '))

                class_type, *_ = class_type.split(',')
                class_type_short = CLASS_TYPE_SHORTS.get(class_type)

                notes = (f"{semester_code}\n"
                         f"{class_name} {class_name_abbrev}\n"
                         f"{class_type} {class_type_short}")

                contacts.append(create_contact(
                    name=name,
                    surname=surname,
                    title=title,
                    email=email,
                    notes=notes,
                    category_tag=semester_code
                ))

                print(title, name, surname, "✔️")
            except:
                print(lecturer_name, "✗")

    print("\nSaving all details to a CSV file...")
    save_contact_list(contacts)
    print("Contact list saved.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.RequestException as exc:
        print(f"\nBłąd HTTP: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        print(f"\nBłąd: {exc}", file=sys.stderr)
        raise SystemExit(1)
# EmailingListMachen

Small Python scraper for extracting lecturer information from PUT USOSweb and generating a CSV file suitable for contact import.

## Requirements

- Python 3.10+
- Access to PUT USOSweb
- Active eLogin credentials

## Installation

Clone the repository:

```bash
git clone <REPOSITORY_URL>
cd EmailingListMachen
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project directory:

```env
PUT_USERNAME=your.name@student.put.poznan.pl
PUT_PASSWORD=your_password
SEMESTER_CODE=your_semester_tag
```

Do not commit the `.env` file.

## Usage

Run:

```bash
python download_timetable.py
```

The script will:

- log into PUT USOSweb,
- download the timetable,
- extract subjects, class types and lecturer profile URLs,
- download lecturer details,
- extract lecturer titles and email addresses,
- generate a CSV contact list.

`parse_timetable.py` contains helper functions used to parse timetable and lecturer HTML pages. It can also be run separately for debugging or inspecting parsed timetable data.

## Output

The generated CSV file can be imported into a compatible contact manager, such as Zimbra.
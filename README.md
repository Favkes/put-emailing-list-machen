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

Activate it:

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
```

Do not commit the `.env` file.

## Usage

Run the scraper:

```bash
python main.py
```

The script logs into PUT USOSweb, reads timetable entries, extracts lecturer data, and generates a CSV file for contact import.
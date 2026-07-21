import pandas as pd
from models import Guest
from pathlib import Path


def load_guest_list(filename):

    filename = Path(filename)

    if filename.suffix.lower() == ".csv":
        df = pd.read_csv(filename)
    else:
        df = pd.read_excel(filename)

    guests = []

    for guest_id, (_, row) in enumerate(df.iterrows()):

        first = str(row["First Name"]).strip()
        last = str(row["Last Name"]).strip()

        family = row["Family"] if "Family" in df.columns else None
        side = row["Side"] if "Side" in df.columns else None

        guest = Guest(
            guest_id=guest_id,
            first_name=first,
            last_name=last,
            family=family,
            side=side
        )

        guests.append(guest)

    return guests
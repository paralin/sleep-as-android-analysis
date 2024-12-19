import pandas as pd
import json
from io import StringIO
from datetime import datetime
import pytz


def clean_sleep_data(input_file, output_file):
    # First, read the file as text to handle the varying number of columns
    with open(input_file, "r") as f:
        lines = f.readlines()

    # Initialize list to store cleaned records
    cleaned_records = []

    current_header = None
    current_data = None

    for line in lines:
        if line.startswith("Id,"):
            # This is a header line
            current_header = line.strip()
        elif line.strip() and not line.startswith(","):
            # This is a data line
            current_data = line.strip()

            if current_header and current_data:
                # Create a single-row DataFrame
                df = pd.read_csv(StringIO(current_header + "\n" + current_data))

                # Extract base data
                # Parse timezone
                tz = pytz.timezone(df["Tz"].iloc[0])
                pst = pytz.timezone("America/Los_Angeles")

                # Parse dates with timezone
                from_time = datetime.strptime(df["From"].iloc[0], "%d. %m. %Y %H:%M")
                from_time = tz.localize(from_time).astimezone(pst)

                to_time = datetime.strptime(df["To"].iloc[0], "%d. %m. %Y %H:%M")
                to_time = tz.localize(to_time).astimezone(pst)

                sched_time = datetime.strptime(df["Sched"].iloc[0], "%d. %m. %Y %H:%M")
                sched_time = tz.localize(sched_time).astimezone(pst)

                base_data = {
                    "id": df["Id"].iloc[0],
                    "from_time": from_time.isoformat(),
                    "to_time": to_time.isoformat(),
                    "scheduled_time": sched_time.isoformat(),
                    "hours": (
                        float(df["Hours"].iloc[0])
                        if pd.notnull(df["Hours"].iloc[0])
                        else None
                    ),
                    "rating": (
                        float(df["Rating"].iloc[0])
                        if pd.notnull(df["Rating"].iloc[0])
                        else None
                    ),
                    "cycles": (
                        float(df["Cycles"].iloc[0])
                        if pd.notnull(df["Cycles"].iloc[0])
                        else None
                    ),
                    "deep_sleep": (
                        float(df["DeepSleep"].iloc[0])
                        if pd.notnull(df["DeepSleep"].iloc[0])
                        else None
                    ),
                    "geo": df["Geo"].iloc[0],
                }

                # Extract time series data
                time_series = {}
                for col in df.columns:
                    if ":" in str(col):  # If column name contains time
                        if pd.notnull(df[col].iloc[0]):
                            time_series[col] = float(df[col].iloc[0])

                # Extract events
                events = []
                for col in df.columns:
                    if str(col).startswith("Event"):
                        if pd.notnull(df[col].iloc[0]):
                            # Split on hyphen to get event type and timestamp
                            event_str = str(df[col].iloc[0])
                            try:
                                event_type, timestamp = event_str.split("-", 1)
                                events.append(
                                    {"type": event_type, "timestamp": timestamp}
                                )
                            except ValueError:
                                print(f"Warning: Could not parse event: {event_str}")
                                continue

                # Combine all data
                record = {**base_data, "time_series": time_series, "events": events}

                cleaned_records.append(record)

    # Write to JSON file
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, "item"):
                return obj.item()
            return super().default(obj)

    with open(output_file, "w") as f:
        json.dump(cleaned_records, f, indent=2, cls=NumpyEncoder)


# Usage
clean_sleep_data("sleep-export.csv", "sleep-data-cleaned.json")

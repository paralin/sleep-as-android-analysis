# Sleep Data Format Documentation

This document describes the format of the sleep tracking data stored in `sleep-data-cleaned.json`.

## Data Structure

The JSON file contains an array of sleep records, where each record has the following fields:

### Core Fields

- `id` (number): Unique record identifier (timestamp of when the record began)
- `from_time` (string): Record beginning datetime in ISO 8601 format with timezone
- `to_time` (string): Record end datetime in ISO 8601 format with timezone 
- `scheduled_time` (string): Next scheduled sleep tracking terminating alarm in ISO 8601 format
- `hours` (number): Duration of the sleep record in hours
- `rating` (number): User rating from 0.0 to 5.0 in 0.25 increments
- `cycles` (number): Number of sleep cycles measured (-1 indicates manually inserted sleep record)
- `deep_sleep` (number): Deep sleep aggregated value (-2.0 or -1.0 indicates no hypnogram data available)
- `geo` (string|null): Hashed value of the geo location, or null if not available

### Time Series Data

The `time_series` object contains accelerometric (actigraphic) data aggregated into regular time intervals. The keys are timestamps in HH:mm format and values are numeric measurements from 0.0 to 10.0, where higher values indicate more movement.

### Events

The `events` array contains a chronological list of events that occurred during the sleep session. Each event has:

- `type` (string): The type of event, which can be one of:
  - Sleep stages: "LIGHT_START", "LIGHT_END", "DEEP_START", "DEEP_END", "REM_START", "REM_END"
  - Wake events: "AWAKE_START", "AWAKE_END"
  - Alarm events: "ALARM_EARLIEST", "ALARM_LATEST", "ALARM_STARTED", "ALARM_SNOOZE", "ALARM_DISMISS"
  - Sensor events: "LUX" (light level), "DHA" (device health/activity)
  - Other: "DEVICE", "TRACKING_STOPPED_BY_USER", "BROKEN_START", "BROKEN_END"
- `timestamp` (string): When the event occurred, with optional appended measurement value after a hyphen
  - For LUX events: Light level in lux units (e.g., "1731959588120-8.37375")
  - For DHA events: Device health metric (e.g., "1731959588120-4.5955263E-35")
  - For other events: Just the timestamp (e.g., "1731959588120")

## Sleep Stage Interpretation

The sleep record is divided into stages using pairs of START/END events:
- Light sleep: Period between LIGHT_START and LIGHT_END
- Deep sleep: Period between DEEP_START and DEEP_END  
- REM sleep: Period between REM_START and REM_END
- Awake: Period between AWAKE_START and AWAKE_END

## Example Record

```json
{
  "id": 1731959588120,
  "from_time": "2024-11-18T11:53:00-08:00", 
  "to_time": "2024-11-18T13:11:00-08:00",
  "scheduled_time": "2024-11-18T13:12:00-08:00",
  "hours": 1.31,
  "rating": 0.0,
  "cycles": 0.0,
  "deep_sleep": 0.0,
  "geo": null,
  "time_series": {
    "11:58": 10.0,
    "12:02": 10.0
  },
  "events": [
    {
      "type": "AWAKE_START",
      "timestamp": "1731959588120"
    }
  ]
}
```

## Analysis Output

The `step-2-analyze.py` script generates an interactive HTML report in the `./analysis` directory:

### Interactive HTML Report
The report (`index.html`) contains:

- Key metrics summary showing average sleep duration, deep sleep ratio, and interruption frequency
- Personalized recommendations based on sleep metrics compared to guidelines
- Interactive visualizations:
  - Sleep duration timeline with recommended range overlay
  - Sleep stage distribution pie chart (Deep, REM, Light sleep)
  - Weekly sleep pattern analysis
  - Sleep/wake time distribution patterns

The interactive visualizations help identify sleep patterns and trends, while the insights provide actionable recommendations based on sleep science standards and personal data.

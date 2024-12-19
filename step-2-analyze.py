"""Interactive sleep data analysis and visualization.

Generates a self-contained HTML report with interactive charts focused on key sleep insights.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import os
import click

# Suppress warnings
warnings.filterwarnings("ignore")

# Sleep guidelines from sleep science research
SLEEP_GUIDELINES = {
    "min_hours": 7.0,
    "max_hours": 9.0,
    "deep_sleep_ratio": 0.20,
    "rem_ratio": 0.25,
    "light_ratio": 0.55,
}


def load_sleep_data(filename: str, start_date: Optional[datetime] = None) -> List[Dict]:
    """Load and parse sleep records from JSON file."""
    with open(filename, "r") as f:
        records = json.load(f)

    if start_date:
        records = [
            r for r in records if datetime.fromisoformat(r["from_time"]) >= start_date
        ]

    return records


def create_analysis_dataframe(records: List[Dict]) -> pd.DataFrame:
    """Convert sleep records to pandas DataFrame with calculated metrics."""
    data = []

    for record in records:
        # Parse dates
        sleep_time = datetime.fromisoformat(record["from_time"])
        wake_time = datetime.fromisoformat(record["to_time"])

        # Calculate interruptions
        interruptions = []
        current_awake = None

        for event in record["events"]:
            if event["type"] == "AWAKE_START":
                current_awake = float(event["timestamp"].split("-")[0]) / 1000
            elif event["type"] == "AWAKE_END" and current_awake:
                end_time = float(event["timestamp"]) / 1000
                duration = (end_time - current_awake) / 60  # Minutes
                interruptions.append(duration)
                current_awake = None

        # Calculate REM time
        rem_events = [
            e for e in record["events"] if e["type"] in ["REM_START", "REM_END"]
        ]
        rem_time = 0
        for i in range(0, len(rem_events), 2):
            if i + 1 < len(rem_events):
                start = float(rem_events[i]["timestamp"].split("-")[0]) / 1000
                end = float(rem_events[i + 1]["timestamp"].split("-")[0]) / 1000
                rem_time += (end - start) / 3600  # Hours

        data.append(
            {
                "date": sleep_time.date(),
                "sleep_time": sleep_time.time(),
                "wake_time": wake_time.time(),
                "hours": record["hours"],
                "deep_sleep_hours": (
                    record["deep_sleep"] * record["hours"]
                    if record["deep_sleep"] >= 0
                    else None
                ),
                "rem_sleep_hours": rem_time,
                "light_sleep_hours": (
                    record["hours"]
                    - (record["deep_sleep"] * record["hours"])
                    - rem_time
                    if record["deep_sleep"] >= 0
                    else None
                ),
                "interruption_count": len(interruptions),
                "avg_interruption_mins": np.mean(interruptions) if interruptions else 0,
                "day_of_week": sleep_time.strftime("%A"),
                "is_weekend": sleep_time.weekday() >= 5,
            }
        )

    df = pd.DataFrame(data)
    df.set_index("date", inplace=True)
    return df


def create_html_report(df: pd.DataFrame, output_file: str):
    """Generate interactive HTML report with Plotly charts."""
    
    # Calculate sleep consistency
    consistency_fig = go.Figure()
    
    # Add sleep times
    consistency_fig.add_trace(
        go.Scatter(
            x=df.index,
            y=[t.hour + t.minute/60 for t in df["sleep_time"]],
            mode="markers+lines",
            name="Sleep Time",
            line=dict(color="#2E86C1"),
            hovertemplate="Sleep Time: %{text}<br>Date: %{x}",
            text=[t.strftime("%I:%M %p") for t in df["sleep_time"]]
        )
    )
    
    # Add wake times
    consistency_fig.add_trace(
        go.Scatter(
            x=df.index,
            y=[t.hour + t.minute/60 for t in df["wake_time"]],
            mode="markers+lines", 
            name="Wake Time",
            line=dict(color="#E74C3C"),
            hovertemplate="Wake Time: %{text}<br>Date: %{x}",
            text=[t.strftime("%I:%M %p") for t in df["wake_time"]]
        )
    )

    # Calculate standard deviations for sleep consistency score
    sleep_std = pd.Series([t.hour + t.minute/60 for t in df["sleep_time"]]).std()
    wake_std = pd.Series([t.hour + t.minute/60 for t in df["wake_time"]]).std()
    consistency_score = 100 * (1 - (sleep_std + wake_std)/(24))  # Higher score = more consistent

    consistency_fig.update_layout(
        title=f"Sleep Schedule Consistency (Score: {consistency_score:.1f}%)",
        yaxis=dict(
            title="Time of Day",
            tickmode="array",
            ticktext=[f"{i:02d}:00" for i in range(24)],
            tickvals=list(range(24))
        ),
        hovermode="x unified"
    )

    # 1. Sleep Duration Timeline
    duration_fig = go.Figure()

    # Add actual duration line
    duration_fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["hours"],
            mode="lines+markers",
            name="Sleep Duration",
            line=dict(color="#2E86C1"),
        )
    )

    # Add recommended range
    duration_fig.add_hrect(
        y0=SLEEP_GUIDELINES["min_hours"],
        y1=SLEEP_GUIDELINES["max_hours"],
        fillcolor="rgba(0,255,0,0.1)",
        line_width=0,
        name="Recommended Range",
    )

    duration_fig.update_layout(
        title="Sleep Duration Over Time",
        yaxis_title="Hours",
        hovermode="x unified",
        showlegend=True,
    )

    # 2. Sleep Stage Distribution
    stages_df = df[["deep_sleep_hours", "rem_sleep_hours", "light_sleep_hours"]].mean()
    stages_fig = go.Figure(
        data=[
            go.Pie(
                labels=["Deep Sleep", "REM Sleep", "Light Sleep"],
                values=stages_df.values,
                hole=0.4,
                marker_colors=["#2E86C1", "#E74C3C", "#27AE60"],
            )
        ]
    )

    stages_fig.update_layout(title="Average Sleep Stage Distribution")

    # 3. Weekly Pattern
    weekly_avg = df.groupby("day_of_week")["hours"].mean()
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    weekly_avg = weekly_avg.reindex(days)

    weekly_fig = go.Figure(
        data=[go.Bar(x=weekly_avg.index, y=weekly_avg.values, marker_color="#2E86C1")]
    )

    weekly_fig.update_layout(
        title="Average Sleep Duration by Day",
        yaxis_title="Hours",
        xaxis_title="Day of Week",
    )

    # 4. Sleep Time Distribution
    def time_to_hours(t):
        return t.hour + t.minute / 60

    timing_data = pd.DataFrame(
        {
            "Sleep Time": df["sleep_time"].apply(time_to_hours),
            "Wake Time": df["wake_time"].apply(time_to_hours),
        }
    )

    sleep_fig = go.Figure()
    sleep_fig.add_trace(
        go.Violin(
            y=timing_data["Sleep Time"],
            name="Sleep Time",
            line_color="#2E86C1",
        )
    )
    sleep_fig.update_layout(
        title="Sleep Time Distribution",
        yaxis_title="Hour of Day (24h)",
        yaxis=dict(tickmode="linear", tick0=0, dtick=2),
    )

    # 5. Wake Time Distribution
    wake_fig = go.Figure()
    wake_fig.add_trace(
        go.Violin(
            y=timing_data["Wake Time"],
            name="Wake Time",
            line_color="#E74C3C",
        )
    )
    wake_fig.update_layout(
        title="Wake Time Distribution",
        yaxis_title="Hour of Day (24h)",
        yaxis=dict(tickmode="linear", tick0=0, dtick=2),
    )

    # Generate HTML with insights
    avg_duration = df["hours"].mean()
    avg_deep = (
        df["deep_sleep_hours"].mean() / avg_duration
        if not df["deep_sleep_hours"].isna().all()
        else 0
    )
    avg_interruptions = df["interruption_count"].mean()

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sleep Analysis Report</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .chart-explanation {{
                background-color: #f8f9fa;
                padding: 15px;
                border-left: 4px solid #2E86C1;
                margin-bottom: 20px;
                border-radius: 4px;
            }}
            .chart-explanation p {{
                margin: 8px 0;
                line-height: 1.4;
            }}
            .insight-box {{
                background-color: white;
                padding: 20px;
                margin: 20px 0;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .chart-container {{
                background-color: white;
                padding: 20px;
                margin: 20px 0;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            h1, h2 {{
                color: #2C3E50;
            }}
            .metric {{
                font-size: 24px;
                font-weight: bold;
                color: #2E86C1;
            }}
            .recommendation {{
                color: #E74C3C;
            }}
        </style>
    </head>
    <body>
        <h1>Sleep Analysis Report</h1>
        
        <div class="insight-box">
            <h2>Key Metrics</h2>
            <p>Average Sleep Duration: <span class="metric">{avg_duration:.1f} hours</span>
               {" (Below recommended)" if avg_duration < 7 else " (Within recommended range)" if avg_duration <= 9 else " (Above recommended)"}
            </p>
            <p>Deep Sleep Ratio: <span class="metric">{avg_deep:.1%}</span>
               {" (Below optimal)" if avg_deep < 0.2 else " (Optimal)"}
            </p>
            <p>Average Interruptions: <span class="metric">{avg_interruptions:.1f}</span> per night
               {" (Higher than ideal)" if avg_interruptions > 2 else " (Normal range)"}
            </p>
        </div>

        <div class="insight-box">
            <h2>Recommendations</h2>
            {"<p class='recommendation'>Consider going to bed earlier to increase sleep duration</p>" if avg_duration < 7 else ""}
            {"<p class='recommendation'>Your deep sleep ratio is below optimal. Consider:</p><ul><li>Maintaining a cooler bedroom temperature</li><li>Avoiding screens before bedtime</li><li>Regular exercise (but not close to bedtime)</li></ul>" if avg_deep < 0.2 else ""}
            {"<p class='recommendation'>You're experiencing more interruptions than ideal. Try:</p><ul><li>Keeping your bedroom quiet and dark</li><li>Maintaining a comfortable temperature</li><li>Avoiding liquids close to bedtime</li></ul>" if avg_interruptions > 2 else ""}
        </div>

        <div class="chart-container">
            <div id="duration-chart"></div>
        </div>
        
        <div class="chart-container">
            <div id="stages-chart"></div>
        </div>
        
        <div class="chart-container">
            <div id="weekly-chart"></div>
        </div>
        
        <div class="chart-container">
            <div class="chart-explanation">
                <p>The Sleep Time Distribution chart shows when you typically fall asleep. The wider sections indicate more common bedtimes, while narrower sections show less frequent times.</p>
                <p>This visualization helps identify your natural sleep patterns and consistency in bedtime routines.</p>
            </div>
            <div id="sleep-chart"></div>
        </div>
        
        <div class="chart-container">
            <div class="chart-explanation">
                <p>The Sleep Schedule Consistency chart shows your sleep and wake times across days. More consistent times generally lead to better sleep quality.</p>
                <p>The consistency score considers how much your sleep and wake times vary - higher scores mean a more regular schedule.</p>
            </div>
            <div id="consistency-chart"></div>
        </div>

        <div class="chart-container">
            <div class="chart-explanation">
                <p>The Wake Time Distribution chart shows when you typically wake up. The wider sections indicate more common wake times, while narrower sections show less frequent times.</p>
                <p>This visualization helps identify your natural wake patterns and consistency in morning routines.</p>
            </div>
            <div id="wake-chart"></div>
        </div>

        <script>
            var durationData = {duration_fig.to_json()};
            Plotly.newPlot('duration-chart', durationData.data, durationData.layout);
            
            var stagesData = {stages_fig.to_json()};
            Plotly.newPlot('stages-chart', stagesData.data, stagesData.layout);
            
            var weeklyData = {weekly_fig.to_json()};
            Plotly.newPlot('weekly-chart', weeklyData.data, weeklyData.layout);
            
            var sleepData = {sleep_fig.to_json()};
            Plotly.newPlot('sleep-chart', sleepData.data, sleepData.layout);
            
            var wakeData = {wake_fig.to_json()};
            Plotly.newPlot('wake-chart', wakeData.data, wakeData.layout);
            
            var consistencyData = {consistency_fig.to_json()};
            Plotly.newPlot('consistency-chart', consistencyData.data, consistencyData.layout);
        </script>
    </body>
    </html>
    """

    with open(output_file, "w") as f:
        f.write(html_content)


@click.command()
@click.option(
    "--start-date",
    type=click.DateTime(),
    help="Analyze records from this date forward (YYYY-MM-DD)",
)
@click.option(
    "--input-file",
    default="sleep-data-cleaned.json",
    help="Input JSON file path",
)
@click.option(
    "--output-file",
    default="./analysis/index.html",
    help="Output HTML file path",
)
def main(start_date, input_file, output_file):
    """Analyze sleep data and generate interactive HTML report."""
    # Create analysis directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    print("Loading sleep data...")
    records = load_sleep_data(input_file, start_date)

    print("Analyzing sleep patterns...")
    df = create_analysis_dataframe(records)

    print("Generating interactive report...")
    create_html_report(df, output_file)

    print(f"\nAnalysis complete! Open {output_file} in your browser to view the report")


if __name__ == "__main__":
    main()

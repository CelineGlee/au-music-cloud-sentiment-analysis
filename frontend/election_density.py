import requests
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta

url = "https://localhost:9200/election-index/_search"  # HTTPS
auth = HTTPBasicAuth("elastic", "elastic")

# Elasticsearch
query = {
    "size": 0,  # Don't requite original posts
    "aggs": {
        "posts_over_time": {
            "date_histogram": {
                "field": "created_at",
                "calendar_interval": "day"
            }
        }
    }
}

response = requests.post(url, json=query, auth=auth, verify=False)  # verify=False to skip SSL

response.raise_for_status()

print(response.json())

buckets = response.json()["aggregations"]["posts_over_time"]["buckets"]

date_count_dict = {
    bucket["key_as_string"][:10]: bucket["doc_count"]
    for bucket in buckets
}

with open("election_date_count.json", "w") as outfile:
    json.dump(date_count_dict, outfile, indent=4)

print("Date: count saved into election_date_count.json.")

# Load date: count dictionary
try:
    with open("election_date_count.json", "r") as f:
        date_count = json.load(f)
except FileNotFoundError:
    print("Error: election_date_count.json not found. Using sample data.")
    date_count = {"2022-11-09": 10, "2022-11-10": 50, "2022-11-11": 200}

# Generate complete date sequence
start_date = datetime.strptime("2022-11-09", "%Y-%m-%d")
end_date = datetime.strptime("2025-05-06", "%Y-%m-%d")
all_dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d")
             for i in range((end_date - start_date).days + 1)]

# Convert to count list, missing dates get 0
count_list = [date_count.get(date, 0) for date in all_dates]

# Set grid parameters
row_length = 50
num_rows = (len(count_list) + row_length - 1) // row_length

# Pad data
padded_counts = count_list + [None] * (num_rows * row_length - len(count_list))
padded_dates = all_dates + [None] * (num_rows * row_length - len(all_dates))

# Convert to NumPy arrays
grid_counts = np.array(padded_counts).reshape((num_rows, row_length))
grid_dates = np.array(padded_dates).reshape((num_rows, row_length))

# Define color function
def get_color(value):
    if value is None:
        return "#ffffff"
    elif value == 0:
        return "#e0f7fa"     # very light blue
    elif 1 <= value <= 5:
        return "#90caf9"     # light blue
    elif 6 <= value <= 10:
        return "#64b5f6"     # blue
    elif 11 <= value <= 20:
        return "#9575cd"     # light purple
    elif 21 <= value <= 40:
        return "#ffb74d"     # light yellow
    elif 41 <= value <= 80:
        return "#ff8a65"     # orange pink
    elif 81 <= value <= 160:
        return "#f06292"     # pink
    else:  # >= 161
        return "#d32f2f"     # red

legend_labels = [
    ("0", "#e0f7fa"),
    ("1–5", "#90caf9"),
    ("6–10", "#64b5f6"),
    ("11–20", "#9575cd"),
    ("21–40", "#ffb74d"),
    ("41–80", "#ff8a65"),
    ("81–160", "#f06292"),
    ("161+", "#d32f2f"),
]

fig, ax = plt.subplots(figsize=(row_length * 0.25, num_rows * 0.25))

# Draw grid heatmap
for row in range(num_rows):
    for col in range(row_length):
        value = grid_counts[row, col]
        color = get_color(value)
        rect = plt.Rectangle((col, num_rows - 1 - row), 1, 1, facecolor=color, edgecolor="white", lw=0.5)
        ax.add_patch(rect)

# Set axis limits
ax.set_xlim(0, row_length)
ax.set_ylim(0, num_rows)

# Hide ticks
ax.set_xticks([])
ax.set_yticks([])

# Add legend
legend_handles = [mpatches.Patch(color=color, label=label) for label, color in legend_labels]
ax.legend(handles=legend_handles, loc="upper right", bbox_to_anchor=(1.05, 1), title="Count Range")

# Set equal aspect ratio
ax.set_aspect("equal")

plt.tight_layout()
plt.show()
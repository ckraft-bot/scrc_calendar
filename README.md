# scrc_calendar

Scenic City Run Club calendar app built with Streamlit.

This app displays running events on an interactive calendar, loads recurring and one-time events from dates.json, and lets users submit new events from a form.

## What it does

- Shows events by type with color coding:
	- Group Run (green)
	- Race (blue)
	- Other (red)
- Supports event type filters in the Calendar tab.
- Displays clickable event details (time, location, website link).
- Loads event data from dates.json:
	- recurring_events (DAILY, WEEKDAYS, WEEKLY, MONTHLY_FIRST)
	- one_time_events
- Includes admin-only delete actions in the sidebar after selecting an event.

## Run locally

```bash
pip install -r requirements.txt
streamlit run running_club_calendar.py
```
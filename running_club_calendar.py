"""
Running Club Calendar
----------------------
A Streamlit app that displays a color-coded calendar for a running club:
  - Group Runs -> Green
  - Races      -> Blue
  - Other      -> Red

Requires:
  pip install streamlit streamlit-calendar

Run with:
  streamlit run running_club_calendar.py
"""

import streamlit as st
from streamlit_calendar import calendar
from datetime import datetime, date, time, timedelta
from pathlib import Path
import json
import re
import uuid

st.set_page_config(page_title="Scenic City Run Crew Calendar", page_icon=":athletic_shoe:", layout="wide")

THEME_BACKGROUND = st.get_option("theme.backgroundColor") or "#FFFFFF"
THEME_SECONDARY_BACKGROUND = st.get_option("theme.secondaryBackgroundColor") or "#F5F5F5"
THEME_TEXT = st.get_option("theme.textColor") or "#000000"

# ---------------------------------------------------------------------------
# Config: event type -> color
# ---------------------------------------------------------------------------
EVENT_COLORS = {
    "Group Run": "#31C322",  # green
    "Race": "#3498db",       # blue
    "Other": "#e74c3c",      # red
}


def _get_admin_password():
    password = st.secrets.get("SCRC_ADMIN_PASSWORD", "")
    if not password:
        st.error("Missing SCRC_ADMIN_PASSWORD in Streamlit secrets.")
        st.stop()
    return str(password)


ADMIN_PASSWORD = _get_admin_password()

DATES_FILE = Path(__file__).with_name("dates.json")
RECURRING_LOOKAHEAD_DAYS = 180
DAY_TO_WEEKDAY = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}


def _strip_json_line_comments(text):
    # Support JSON files that include full-line // comments.
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


def _parse_time_value(value):
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except (TypeError, ValueError):
            continue
    return None


def _format_display_datetime(value):
    if not value:
        return ""

    parsed = None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        return value

    return parsed.strftime("%Y-%m-%d %I:%M %p").lower()


def _build_event(event_def, event_date):
    event_type = event_def.get("type", "Other")
    color = EVENT_COLORS.get(event_type, EVENT_COLORS["Other"])
    start_value = event_def.get("start_time")
    end_value = event_def.get("end_time")
    start_t = _parse_time_value(start_value) if start_value else None
    end_t = _parse_time_value(end_value) if end_value else None

    event = {
        "id": str(uuid.uuid4()),
        "title": event_def.get("title", event_def.get("name", "Untitled Event")),
        "type": event_type,
        "color": color,
        "location": event_def.get("location", ""),
        "website_link": event_def.get("website_link", ""),
        "notes": event_def.get("notes", ""),
    }

    if start_t:
        event["start"] = datetime.combine(event_date, start_t).isoformat()
    else:
        event["start"] = event_date.isoformat()
        event["allDay"] = True

    if end_t:
        event["end"] = datetime.combine(event_date, end_t).isoformat()

    return event


def _first_weekday_of_month(year, month, weekday):
    first = date(year, month, 1)
    shift = (weekday - first.weekday()) % 7
    return first + timedelta(days=shift)


def _generate_recurring_events(event_def, start_date, end_date):
    events = []
    frequency = str(event_def.get("frequency", "")).upper()
    weekday_name = str(event_def.get("day", "")).upper()
    weekday = DAY_TO_WEEKDAY.get(weekday_name)

    if frequency == "DAILY":
        current = start_date
        while current <= end_date:
            events.append(_build_event(event_def, current))
            current += timedelta(days=1)
        return events

    if frequency == "WEEKDAYS":
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                events.append(_build_event(event_def, current))
            current += timedelta(days=1)
        return events

    if frequency == "WEEKLY" and weekday is not None:
        days_ahead = (weekday - start_date.weekday()) % 7
        current = start_date + timedelta(days=days_ahead)
        while current <= end_date:
            events.append(_build_event(event_def, current))
            current += timedelta(days=7)
        return events

    if frequency == "MONTHLY_FIRST" and weekday is not None:
        year = start_date.year
        month = start_date.month
        while date(year, month, 1) <= end_date:
            candidate = _first_weekday_of_month(year, month, weekday)
            if start_date <= candidate <= end_date:
                events.append(_build_event(event_def, candidate))
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
        return events

    return events


def load_events_from_dates_json(file_path):
    if not file_path.exists():
        st.warning("dates.json not found. Starting with an empty calendar.")
        return []

    try:
        raw = file_path.read_text(encoding="utf-8")
        data = json.loads(_strip_json_line_comments(raw))
    except Exception as exc:
        st.error(f"Could not parse dates.json: {exc}")
        return []

    today = date.today()
    end_date = today + timedelta(days=RECURRING_LOOKAHEAD_DAYS)
    events = []

    for recurring in data.get("recurring_events", []):
        events.extend(_generate_recurring_events(recurring, today, end_date))

    for one_time in data.get("one_time_events", []):
        try:
            event_date = datetime.strptime(one_time["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        events.append(_build_event(one_time, event_date))

    events.sort(key=lambda event: event["start"])
    return events

# ---------------------------------------------------------------------------
# Session state: store events in memory (swap for a DB/file for persistence)
# ---------------------------------------------------------------------------
if "events" not in st.session_state:
    st.session_state.events = load_events_from_dates_json(DATES_FILE)

if "is_admin_verified" not in st.session_state:
    st.session_state.is_admin_verified = False

if "selected_event_id" not in st.session_state:
    st.session_state.selected_event_id = None

st.sidebar.divider()
st.sidebar.markdown("### Legend")
for label, color in EVENT_COLORS.items():
    st.sidebar.markdown(
        f"<span style='display:inline-block;width:12px;height:12px;"
        f"background-color:{color};border-radius:3px;margin-right:8px;'></span>{label}",
        unsafe_allow_html=True,
    )

st.sidebar.divider()
st.sidebar.markdown("### Admin")
st.sidebar.caption("Click an event on the calendar to select it for admin actions.")

selected_event = next(
    (event for event in st.session_state.events if event["id"] == st.session_state.selected_event_id),
    None,
)

if selected_event:
    st.sidebar.write(f"Selected: {selected_event['title']}")
    st.sidebar.write(f"Start: {_format_display_datetime(selected_event['start'])}")

    if not st.session_state.is_admin_verified:
        sidebar_admin_password = st.sidebar.text_input(
            "Admin password",
            type="password",
            key="sidebar_admin_password",
        )
        if st.sidebar.button("Verify Admin", key="sidebar_verify_admin", use_container_width=True):
            if sidebar_admin_password == ADMIN_PASSWORD:
                st.session_state.is_admin_verified = True
                st.sidebar.success("Admin verified.")
                st.rerun()
            else:
                st.sidebar.error("Incorrect admin password.")
    else:
        if st.sidebar.button("Delete Selected Event", key="sidebar_delete_event", use_container_width=True):
            st.session_state.events = [
                event for event in st.session_state.events if event["id"] != selected_event["id"]
            ]
            st.session_state.selected_event_id = None
            st.sidebar.success(f"Deleted '{selected_event['title']}'.")
            st.rerun()

        if st.sidebar.button("Logout Admin", key="sidebar_logout_admin", use_container_width=True):
            st.session_state.is_admin_verified = False
            st.sidebar.success("Admin logged out.")
            st.rerun()
else:
    st.sidebar.info("No event selected yet.")

st.sidebar.divider()
if st.sidebar.button("Reload Events From dates.json", use_container_width=True):
    st.session_state.events = load_events_from_dates_json(DATES_FILE)
    st.sidebar.success("Reloaded events from dates.json")
    st.rerun()

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title(":athletic_shoe: Scenic City Run Crew Calendar")
st.caption("Group runs in green, races in blue, everything else in red.")

tab_calendar, tab_submit = st.tabs(["Calendar", "Submit an Event"])

with tab_calendar:
    st.subheader("Filter Events")
    selected_types = st.multiselect(
        "Event types",
        options=list(EVENT_COLORS.keys()),
        default=list(EVENT_COLORS.keys()),
        help="Choose which event types to show in the calendar and list.",
    )

    filtered_events = [e for e in st.session_state.events if e["type"] in selected_types]

    if not selected_types:
        st.info("Select at least one event type to display events.")

    calendar_options = {
        "editable": True,
        "selectable": True,
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay,listMonth",
        },
        "height": 700,
    }

    # streamlit-calendar wants each event dict to include a "backgroundColor" /
    # "borderColor" key (it reads "color" too, but being explicit is safest).
    calendar_events = []
    for e in filtered_events:
        ev = dict(e)
        ev["backgroundColor"] = e["color"]
        ev["borderColor"] = e["color"]
        calendar_events.append(ev)

    state = calendar(
        events=calendar_events,
        options=calendar_options,
        key="running_calendar",
    )

    if state.get("eventClick"):
        clicked = state["eventClick"]["event"]
        st.session_state.selected_event_id = clicked.get("id")
        st.subheader(f"📌 {clicked['title']}")
        matching = next((e for e in filtered_events if e["id"] == clicked.get("id")), None)
        if matching:
            st.write(f"**Type:** {matching['type']}")
            st.write(f"**Start:** {_format_display_datetime(matching['start'])}")
            if matching.get("end"):
                st.write(f"**End:** {_format_display_datetime(matching['end'])}")
            if matching.get("location"):
                st.write(f"**Location:** {matching['location']}")
            if matching.get("website_link"):
                st.markdown(f"**Website:** [Event Link]({matching['website_link']})")
            if matching.get("notes"):
                st.write(f"**Notes:** {matching['notes']}")

    st.divider()
    with st.expander("Upcoming Events", expanded=False):
        sorted_events = sorted(filtered_events, key=lambda e: e["start"])
        if not sorted_events:
            st.write("No events match the selected event type filters.")

        for e in sorted_events:
            color = e["color"]
            start_label = _format_display_datetime(e["start"])
            end_label = _format_display_datetime(e.get("end")) if e.get("end") else ""
            when = f"{start_label} - {end_label}" if end_label else start_label
            st.markdown(
                f"""
                <div style="border-left: 5px solid {color}; padding: 6px 12px; margin-bottom: 6px; background-color: {THEME_SECONDARY_BACKGROUND}; border-radius: 4px;">
                    <strong>{e['title']}</strong> &mdash; {e['type']}<br>
                    <span style="color: {THEME_TEXT}; opacity: 0.65; font-size: 0.85em;">{when}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

with tab_submit:
    st.subheader("Event Intake Form")
    st.write("Use this form to submit events directly to the calendar.")

    with st.form("event_intake_form", clear_on_submit=True):
        intake_title = st.text_input("Event name", placeholder="e.g. Thursday Hill Repeats")
        intake_type = st.selectbox("Event type", list(EVENT_COLORS.keys()), key="intake_type")
        intake_date = st.date_input("Date", value=date.today(), key="intake_date")
        intake_all_day = st.checkbox("All day event", key="intake_all_day")

        intake_start_time = None
        intake_end_time = None
        if not intake_all_day:
            col1, col2 = st.columns(2)
            with col1:
                intake_start_time = st.time_input("Start time", value=time(8, 0), key="intake_start")
            with col2:
                intake_end_time = st.time_input("End time", value=time(9, 0), key="intake_end")

        intake_location = st.text_input("Location")
        intake_notes = st.text_area("Notes")

        intake_submitted = st.form_submit_button("Submit Event", use_container_width=True)

        if intake_submitted:
            if not intake_title:
                st.error("Please complete event name.")
            elif not intake_all_day and intake_end_time <= intake_start_time:
                st.error("End time must be after start time.")
            else:
                new_event = {
                    "id": str(uuid.uuid4()),
                    "title": intake_title,
                    "type": intake_type,
                    "color": EVENT_COLORS[intake_type],
                    "location": intake_location,
                    "notes": intake_notes,
                }

                if intake_all_day:
                    new_event["start"] = intake_date.isoformat()
                    new_event["allDay"] = True
                else:
                    new_event["start"] = datetime.combine(intake_date, intake_start_time).isoformat()
                    new_event["end"] = datetime.combine(intake_date, intake_end_time).isoformat()

                st.session_state.events.append(new_event)
                st.success("Thanks. Your event was added to the calendar.")

st.divider()
st.markdown(
    f'''
    <div style="text-align:center; color: {THEME_TEXT}; font-size: 0.85rem; padding: 0.75rem 0 0.25rem 0;">
        Built by Claire Kraft · {datetime.now().year}
    </div>
    '''
    ,
    unsafe_allow_html=True,
)

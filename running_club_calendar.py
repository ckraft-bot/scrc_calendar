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
from datetime import datetime, date, time
import uuid

st.set_page_config(page_title="Scenic City Run Club Calendar", page_icon="🏃", layout="wide")

# ---------------------------------------------------------------------------
# Config: event type -> color
# ---------------------------------------------------------------------------
EVENT_COLORS = {
    "Group Run": "#2ecc71",  # green
    "Race": "#3498db",       # blue
    "Other": "#e74c3c",      # red
}

# ---------------------------------------------------------------------------
# Session state: store events in memory (swap for a DB/file for persistence)
# ---------------------------------------------------------------------------
if "events" not in st.session_state:
    st.session_state.events = [
        {
            "id": str(uuid.uuid4()),
            "title": "Saturday Morning Group Run",
            "start": f"{date.today().isoformat()}T08:00:00",
            "end": f"{date.today().isoformat()}T09:00:00",
            "type": "Group Run",
            "color": EVENT_COLORS["Group Run"],
        },
        {
            "id": str(uuid.uuid4()),
            "title": "City 10K Race",
            "start": f"{date.today().isoformat()}T07:00:00",
            "type": "Race",
            "color": EVENT_COLORS["Race"],
        },
    ]

# ---------------------------------------------------------------------------
# Sidebar: admin quick add
# ---------------------------------------------------------------------------
st.sidebar.header("Admin Quick Add")

with st.sidebar.form("add_event_form", clear_on_submit=True):
    title = st.text_input("Event name", placeholder="e.g. Tuesday Track Workout")
    event_type = st.selectbox("Event type", list(EVENT_COLORS.keys()))
    event_date = st.date_input("Date", value=date.today())
    all_day = st.checkbox("All day event")

    start_time = None
    end_time = None
    if not all_day:
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.time_input("Start time", value=time(8, 0))
        with col2:
            end_time = st.time_input("End time", value=time(9, 0))

    location = st.text_input("Location (optional)")
    notes = st.text_area("Notes (optional)")

    submitted = st.form_submit_button("Add Event", use_container_width=True)

    if submitted:
        if not title:
            st.sidebar.error("Please give the event a name.")
        else:
            new_event = {
                "id": str(uuid.uuid4()),
                "title": title,
                "type": event_type,
                "color": EVENT_COLORS[event_type],
                "location": location,
                "notes": notes,
            }
            if all_day:
                new_event["start"] = event_date.isoformat()
                new_event["allDay"] = True
            else:
                new_event["start"] = datetime.combine(event_date, start_time).isoformat()
                new_event["end"] = datetime.combine(event_date, end_time).isoformat()

            st.session_state.events.append(new_event)
            st.sidebar.success(f"Added '{title}'")

st.sidebar.divider()
st.sidebar.markdown("### Legend")
for label, color in EVENT_COLORS.items():
    st.sidebar.markdown(
        f"<span style='display:inline-block;width:12px;height:12px;"
        f"background-color:{color};border-radius:3px;margin-right:8px;'></span>{label}",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("🏃 Running Club Calendar")
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
        custom_css="""
            .fc-event-title { font-weight: 600; }
            .fc-toolbar-title { font-size: 1.4rem; }
        """,
        key="running_calendar",
    )

    if state.get("eventClick"):
        clicked = state["eventClick"]["event"]
        st.subheader(f"📌 {clicked['title']}")
        matching = next((e for e in filtered_events if e["id"] == clicked.get("id")), None)
        if matching:
            st.write(f"**Type:** {matching['type']}")
            st.write(f"**Start:** {matching['start']}")
            if matching.get("end"):
                st.write(f"**End:** {matching['end']}")
            if matching.get("location"):
                st.write(f"**Location:** {matching['location']}")
            if matching.get("notes"):
                st.write(f"**Notes:** {matching['notes']}")

    st.divider()
    st.subheader("Upcoming Events")

    sorted_events = sorted(filtered_events, key=lambda e: e["start"])
    if not sorted_events:
        st.write("No events match the selected event type filters.")

    for e in sorted_events:
        color = e["color"]
        when = e["start"].replace("T", " ")
        st.markdown(
            f"""
            <div style="border-left: 5px solid {color}; padding: 6px 12px; margin-bottom: 6px; background-color: rgba(0,0,0,0.03); border-radius: 4px;">
                <strong>{e['title']}</strong> &mdash; {e['type']}<br>
                <span style="color: gray; font-size: 0.85em;">{when}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

with tab_submit:
    st.subheader("Event Intake Form")
    st.write("Use this form to submit events directly to the calendar.")

    with st.form("event_intake_form", clear_on_submit=True):
        submitter_name = st.text_input("Your name")
        submitter_email = st.text_input("Your email")
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
            if not submitter_name or not submitter_email or not intake_title:
                st.error("Please complete name, email, and event name.")
            elif "@" not in submitter_email:
                st.error("Please enter a valid email address.")
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

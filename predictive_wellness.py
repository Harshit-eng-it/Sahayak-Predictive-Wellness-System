from __future__ import annotations

from twilio.rest import Client
import streamlit as st

def send_sms_alert(message):

    account_sid = st.secrets["TWILIO_SID"]
    auth_token = st.secrets["TWILIO_AUTH"]
    from_number = st.secrets["TWILIO_PHONE"]

    # MULTIPLE NUMBERS
    to_numbers = st.secrets["ALERT_PHONES"]

    client = Client(account_sid, auth_token)

    for number in to_numbers:
        client.messages.create(
            body=message,
            from_=from_number,
            to=number
        )



import pandas as pd
import streamlit as st

from groq import Groq

from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "wellness_log.csv"

MODE_CONFIG = {
    "Student": {
        "sleep_target": 8.0,
        "water_target": 2.5,
        "activity_target": 45,
        "steps_target": 8000,
        "screen_limit": 8.0,
        "sedentary_limit": 8.0,
        "focus_label": "Burnout risk",
        "audience_line": "Academic wellness for learners under pressure.",
    },
    "Elder": {
        "sleep_target": 7.5,
        "water_target": 2.2,
        "activity_target": 35,
        "steps_target": 5500,
        "screen_limit": 5.0,
        "sedentary_limit": 9.0,
        "focus_label": "Fatigue risk",
        "audience_line": "Healthy aging support for elders and caregivers.",
    },
}

CSV_COLUMNS = [
    "timestamp",
    "name",
    "mode",
    "age",
    "sleep_hours",
    "stress_level",
    "mood_level",
    "fatigue_level",
    "water_liters",
    "activity_minutes",
    "steps",
    "screen_hours",
    "sedentary_hours",
    "caffeine_intake",
    "study_hours",
    "assignments_due",
    "exam_pressure",
    "mobility_level",
    "social_connection",
    "chronic_conditions",
    "medication_adherence",
    "sleep_risk",
    "hydration_risk",
    "activity_risk",
    "focus_risk",
    "mental_risk",
    "physical_risk",
    "caffeine_risk",
    "overall_risk",
    "health_score",
    "mental_score",
    "physical_score",
]


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, float(value)))


def load_history() -> pd.DataFrame:
    if DATA_FILE.exists():
        history = pd.read_csv(DATA_FILE)
        if "timestamp" in history.columns:
            history["timestamp"] = pd.to_datetime(history["timestamp"], errors="coerce")
        return history

    history = pd.DataFrame(columns=CSV_COLUMNS)
    history.to_csv(DATA_FILE, index=False)
    return history


def save_assessment(record: Dict[str, float | int | str]) -> None:
    history = load_history()
    row = pd.DataFrame([record], columns=CSV_COLUMNS)
    updated = pd.concat([history, row], ignore_index=True)
    updated.to_csv(DATA_FILE, index=False)


def filtered_history(history: pd.DataFrame, name: str, mode: str) -> pd.DataFrame:
    if history.empty:
        return history

    filtered = history.copy()
    if name.strip():
        filtered = filtered[filtered["name"].str.lower() == name.strip().lower()]
    filtered = filtered[filtered["mode"] == mode]
    return filtered.sort_values("timestamp")


def previous_entry(history: pd.DataFrame) -> pd.Series | None:
    if len(history) < 2:
        return None
    return history.iloc[-2]


def score_delta(current: float, previous: pd.Series | None, key: str) -> str | None:
    if previous is None or key not in previous or pd.isna(previous[key]):
        return None
    delta = round(float(current) - float(previous[key]), 1)
    if delta == 0:
        return "No change"
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta}"


def risk_band(score: float) -> str:
    if score >= 75:
        return "Critical"
    if score >= 55:
        return "High"
    if score >= 30:
        return "Moderate"
    return "Low"


def band_color(score: float) -> str:
    if score >= 75:
        return "#ff3b3b"   # neon red
    if score >= 55:
        return "#ff9f1c"   # neon orange
    if score >= 30:
        return "#ffe600"   # neon yellow
    return "#00ff9c"       # neon green

def calculate_sleep_risk(hours: float, target: float) -> float:
    gap = abs(target - hours)
    risk = gap * 14
    if hours < 5:
        risk += 18
    if hours > target + 2.5:
        risk += 10
    return clamp(risk)


def calculate_hydration_risk(water_liters: float, target: float) -> float:
    if water_liters >= target:
        return 8 if water_liters > target + 1.5 else 0

    shortfall = target - water_liters
    risk = (shortfall / max(target, 0.1)) * 75
    if water_liters < 1.2:
        risk += 15
    return clamp(risk)


def calculate_activity_risk(
    activity_minutes: float,
    steps: int,
    sedentary_hours: float,
    target_minutes: float,
    target_steps: int,
    sedentary_limit: float,
) -> float:
    minute_gap = max(0.0, target_minutes - activity_minutes) / max(target_minutes, 1) * 40
    step_gap = max(0, target_steps - steps) / max(target_steps, 1) * 35
    sitting_penalty = max(0.0, sedentary_hours - sedentary_limit) * 6
    if activity_minutes < 15:
        sitting_penalty += 10
    return clamp(minute_gap + step_gap + sitting_penalty)


def compute_scores(inputs: Dict[str, float | int | str]) -> Dict[str, float]:
    mode = str(inputs["mode"])
    config = MODE_CONFIG[mode]

    sleep_risk = calculate_sleep_risk(float(inputs["sleep_hours"]), config["sleep_target"])
    hydration_risk = calculate_hydration_risk(float(inputs["water_liters"]), config["water_target"])
    activity_risk = calculate_activity_risk(
        float(inputs["activity_minutes"]),
        int(inputs["steps"]),
        float(inputs["sedentary_hours"]),
        config["activity_target"],
        config["steps_target"],
        config["sedentary_limit"],
    )

    stress_component = float(inputs["stress_level"]) * 10
    fatigue_component = float(inputs["fatigue_level"]) * 9
    mood_penalty = (10 - float(inputs["mood_level"])) * 8

   
    caffeine_risk = clamp(
        float(inputs["caffeine_intake"]) * 8 +
        float(inputs["stress_level"]) * 3 +
        float(inputs["fatigue_level"]) * 2 +
        max(0, 7 - float(inputs["sleep_hours"])) * 4
    )

    if mode == "Student":
        screen_overload = clamp(max(0.0, float(inputs["screen_hours"]) - config["screen_limit"]) * 12)
        study_load = clamp(float(inputs["study_hours"]) / 10 * 100)
        assignment_load = clamp(float(inputs["assignments_due"]) * 8)
        exam_load = clamp(float(inputs["exam_pressure"]) * 10)

        focus_risk = clamp(
            0.28 * stress_component
            + 0.18 * fatigue_component
            + 0.18 * study_load
            + 0.16 * assignment_load
            + 0.12 * exam_load
            + 0.08 * screen_overload
        )

        mental_risk = clamp(
            0.30 * stress_component
            + 0.20 * focus_risk
            + 0.16 * sleep_risk
            + 0.18 * mood_penalty
            + 0.16 * screen_overload
        )

        physical_risk = clamp(
            0.34 * sleep_risk
            + 0.24 * hydration_risk
            + 0.24 * activity_risk
            + 0.10 * fatigue_component
            + 0.08 * screen_overload
        )

    else:
        mobility_risk = clamp((10 - float(inputs["mobility_level"])) * 10)
        social_risk = clamp((10 - float(inputs["social_connection"])) * 10)
        medication_risk = 0 if str(inputs["medication_adherence"]) == "Yes" else 35
        condition_risk = clamp(float(inputs["chronic_conditions"]) * 12)

        focus_risk = clamp(
            0.25 * stress_component
            + 0.22 * fatigue_component
            + 0.20 * social_risk
            + 0.18 * mobility_risk
            + 0.15 * condition_risk
        )

        mental_risk = clamp(
            0.30 * stress_component
            + 0.22 * social_risk
            + 0.20 * focus_risk
            + 0.18 * mood_penalty
            + 0.10 * sleep_risk
        )

        physical_risk = clamp(
            0.24 * sleep_risk
            + 0.20 * hydration_risk
            + 0.20 * activity_risk
            + 0.16 * mobility_risk
            + 0.10 * condition_risk
            + 0.10 * medication_risk
        )

    overall_risk = clamp(0.48 * mental_risk + 0.52 * physical_risk)

    return {
        "sleep_risk": round(sleep_risk, 1),
        "hydration_risk": round(hydration_risk, 1),
        "activity_risk": round(activity_risk, 1),
        "focus_risk": round(focus_risk, 1),
        "mental_risk": round(mental_risk, 1),
        "physical_risk": round(physical_risk, 1),
        "caffeine_risk": round(caffeine_risk, 1),
        "overall_risk": round(overall_risk, 1),
        "health_score": round(100 - overall_risk, 1),
        "mental_score": round(100 - mental_risk, 1),
        "physical_score": round(100 - physical_risk, 1),
    }

def build_alerts(inputs: Dict[str, float | int | str], scores: Dict[str, float]) -> List[str]:
    alerts: List[str] = []
    mode = str(inputs["mode"])

    if scores["overall_risk"] >= 75:
        alerts.append(
            "Critical risk pattern detected. This is not a diagnosis, but the user should consider a prompt check-in with a trusted caregiver, advisor, or clinician."
        )
    if scores["mental_risk"] >= 70:
        alerts.append("Mental wellness risk is high. Prioritize recovery, reduce overload today, and involve a mentor or support person if the pattern continues.")
    if scores["sleep_risk"] >= 65:
        alerts.append("Sleep disruption is a major driver right now. Recovery quality may improve quickly if sleep is stabilized over the next 24-48 hours.")
    if scores["hydration_risk"] >= 60:
        alerts.append("Hydration is below the target range. Use small scheduled water goals rather than waiting for thirst.")
    if mode == "Student" and scores["focus_risk"] >= 65:
        alerts.append("Burnout risk is elevated. Academic load and rest patterns suggest a strong need for workload triage and shorter focus cycles.")
    if mode == "Elder" and scores["physical_risk"] >= 68:
        alerts.append("Physical wellness risk is elevated. Low movement, hydration, or medication consistency may need caregiver visibility.")

    return alerts


def build_recommendations(inputs: Dict[str, float | int | str], scores: Dict[str, float]) -> List[str]:
    mode = str(inputs["mode"])
    recommendations: List[str] = []

    if scores["sleep_risk"] >= 50:
        recommendations.append("Sleep recovery: protect a fixed wind-down window tonight and avoid stimulating screen use in the final hour before bed.")
    if scores["hydration_risk"] >= 40:
        recommendations.append("Hydration reset: split water intake into 3-4 checkpoints across the day instead of one large catch-up effort.")
    if scores["activity_risk"] >= 45:
        recommendations.append("Movement reset: add short walking or stretching breaks every 60-90 minutes to reduce sedentary strain.")
    if scores["mental_risk"] >= 55:
        recommendations.append("Stress regulation: use a low-friction decompression routine today such as slow breathing, a quiet walk, or a short reflective pause.")

    if mode == "Student":
        if float(inputs["study_hours"]) >= 6 or float(inputs["exam_pressure"]) >= 7:
            recommendations.append("Study strategy: convert long study blocks into focused sprints with planned breaks and one realistic top priority.")
        if float(inputs["assignments_due"]) >= 4:
            recommendations.append("Academic triage: rank assignments by urgency and ask for support early on any item that is slipping.")
        if float(inputs["screen_hours"]) >= MODE_CONFIG["Student"]["screen_limit"]:
            recommendations.append("Screen hygiene: move one study or revision block off-screen today to reduce fatigue and improve sleep readiness.")
    else:
        if float(inputs["mobility_level"]) <= 5:
            recommendations.append("Mobility support: aim for two to three gentle movement sessions today, even if each one is only a few minutes.")
        if float(inputs["social_connection"]) <= 5:
            recommendations.append("Connection cue: schedule a call, shared meal, or short social interaction to reduce isolation-driven risk.")
        if str(inputs["medication_adherence"]) == "No":
            recommendations.append("Medication consistency: pair reminders with daily anchors such as breakfast, lunch, or bedtime.")

    if not recommendations:
        recommendations.append("Wellness is stable today. Maintain the current routine and keep tracking patterns so the system can detect changes early.")

    return recommendations


def build_daily_plan(inputs: Dict[str, float | int | str], scores: Dict[str, float]) -> List[str]:
    mode = str(inputs["mode"])
    plan = [
        "Morning: review your score snapshot, drink water early, and set one achievable health goal for today.",
        "Afternoon: take a movement break and respond to the biggest stress driver before it compounds.",
        "Evening: reduce stimulation, reflect on what helped, and prepare for consistent sleep timing.",
    ]

    if mode == "Student" and scores["focus_risk"] >= 55:
        plan[1] = "Afternoon: break your workload into two priority tasks, use a timed focus sprint, and stop multitasking."
    if mode == "Elder" and scores["physical_risk"] >= 55:
        plan[1] = "Afternoon: complete a gentle walk or chair-based mobility session and check hydration before resting again."

    return plan


def top_drivers(inputs: Dict[str, float | int | str], scores: Dict[str, float]) -> List[str]:
    drivers = {
        "Sleep": scores["sleep_risk"],
        "Hydration": scores["hydration_risk"],
        "Activity": scores["activity_risk"],
        "Caffeine": scores.get("caffeine_risk", 0),
        MODE_CONFIG[str(inputs["mode"])]["focus_label"].replace(" risk", ""): scores["focus_risk"],
        "Mental load": scores["mental_risk"],
    }

    ranked = sorted(drivers.items(), key=lambda item: item[1], reverse=True)

    return [f"{name} ({value:.0f}/100 risk)" for name, value in ranked[:3]]


def predict_7_day_forecast(history: pd.DataFrame) -> str:
    if history is None or history.empty:
        return "Not enough data to generate 7-day forecast."

    last = history.iloc[-1]

    base_risk = float(last["overall_risk"])
    mental = float(last["mental_risk"])
    physical = float(last["physical_risk"])
    caffeine = float(last.get("caffeine_risk", 0))

    forecast = []

    for day in range(1, 8):
        # small trend drift
        drift = (mental * 0.02) + (physical * 0.015) + (caffeine * 0.01)
        predicted = max(0, min(100, base_risk + drift * day))

        if predicted >= 75:
            label = "Critical"
        elif predicted >= 55:
            label = "High"
        elif predicted >= 30:
            label = "Moderate"
        else:
            label = "Low"

        forecast.append(f"Day {day}: {predicted:.0f}/100 risk — {label}")

    return "7-Day Health Forecast:\n\n" + "\n".join(forecast)

def predict_caffeine_dependency(scores: Dict[str, float]) -> str:
    caffeine = float(scores.get("caffeine_risk", 0))

    if caffeine >= 75:
        level = "High dependency risk"
        advice = "Your body may be relying heavily on caffeine. Reduce intake gradually and improve sleep."
    elif caffeine >= 55:
        level = "Moderate dependency"
        advice = "Caffeine is affecting fatigue and stress. Try reducing late-day intake."
    elif caffeine >= 30:
        level = "Mild dependency"
        advice = "Monitor caffeine. Avoid consuming after afternoon."
    else:
        level = "Low dependency"
        advice = "Caffeine intake appears safe."

    return f"Caffeine Dependency Prediction:\n\nRisk: {caffeine:.0f}/100\nLevel: {level}\nAdvice: {advice}"

def generate_sahayak_reply(
    message: str,
    inputs: Dict[str, float | int | str],
    scores: Dict[str, float],
    history: pd.DataFrame,
) -> str:

    # ---------- 7 DAY FORECAST ----------
    if "forecast" in message.lower() or "future" in message.lower():
        return predict_7_day_forecast(history)

    # ---------- CAFFEINE DEPENDENCY ----------
    if "caffeine" in message.lower() or "coffee" in message.lower():
        return predict_caffeine_dependency(scores)

    # ---------- NORMAL AI RESPONSE ----------
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    prompt = f"""
You are Sahayak AI — a predictive wellness assistant.

User Data:
Mode: {inputs['mode']}
Sleep: {inputs['sleep_hours']}
Stress: {inputs['stress_level']}
Mood: {inputs['mood_level']}
Fatigue: {inputs['fatigue_level']}
Water: {inputs['water_liters']}
Activity: {inputs['activity_minutes']}
Steps: {inputs['steps']}

Scores:
Health Score: {scores['health_score']}
Mental Score: {scores['mental_score']}
Physical Score: {scores['physical_score']}
Caffeine Risk: {scores['caffeine_risk']}
Overall Risk: {scores['overall_risk']}

User Question:
{message}

Give short, clear, helpful wellness advice.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are Sahayak AI health assistant"},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content

    


def latest_record_from_history(history: pd.DataFrame) -> Dict[str, float | int | str] | None:
    if history.empty:
        return None
    latest = history.iloc[-1].to_dict()
    if pd.notna(latest.get("timestamp")):
        latest["timestamp"] = pd.to_datetime(latest["timestamp"]).strftime("%Y-%m-%d %H:%M")
    return latest


def metric_card(title: str, value: float, subtitle: str, color: str) -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value" style="color:{color};">{value:.0f}</div>
        <div class="metric-subtitle">{subtitle}</div>
    </div>
    """


def progress_card(title: str, value: float, helper: str) -> str:
    bar_color = band_color(value)
    return f"""
<div class="progress-card">
    <div class="progress-row">
        <span>{title}</span>
        <span>{value:.0f}/100</span>
    </div>
    <div class="progress-shell">
        <div class="progress-fill" style="width:{value}%; background:{bar_color};"></div>
    </div>
    <div class="progress-helper">{helper}</div>
</div>
"""


def color_card(title, value):
    color = band_color(value)
    return f"""
<div style="
    padding:18px;
    border-radius:18px;
    background:rgba(10,15,30,0.9);
    border:1px solid {color};
    text-align:center;
">
    <div style="font-size:14px;color:#aaa">{title}</div>
    <div style="font-size:28px;color:{color};font-weight:700">
        {value:.0f}
    </div>
</div>
"""


def render_header(mode: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>Predictive Wellness System</h1>
            <p>
                AI-powered health prediction for students and elders. Track daily patterns,
                detect emerging risks early, and get personalized guidance from the Sahayak assistant.
            </p>
            <p><strong>Active mode:</strong> {mode} | {MODE_CONFIG[mode]["audience_line"]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview_panel() -> None:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            """
            <div class="insight-box">
                <strong>Step 1: Intake</strong><br>
                Daily sleep, stress, activity, hydration, and mode-specific wellness signals.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            """
            <div class="insight-box">
                <strong>Step 2: Prediction</strong><br>
                Local scoring engine converts patterns into mental, physical, and overall risk bands.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            """
            <div class="insight-box">
                <strong>Step 3: Guidance</strong><br>
                Sahayak explains the result, recommends micro-actions, and supports repeat check-ins.
            </div>
            """,
            unsafe_allow_html=True,
        )


def initialize_state() -> None:
    if "latest_inputs" not in st.session_state:
        st.session_state.latest_inputs = None
    if "latest_scores" not in st.session_state:
        st.session_state.latest_scores = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def render_sidebar() -> tuple[str, str, int]:
    with st.sidebar:
        st.title("Profile Setup")
        mode = st.selectbox("Choose user mode", list(MODE_CONFIG.keys()))
        name = st.text_input("User name", value="Demo User")
        age_default = 20 if mode == "Student" else 68
        age = st.number_input("Age", min_value=10, max_value=100, value=age_default)
        st.markdown("---")
        st.caption("Prototype stack")
        st.write("Python + Streamlit")
        st.write("Local CSV logging")
        st.write("Rule-based prediction engine")
        st.write("Sahayak conversational guidance")
        st.markdown("---")
        st.caption("Important note")
        st.write("This demo supports early wellness monitoring. It is not a medical diagnosis tool.")
    return mode, name, int(age)


def render_checkin_tab(mode: str, name: str, age: int) -> None:
    st.subheader("Daily wellness check-in")
    st.write("Capture today's physical, mental, and lifestyle signals for the prediction engine.")

    with st.form("wellness_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            sleep_hours = st.number_input("Sleep hours", min_value=0.0, max_value=16.0, value=6.5, step=0.5)
            stress_level = st.slider("Stress level", 1, 10, 6)
            mood_level = st.slider("Mood level", 1, 10, 6)

        with col2:
            fatigue_level = st.slider("Fatigue level", 1, 10, 5)
            water_liters = st.number_input("Water intake (liters)", min_value=0.0, max_value=6.0, value=1.8, step=0.1)
            activity_minutes = st.number_input("Activity minutes", min_value=0, max_value=300, value=30, step=5)

        with col3:
            steps = st.number_input("Steps", min_value=0, max_value=50000, value=4500, step=250)
            screen_hours = st.number_input("Screen time (hours)", min_value=0.0, max_value=18.0, value=6.0, step=0.5)
            sedentary_hours = st.number_input("Sedentary hours", min_value=0.0, max_value=18.0, value=8.0, step=0.5)

        # ---------- NEW CAFFEINE SLIDER ----------
        st.markdown("### ☕ Caffeine Intake")
        caffeine_intake = st.slider(
            "Coffee / Caffeine intake (cups per day)",
            0, 10, 2
        )

        if mode == "Student":
            st.markdown("#### Student-specific signals")
            spec1, spec2, spec3 = st.columns(3)
            with spec1:
                study_hours = st.number_input("Study hours", min_value=0.0, max_value=16.0, value=5.0, step=0.5)
            with spec2:
                assignments_due = st.number_input("Assignments due soon", min_value=0, max_value=20, value=3, step=1)
            with spec3:
                exam_pressure = st.slider("Exam pressure", 1, 10, 6)

            mobility_level = 0
            social_connection = 0
            chronic_conditions = 0
            medication_adherence = "N/A"

        else:
            st.markdown("#### Elder-specific signals")
            spec1, spec2, spec3, spec4 = st.columns(4)

            with spec1:
                mobility_level = st.slider("Mobility comfort", 1, 10, 6)
            with spec2:
                social_connection = st.slider("Social connection", 1, 10, 6)
            with spec3:
                chronic_conditions = st.number_input("Chronic conditions", min_value=0, max_value=10, value=2, step=1)
            with spec4:
                medication_adherence = st.selectbox("Medication adherence today", ["Yes", "No"])

            study_hours = 0.0
            assignments_due = 0
            exam_pressure = 0

        submit = st.form_submit_button(
            "Run predictive wellness analysis",
            use_container_width=True
        )

    if not submit:
        return

    inputs = {
        "name": name.strip() or "Anonymous User",
        "mode": mode,
        "age": int(age),
        "sleep_hours": float(sleep_hours),
        "stress_level": int(stress_level),
        "mood_level": int(mood_level),
        "fatigue_level": int(fatigue_level),
        "water_liters": float(water_liters),
        "activity_minutes": int(activity_minutes),
        "steps": int(steps),
        "screen_hours": float(screen_hours),
        "sedentary_hours": float(sedentary_hours),

        # NEW CAFFEINE INPUT
        "caffeine_intake": int(caffeine_intake),

        "study_hours": float(study_hours),
        "assignments_due": int(assignments_due),
        "exam_pressure": int(exam_pressure),
        "mobility_level": int(mobility_level),
        "social_connection": int(social_connection),
        "chronic_conditions": int(chronic_conditions),
        "medication_adherence": medication_adherence,
    }

    scores = compute_scores(inputs)

    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        **inputs,
        **scores,
    }

    save_assessment(record)

    st.session_state.latest_inputs = inputs
    st.session_state.latest_scores = scores
    st.session_state.chat_history = []

    st.success(
        "Assessment completed. Open the Dashboard and Sahayak tabs to review the prediction and care plan."
    )

def get_active_context(name: str, mode: str) -> tuple[Dict[str, float | int | str] | None, Dict[str, float] | None, pd.DataFrame]:
    refreshed_history = filtered_history(load_history(), name, mode)
    active_inputs = st.session_state.latest_inputs
    active_scores = st.session_state.latest_scores

    if active_inputs is None or active_scores is None:
        latest_from_history = latest_record_from_history(refreshed_history)

        if latest_from_history is not None:

            active_inputs = {
                "name": latest_from_history["name"],
                "mode": latest_from_history["mode"],
                "age": latest_from_history["age"],
                "sleep_hours": latest_from_history["sleep_hours"],
                "stress_level": latest_from_history["stress_level"],
                "mood_level": latest_from_history["mood_level"],
                "fatigue_level": latest_from_history["fatigue_level"],
                "water_liters": latest_from_history["water_liters"],
                "activity_minutes": latest_from_history["activity_minutes"],
                "steps": latest_from_history["steps"],
                "screen_hours": latest_from_history["screen_hours"],
                "sedentary_hours": latest_from_history["sedentary_hours"],
                "caffeine_intake": latest_from_history.get("caffeine_intake", 0),
                "study_hours": latest_from_history["study_hours"],
                "assignments_due": latest_from_history["assignments_due"],
                "exam_pressure": latest_from_history["exam_pressure"],
                "mobility_level": latest_from_history["mobility_level"],
                "social_connection": latest_from_history["social_connection"],
                "chronic_conditions": latest_from_history["chronic_conditions"],
                "medication_adherence": latest_from_history["medication_adherence"],
            }

            active_scores = {
                "sleep_risk": latest_from_history.get("sleep_risk", 0),
                "hydration_risk": latest_from_history.get("hydration_risk", 0),
                "activity_risk": latest_from_history.get("activity_risk", 0),
                "focus_risk": latest_from_history.get("focus_risk", 0),
                "mental_risk": latest_from_history.get("mental_risk", 0),
                "physical_risk": latest_from_history.get("physical_risk", 0),
                "caffeine_risk": latest_from_history.get("caffeine_risk", 0),
                "overall_risk": latest_from_history.get("overall_risk", 0),
                "health_score": latest_from_history.get("health_score", 0),
                "mental_score": latest_from_history.get("mental_score", 0),
                "physical_score": latest_from_history.get("physical_score", 0),
            }

    return active_inputs, active_scores, refreshed_history


def render_dashboard_tab(
    active_inputs: Dict[str, float | int | str] | None,
    active_scores: Dict[str, float] | None,
    history: pd.DataFrame,
) -> None:
    st.subheader("Health scores and risk indicators")

    if active_inputs is None or active_scores is None:
        st.info("Submit a check-in first to generate the wellness dashboard.")
        return

    previous = previous_entry(history)
    focus_label = MODE_CONFIG[str(active_inputs["mode"])]["focus_label"]

    # ---------- METRIC CARDS ----------
    metric_cols = st.columns(4)
    cards = [
        ("Overall health",
         float(active_scores["health_score"]),
         score_delta(float(active_scores["health_score"]), previous, "health_score") or "Latest score",
         "#1f7a5c"),

        ("Mental score",
         float(active_scores["mental_score"]),
         score_delta(float(active_scores["mental_score"]), previous, "mental_score") or "Emotional resilience",
         "#2e9d6b"),

        ("Physical score",
         float(active_scores["physical_score"]),
         score_delta(float(active_scores["physical_score"]), previous, "physical_score") or "Body readiness",
         "#4d7cfe"),

        (focus_label,
         float(active_scores["focus_risk"]),
         risk_band(float(active_scores["focus_risk"])),
         band_color(float(active_scores["focus_risk"]))),
    ]

    for column, (title, value, subtitle, color) in zip(metric_cols, cards):
        with column:
            st.markdown(metric_card(title, value, subtitle, color), unsafe_allow_html=True)

    # ---------- LIFESTYLE RISK (NEW) ----------
    st.markdown("### Lifestyle Risk")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            color_card("Stress Risk", active_scores["mental_risk"]),
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            color_card("Fatigue Risk", active_scores["physical_risk"]),
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            color_card("Caffeine Risk", active_scores["caffeine_risk"]),
            unsafe_allow_html=True
        )

    left, right = st.columns([1.2, 1])

    # ---------- LEFT ----------
    with left:
        st.markdown(
            progress_card(
                "Overall risk",
                float(active_scores["overall_risk"]),
                "Integrated prediction across mental and physical wellbeing.",
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            progress_card(
                "Mental risk",
                float(active_scores["mental_risk"]),
                "Stress, mood, fatigue, and overload pattern.",
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            progress_card(
                "Physical risk",
                float(active_scores["physical_risk"]),
                "Sleep, activity, hydration, and body-function signals.",
            ),
            unsafe_allow_html=True,
        )

    # ---------- RIGHT ----------
    with right:
        st.markdown(
            f"<span class='pill' style='background:{band_color(float(active_scores['overall_risk']))};'>"
            f"{risk_band(float(active_scores['overall_risk']))} overall risk</span>",
            unsafe_allow_html=True,
        )

        st.write("")
        st.markdown("**Top drivers today**")

        for driver in top_drivers(active_inputs, active_scores):
            st.write(f"- {driver}")

        # -------- ALERTS --------
        alerts = build_alerts(active_inputs, active_scores)

        st.markdown("**Early alerts**")

        if alerts:
            for alert in alerts:
                st.warning(alert)

            # SEND SMS ALERT
            sms_text = f"""
🚨 Wellness Alert

User: {active_inputs['name']}
Overall Risk: {active_scores['overall_risk']}
Mental Risk: {active_scores['mental_risk']}

Top Issue: {alerts[0]}
"""
            send_sms_alert(sms_text)

        else:
            st.success("No urgent alert threshold crossed in this check-in.")

    # ---------- RECOMMENDATIONS ----------
    rec_col, plan_col = st.columns(2)

    with rec_col:
        st.markdown("**Actionable suggestions**")
        for item in build_recommendations(active_inputs, active_scores):
            st.write(f"- {item}")

    with plan_col:
        st.markdown("**Daily recovery plan**")
        for item in build_daily_plan(active_inputs, active_scores):
            st.write(f"- {item}")


def render_sahayak_tab(
    active_inputs: Dict[str, float | int | str] | None,
    active_scores: Dict[str, float] | None,
    history: pd.DataFrame,
) -> None:
    st.subheader("Sahayak AI assistant")
    st.write("Ask for explanations, next steps, or a simple recovery plan based on the latest scores.")

    if active_inputs is None or active_scores is None:
        st.info("Run a wellness check-in first so Sahayak has context.")
        return

    for speaker, message in st.session_state.chat_history:
        with st.chat_message("user" if speaker == "user" else "assistant"):
            st.write(message)

    user_message = st.chat_input("Ask Sahayak about sleep, stress, hydration, activity, or today's plan")
    if user_message:
        st.session_state.chat_history.append(("user", user_message))
        reply = generate_sahayak_reply(user_message, active_inputs, active_scores, history)
        st.session_state.chat_history.append(("assistant", reply))
        st.rerun()

    if not st.session_state.chat_history:
        starter_reply = generate_sahayak_reply("overall summary", active_inputs, active_scores, history)
        with st.chat_message("assistant"):
            st.write(starter_reply)


def render_history_tab(name: str, mode: str, history: pd.DataFrame) -> None:
    st.subheader("History and trends")

    if history.empty:
        st.info("No saved history for this profile yet. Submit the first check-in to start tracking trends.")
        return

    chart_data = history.copy().set_index("timestamp")[["health_score", "mental_score", "physical_score"]]
    st.line_chart(chart_data)

    latest_row = history.iloc[-1]
    summary_cols = st.columns(3)
    summary_cols[0].metric("Entries logged", len(history))
    summary_cols[1].metric("Latest health score", round(float(latest_row["health_score"]), 1))
    summary_cols[2].metric("Latest overall risk", round(float(latest_row["overall_risk"]), 1))

    display_columns = [
        "timestamp",
        "mode",
        "health_score",
        "mental_score",
        "physical_score",
        "overall_risk",
        "sleep_risk",
        "hydration_risk",
        "activity_risk",
        "focus_risk",
    ]
    st.dataframe(
        history[display_columns].sort_values("timestamp", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    csv_bytes = history.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download user history as CSV",
        data=csv_bytes,
        file_name=f"{name.strip().replace(' ', '_').lower() or 'wellness'}_{mode.lower()}_history.csv",
        mime="text/csv",
    )


def main() -> None:
    st.set_page_config(
        page_title="Predictive Wellness System",
        layout="wide",
        initial_sidebar_state="expanded",
    )



def main():
    st.set_page_config(
        page_title="Predictive Wellness System",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    apply_styles()
def apply_styles() -> None:
    st.markdown(
        """
        <style>

        .block-container {
            color: white !important;
        }

        /* MAIN BACKGROUND */
        .stApp { 
            background: radial-gradient(circle at top, #0b0f1a, #05070d 70%);
            color: #e6f1ff;
        }

        /* FIX SLIDER NOT MOVING */
        [data-baseweb="slider"] * {
            pointer-events: auto !important;
        }

        /* SIDEBAR */
        section[data-testid="stSidebar"] {
            background: #05070d;
        }

        .hero {
            padding: 1.6rem 1.8rem;
            border-radius: 24px;
            background: linear-gradient(135deg, #00f5ff, #00ff9c);
            color: #001014;
            box-shadow: 0 0 30px rgba(0,255,255,0.35);
            margin-bottom: 1.2rem;
        }

        .insight-box {
            background: rgba(10,15,30,0.85);
            border: 1px solid rgba(0,255,255,0.25);
            border-radius: 20px;
            padding: 1rem;
        }

        .metric-card {
            background: rgba(8,12,25,0.9);
            border-radius: 22px;
            padding: 1.1rem;
            border: 1px solid rgba(0,255,255,0.25);
        }

        .progress-card {
            background: rgba(8,12,25,0.9);
            border: 1px solid rgba(0,255,255,0.25);
            border-radius: 18px;
            padding: 0.95rem;
        }

        .stButton>button {
            background: linear-gradient(90deg,#00f5ff,#00ff9c);
            color: black;
            border: none;
            border-radius: 12px;
            font-weight: 700;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


def main():
    st.set_page_config(
        page_title="Predictive Wellness System",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    apply_styles()

    initialize_state()

    mode, name, age = render_sidebar()

    render_header(mode)
    render_overview_panel()

    tabs = st.tabs(["Check-in", "Dashboard", "Sahayak", "History"])

    with tabs[0]:
        render_checkin_tab(mode, name, age)

    active_inputs, active_scores, history = get_active_context(name, mode)

    with tabs[1]:
        render_dashboard_tab(active_inputs, active_scores, history)

    with tabs[2]:
        render_sahayak_tab(active_inputs, active_scores, history)

    with tabs[3]:
        render_history_tab(name, mode, history)


if __name__ == "__main__":
    main()
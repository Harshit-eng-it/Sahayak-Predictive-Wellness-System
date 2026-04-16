# 🩺 Sahayak : Predictive Wellness System
## 🚀 Live Demo

<p align="center">
<a href="https://sahayak-predictive-wellness-system-hsbwk6fm3wa464f829pejr.streamlit.app/">
<img src="https://img.shields.io/badge/TRY-SAHAYAK%20LIVE-00ff9c?style=for-the-badge" />
</a>
</p>

AI-powered early wellness prediction system for students & elders.  
Track daily habits → Detect risk → Get smart guidance → Prevent burnout.

Sleep • Stress • Fatigue • Hydration • Activity • Caffeine • Mental Risk • Physical Risk

Built with Streamlit + Python + Predictive Risk Engine + AI Assistant


Sahayak is a predictive wellness monitoring system that analyzes daily lifestyle signals to detect early mental and physical health risks. The system provides risk scoring, personalized recommendations, AI chat guidance, and automated alerting.

This project is designed for students and elders to track wellness trends and identify early warning signs.

---

## Features

* Daily wellness check-in interface
* Mental, physical, and overall risk prediction
* Caffeine dependency detection
* 7-day health risk forecast
* AI assistant (Sahayak chat)
* Dashboard with health score cards
* Early warning alerts
* SMS alert system (Twilio integration)
* History tracking and trend visualization
* Personalized recovery recommendations
* Student mode & Elder mode

---

## Tech Stack

Python
Streamlit
Pandas
Groq LLM (Llama 3.1)
Twilio SMS API
CSV data storage

---

## Project Structure

predictive_wellness.py
wellness_log.csv
.streamlit/
└── secrets.toml
README.md

---

## Installation

Clone the repository

git clone https://github.com/yourusername/sahayak-predictive-wellness.git

cd sahayak-predictive-wellness

Install dependencies

pip install streamlit pandas groq twilio

---

## Run the App

streamlit run predictive_wellness.py

---

## Secrets Configuration

Create file:

.streamlit/secrets.toml

Add:

GROQ_API_KEY = "your_groq_key"

TWILIO_SID = "your_sid"
TWILIO_AUTH = "your_auth_token"
TWILIO_PHONE = "+1234567890"

ALERT_PHONES = ["+91XXXXXXXXXX"]

---

## How It Works

User enters daily wellness data
System calculates risk scores
Dashboard shows predictions
Alerts triggered if risk is high
Sahayak assistant provides guidance
History tracks long-term trends

---

## Risk Engine

The system calculates:

Sleep Risk
Hydration Risk
Activity Risk
Mental Risk
Physical Risk
Caffeine Dependency Risk
Overall Health Risk

Health Score = 100 − Overall Risk

---

## AI Assistant (Sahayak)

Users can ask:

"How is my health today?"
"Give me recovery plan"
"7 day forecast"
"Caffeine risk"
"How to reduce stress?"

---

## Screens

Check-in Page
Dashboard
AI Chat Assistant
History Graph
SMS Alert System

---

## Use Cases

Student burnout prediction
Elder health monitoring
Stress tracking
Fatigue detection
Lifestyle risk prediction
Early wellness alerts

---

## Future Improvements

Mobile app version
Doctor dashboard
Wearable integration
Real-time alerts
Email notifications
Cloud database

---

## Author

Harshit
Predictive Health AI Project

---

## License

Educational / Research Use

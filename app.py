import os
import uuid
import mimetypes
from datetime import datetime

import requests
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "demo-secret-key-not-for-prod")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://gqrcmyvdhezhimehnszj.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
BUCKET = "demo-911missing-photos"

ORG_NAME = os.environ.get("ORG_NAME", "Find The Missing")
ORG_NAME_LEGACY = "911Missing"


def supabase_headers():
    # NOTE: intentionally NOT requesting Prefer: return=representation.
    # These tables only grant INSERT to anon (no SELECT), by design, so
    # submitted contact info can never be read back out over the public
    # anon key. We generate the record id client-side instead (below) so
    # we can still show a confirmation id without needing read access.
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }


# Sample / placeholder cases only — invented people, never real case data.
SAMPLE_CASES = [
    {
        "name": "Jordan A. (placeholder)",
        "age": 27,
        "last_seen": "Downtown transit center, Springfield — 3 weeks ago",
        "status": "Active Search",
        "status_color": "active",
        "description": "Sample case card for demo purposes only. In production this "
        "would show real, verified case details submitted and reviewed by our team.",
    },
    {
        "name": "Sample Case — M. Rivera",
        "age": 15,
        "last_seen": "Near Lincoln Park footbridge — 5 days ago",
        "status": "Active Search — Urgent",
        "status_color": "urgent",
        "description": "Placeholder listing showing how an at-risk-minor case would "
        "be flagged and prioritized at the top of the queue. Not a real person.",
    },
    {
        "name": "Sample Case — R. Okafor",
        "age": 61,
        "last_seen": "Rest stop off Highway 40 — 2 months ago",
        "status": "Found Safe",
        "status_color": "resolved",
        "description": "Demo of a resolved case card. In production, families and "
        "volunteers can see honest, up-to-date status at every stage of a search.",
    },
]


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/")
def home():
    return render_template("index.html", org=ORG_NAME, org_legacy=ORG_NAME_LEGACY)


@app.route("/cases")
def cases():
    return render_template("cases.html", cases=SAMPLE_CASES, org=ORG_NAME)


@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        try:
            photo_path = None
            photo = request.files.get("photo")
            if photo and photo.filename:
                ext = os.path.splitext(photo.filename)[1] or ".jpg"
                object_name = f"{uuid.uuid4()}{ext}"
                content_type = photo.mimetype or mimetypes.guess_type(photo.filename)[0] or "application/octet-stream"
                upload_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{object_name}"
                up_resp = requests.post(
                    upload_url,
                    headers={
                        "apikey": SUPABASE_ANON_KEY,
                        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                        "Content-Type": content_type,
                    },
                    data=photo.read(),
                    timeout=20,
                )
                if up_resp.status_code in (200, 201):
                    photo_path = object_name

            case_id = str(uuid.uuid4())
            payload = {
                "id": case_id,
                "reporter_name": request.form.get("reporter_name", "").strip(),
                "reporter_contact": request.form.get("reporter_contact", "").strip(),
                "missing_person_name": request.form.get("missing_person_name", "").strip(),
                "age": request.form.get("age", "").strip(),
                "description": request.form.get("description", "").strip(),
                "last_seen_location": request.form.get("last_seen_location", "").strip(),
                "urgency_flag": bool(request.form.get("urgency_flag")),
                "photo_path": photo_path,
                "status": "new_demo_submission",
            }

            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/demo_911missing_reports",
                headers=supabase_headers(),
                json=payload,
                timeout=15,
            )
            if resp.status_code not in (200, 201, 204):
                flash(f"Something went wrong saving this report (status {resp.status_code}). Please try again.", "error")
                return redirect(url_for("report"))

            return render_template(
                "report_success.html",
                org=ORG_NAME,
                case_id=case_id,
                urgent=payload["urgency_flag"],
                name=payload["missing_person_name"],
            )
        except Exception as exc:  # noqa: BLE001
            flash(f"Submission failed: {exc}", "error")
            return redirect(url_for("report"))

    return render_template("report.html", org=ORG_NAME)


@app.route("/tip", methods=["GET", "POST"])
def tip():
    if request.method == "POST":
        try:
            payload = {
                "id": str(uuid.uuid4()),
                "related_case": request.form.get("related_case", "").strip(),
                "tip_text": request.form.get("tip_text", "").strip(),
                "contact_info": request.form.get("contact_info", "").strip(),
            }
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/demo_911missing_tips",
                headers=supabase_headers(),
                json=payload,
                timeout=15,
            )
            if resp.status_code not in (200, 201, 204):
                flash(f"Something went wrong saving this tip (status {resp.status_code}). Please try again.", "error")
                return redirect(url_for("tip"))

            return render_template("tip_success.html", org=ORG_NAME)
        except Exception as exc:  # noqa: BLE001
            flash(f"Submission failed: {exc}", "error")
            return redirect(url_for("tip"))

    return render_template("tip.html", org=ORG_NAME)


@app.route("/donate")
def donate():
    return render_template("donate.html", org=ORG_NAME)


ALL_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine",
    "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
    "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming",
]
POPULATED_STATES = {"Wyoming", "Oklahoma", "South Dakota", "Arizona", "Texas"}


@app.route("/resources")
def resources():
    other_states = [s for s in ALL_STATES if s not in POPULATED_STATES]
    return render_template("resources.html", org=ORG_NAME, other_states=other_states)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)

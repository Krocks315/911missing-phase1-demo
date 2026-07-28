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
# Dana Marie Colton is a fully invented demonstration case used to prove the
# end-to-end flow (case page -> sighting/tip forms -> demo admin review view).
# She is NOT a real person and does not represent any real missing-persons case.
DANA_CASE_SLUG = "dana-colton"

SAMPLE_CASES = [
    {
        "name": "Dana Marie Colton",
        "age": 34,
        "last_seen": "Rest stop off Route 12, outside Millbrook Junction (a composite, fictional town) — June 14, 2026",
        "status": "Active Search",
        "status_color": "active",
        "description": "Our one fully fleshed-out sample case, used to demonstrate the "
        "complete flow end to end — case page, sighting reports, and tip submissions. "
        "Entirely fictional. Not a real person.",
        "detail_slug": DANA_CASE_SLUG,
        "featured": True,
    },
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

# Full detail record for the one fully fleshed-out sample case (fictional).
CASE_DETAIL = {
    DANA_CASE_SLUG: {
        "slug": DANA_CASE_SLUG,
        "name": "Dana Marie Colton",
        "age": 34,
        "status": "Active Search",
        "status_color": "active",
        "last_seen_date": "June 14, 2026",
        "last_seen_location": "Rest stop off Route 12, outside Millbrook Junction — a composite, fictional town invented for this demo. Not a real place.",
        "physical_description": "5'6\", medium build, shoulder-length brown hair, brown eyes. "
        "Last seen wearing a gray zip-up jacket and dark jeans.",
        "circumstances": "Was traveling alone by car to visit family and had checked in by "
        "phone the morning of June 14. No contact since that afternoon; her vehicle was "
        "later found parked at the rest stop with no sign of what happened next. Family "
        "reported her missing after two days without contact, which was out of character "
        "for her. There is no indication of where she went from the rest stop or who, if "
        "anyone, she may have been with.",
        "why_public": "This case is shown publicly because visibility and tips from the "
        "public are often the fastest way to develop new leads — someone who saw her at "
        "the rest stop, along Route 12, or afterward may not realize what they saw matters "
        "until they see this page.",
        "fictional_note": "Dana Marie Colton is a composite, invented character created "
        "solely to demonstrate how a case page works. \"Route 12\" and \"Millbrook Junction\" "
        "are fictional and do not correspond to any real road or town. This does not "
        "describe a real person or a real event.",
    }
}

# Fabricated demo submissions shown on the admin-review mockup for Dana's case.
# Invented data only — illustrates what a staff reviewer screen would show.
DEMO_ADMIN_SUBMISSIONS = [
    {
        "kind": "Sighting",
        "submitted": "June 16, 2026 · 9:42 AM",
        "submitter": "Anonymous (no contact info provided)",
        "location": "QuikTrip on Route 12, ~4 miles east of the rest stop (fictional, composite location)",
        "notes": "Reported seeing a woman matching the description getting into a dark "
        "sedan around 6 PM on June 14. Did not get a plate number.",
        "photo": "No photo attached",
        "review_status": "Pending triage",
    },
    {
        "kind": "Tip",
        "submitted": "June 17, 2026 · 2:15 PM",
        "submitter": "M. Alvarez — (555) 010-0142 (demo contact)",
        "location": "N/A",
        "notes": "Says Dana mentioned car trouble in a text the morning of June 14 and "
        "planned to stop for gas near Millbrook Junction.",
        "photo": "N/A",
        "review_status": "Pending triage",
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


@app.route("/cases/<slug>")
def case_detail(slug):
    case = CASE_DETAIL.get(slug)
    if not case:
        return redirect(url_for("cases"))
    return render_template("case_detail.html", case=case, org=ORG_NAME)


@app.route("/cases/<slug>/admin-review")
def case_admin_review(slug):
    case = CASE_DETAIL.get(slug)
    if not case:
        return redirect(url_for("cases"))
    return render_template(
        "admin_review.html",
        case=case,
        submissions=DEMO_ADMIN_SUBMISSIONS,
        org=ORG_NAME,
    )


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


@app.route("/sighting", methods=["GET", "POST"])
def sighting():
    if request.method == "POST":
        try:
            photo_path = None
            photo = request.files.get("photo")
            if photo and photo.filename:
                ext = os.path.splitext(photo.filename)[1] or ".jpg"
                object_name = f"sighting-{uuid.uuid4()}{ext}"
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

            lat = request.form.get("latitude", "").strip()
            lon = request.form.get("longitude", "").strip()
            location_source = request.form.get("location_source", "none").strip() or "none"

            # "When did you see them?" — witness-entered, distinct from the
            # auto-captured submission time (device_timestamp / created_at).
            # Optional: if a witness reporting in real time leaves it blank,
            # default to "just now" so no one is forced to fill it in.
            sighting_occurred_raw = request.form.get("sighting_occurred_at", "").strip()
            if sighting_occurred_raw:
                try:
                    # datetime-local input format: "YYYY-MM-DDTHH:MM"
                    sighting_occurred_at = datetime.fromisoformat(sighting_occurred_raw).isoformat()
                except ValueError:
                    sighting_occurred_at = datetime.utcnow().isoformat()
            else:
                sighting_occurred_at = datetime.utcnow().isoformat()

            sighting_id = str(uuid.uuid4())
            payload = {
                "id": sighting_id,
                "device_timestamp": request.form.get("device_timestamp", "").strip() or None,
                "sighting_occurred_at": sighting_occurred_at,
                "description": request.form.get("description", "").strip(),
                "location_text": request.form.get("location_text", "").strip() or None,
                "latitude": float(lat) if lat else None,
                "longitude": float(lon) if lon else None,
                "location_source": location_source,
                "related_case": request.form.get("related_case", "").strip() or None,
                "reporter_contact": request.form.get("reporter_contact", "").strip() or None,
                "photo_path": photo_path,
                "status": "new_demo_submission",
            }

            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/demo_911missing_sightings",
                headers=supabase_headers(),
                json=payload,
                timeout=15,
            )
            if resp.status_code not in (200, 201, 204):
                flash(f"Something went wrong saving this sighting report (status {resp.status_code}). Please try again.", "error")
                return redirect(url_for("sighting"))

            return render_template(
                "sighting_success.html",
                org=ORG_NAME,
                sighting_id=sighting_id,
                had_photo=bool(photo_path),
                location_source=location_source,
                sighting_occurred_at=sighting_occurred_at,
            )
        except Exception as exc:  # noqa: BLE001
            flash(f"Submission failed: {exc}", "error")
            return redirect(url_for("sighting"))

    return render_template("sighting.html", org=ORG_NAME)


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


@app.route("/how-this-works")
def how_this_works():
    return render_template("how_this_works.html", org=ORG_NAME)


@app.route("/partners")
def partners():
    return render_template("partners.html", org=ORG_NAME)


@app.route("/about")
def about():
    return render_template("about.html", org=ORG_NAME)


@app.route("/security")
def security():
    return render_template("security.html", org=ORG_NAME)


@app.route("/privacy")
def privacy():
    return render_template("privacy.html", org=ORG_NAME)


@app.route("/terms")
def terms():
    return render_template("terms.html", org=ORG_NAME)


@app.route("/nonprofit-status")
def nonprofit_status():
    return render_template("nonprofit_status.html", org=ORG_NAME)


@app.route("/data-retention")
def data_retention():
    return render_template("data_retention.html", org=ORG_NAME)


@app.route("/law-enforcement-partnership")
def law_enforcement_partnership():
    return render_template("law_enforcement.html", org=ORG_NAME)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)

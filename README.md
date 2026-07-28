# 911Missing / Find The Missing — Phase 1 Demo

This is a **DEMO / PROTOTYPE** built to show Phase 1 (the website phase) of the
proposal for 911Missing (possibly renaming to Find The Missing / Find Me Now).

**This is not the production app.** No real missing-persons case data or real
personal information is stored here — every case shown is invented/placeholder
content, clearly labeled.

## What's here

- Mission/home page
- Sample case listing (3 clearly-fake placeholder cases)
- "Report Someone Missing" intake form — functional, stores to Supabase
- Tip/contact submission form — functional, stores to Supabase
- "Report a Sighting" form — functional, stores to Supabase; captures an
  optional photo, an auto-captured device timestamp, geolocation (with a
  manual text-entry fallback when location access is denied or on desktop),
  and a description. Lands in an admin-reviewable queue only — not yet
  auto-linked to a specific case (Phase 2).
- Donate page (styled placeholder — no real payment processing in the demo)

## Stack

- Flask (Python), server-rendered templates
- Supabase (Postgres + Storage) for form storage — isolated demo-only tables
  (`demo_911missing_reports`, `demo_911missing_tips`, `demo_911missing_sightings`)
  and an isolated storage bucket (`demo-911missing-photos`). Insert-only anon
  access; no public read access to submitted data.
- Deployed on Vercel, connected to this GitHub repo for auto-deploy. Vercel
  auto-detects the Flask `app` instance in `app.py` — no custom `vercel.json`
  build config needed (per Vercel's current Flask deployment docs).

## Environment variables (set in Vercel, never committed)

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY` (anon/publishable key only — never the service role key)
- `SECRET_KEY` (Flask session secret)
- `ORG_NAME` (defaults to "Find The Missing")

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SUPABASE_URL=...
export SUPABASE_ANON_KEY=...
python3 app.py
```

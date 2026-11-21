# Remaining team tasks

Only what the three team members still have to do. Hard deadline in the assignment: **22.11.2026**.

## 1. Fill in the report (placeholders on the cover page)

- [ ] Open `docs/FINAL_PROJECT_REPORT.md` and replace the bracketed items on the cover: group number, faculty guide, submission date, GitHub URL, video URL, the three member names, the three college IDs and each member's individual contribution. Nothing else in the report is a placeholder.
- [ ] Rebuild the PDF: install Pandoc, XeLaTeX and `pip install pillow`, then run `python docs/tools/build_report.py`. If you cannot install them, edit the cover in the PDF's source by another route or ask for help.
- [ ] Read the report once. Adjust the learning outcomes in Section 8.2 and sign the declaration if your course asks.

## 2. GitHub repository (not done)

```powershell
cd path\to\I-ITSM
git init
git add .
git commit -m "I-ITSM final submission"
git branch -M main
git remote add origin https://github.com/<your-account>/<repository>.git
git push -u origin main
```

- [ ] Create an empty repository on GitHub first (no README, no .gitignore) and add your lecturer if the course requires it.
- [ ] On the repository page confirm that `node_modules`, `.venv`, `*.db` and `.env` are **not** there (`.gitignore` already excludes them).
- [ ] Each member should commit under their own name if contributions are checked. Put the repository link in the report and in the course spreadsheet.

## 3. Demonstration video (not done)

- [ ] Length **15 to 20 minutes**, all three members on camera, each introducing themselves and explaining a module.
- [ ] Show the three workflows from the assignment: (1) employee reports, system prioritises, technician assigned, notification generated; (2) technician investigates, SLA monitored, incident resolved, user notified; (3) several similar incidents reported, duplicates and related incidents identified, escalation shown.
- [ ] Also show the Settings page, audit log, reports, one class diagram and `python -m pytest`. Demo logins are in `README.md`.
- [ ] File name: the assignment says `<GroupNo>_OOP_S1_2025-2026_Project` but the course header says 2026-2027. Ask your instructor which to use.

## 4. Checks only you can do

- [ ] Run the README Windows steps on your own machines (README section 1). Then run `python -m pytest -q` and `npm run build`. The report marks TC-30 (tests on Windows) as NOT EXECUTED, so update it if you run it.
- [ ] Optional: walk through the manual UI checks: wrong password, 3-character title rejected, 300 affected users raises the impact, duplicate warning, resolve without root cause rejected, another user's incident refused, front-end server stopped shows "Cannot reach the server" (TC-29, also NOT EXECUTED; with only the back end stopped the message is "Request failed (500).", see the finding in Section 3.2 of the technology report), phone-width menu, sign out.
- [ ] **Capture the test-evidence screenshots** listed in `docs/SCREENSHOT_CHECKLIST.md` (31 in total, the ones marked Must are the minimum). Save them as `docs/screenshots/evidence/SS-01.png` and so on. Then run `python docs/tools/build_tech_report.py` and `python docs/tools/build_report.py docs/TECHNOLOGY_SELECTION_REPORT.md docs/TECHNOLOGY_SELECTION_REPORT.pdf "I-ITSM technology selection report" "Technology selection report"`. The images appear in Section 6.7 automatically.
- [ ] If you really run TC-29 or TC-30, open `docs/tools/build_test_cases.py`, change the entry in the list `M` (status `PASS`, and write what you observed in the actual-result text), then rerun `python docs/tools/build_test_cases.py` (main report), `python docs/tools/build_tech_report.py` and the two PDF builds. Never mark a case PASS before it was executed.
- [ ] Fill in the cover placeholders of `docs/TECHNOLOGY_SELECTION_REPORT.md` too (group number, faculty guide, date, repository URL, three names and college IDs), then rebuild its PDF.
- [ ] Optional: retake screenshots in `docs/screenshots/` from your own machine, keep the file names and rebuild the PDF.
- [ ] Decide about the four open `npm audit` advisories (report Section 6.6). Fixing them needs major upgrades and a full interface check.
- [ ] Optional cosmetic fix: `frontend/src/pages/IncidentDetail.jsx` (about line 48) adds a second "Workload x/y" line to each recommendation (report Section 7.4).


## Submission report (I-ITSM_PROJECT_REPORT.pdf)

- [ ] Put the GitHub link and the video link on the cover. Either send them to the assistant, or write them in `docs/report_links.txt` (`REPO_URL=` and `VIDEO_URL=`) and run `python docs/tools/build_master.py` (needs pandoc and XeLaTeX).
- [ ] Optional: SS-07 shows the priority preview empty because no service was chosen when it was taken. Retake it with the service Campus Wi-Fi selected (score 27, P2) and replace `docs/screenshots/evidence/SS-07.png`, then rebuild. The caption already describes the current screenshot honestly.
- [ ] Optional: run TC-29 (stop the front-end server, click Sign in, screenshot SS-29) and change TC-29 in `M` of `docs/tools/build_test_cases.py`, then rerun `build_test_cases.py`, `build_tech_report.py` and `build_master.py`.
- TC-30 was executed on Windows on 20 November 2026 (screenshot SS-31) and is recorded as PASS.

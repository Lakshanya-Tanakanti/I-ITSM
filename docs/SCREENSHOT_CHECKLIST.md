# I-ITSM screenshot checklist (31 screenshots)

This checklist tells you exactly which screenshots to capture as evidence for the test chapter of the report. Nothing here is captured for you, the images must come from your own running system. Every expected result below was checked on 19 November 2026 against the real code and a freshly seeded database. Where a number can differ on your computer, the text says so.

**How it fits the report.** Chapter 6 of `docs/TECHNOLOGY_SELECTION_REPORT.md` has Table 6.6 and 31 figure placeholders (Figure 6.1 to Figure 6.31). Figure 6.N belongs to screenshot SS-N. When you save an image as `docs\screenshots\evidence\SS-NN.png`, the report picks it up automatically (see "After capturing" at the end). One screenshot supports several test cases, so you do not need a picture for every test case.

**Priority column.** *Must* screenshots are the minimum that proves the six required test categories. *Recommended* ones strengthen the evidence. *Optional* ones can be skipped if you are short of time. If you only have time for the Must set, that is acceptable.

| Screenshot | What it shows | Priority | Supports |
|------|---------------------------|--------|-----------|
| SS-01 | Administrator signs in, administrator menu | Must | TC-01, TC-20 |
| SS-02 | Employee menu has no admin pages | Must | TC-20 |
| SS-03 | Technician menu | Optional | TC-20 |
| SS-04 | Invalid login message | Must | TC-10 |
| SS-05 | Technician refused when reporting an incident | Must | TC-19, TC-20 |
| SS-06 | Employee refused another employee's incident | Must | TC-18 |
| SS-07 | Report form with category suggestion and priority preview | Must | TC-02, TC-22 |
| SS-08 | Affected users raise the impact | Recommended | TC-28, TC-22 |
| SS-09 | Duplicate warning panel | Must | TC-26 |
| SS-10 | Incident reported dialog, still created | Must | TC-02, TC-26 |
| SS-11 | Incident detail: priority, SLA deadlines, timeline | Must | TC-02, TC-23, TC-24 |
| SS-12 | Technician recommendations with reasons | Must | TC-04 |
| SS-13 | No eligible technician | Recommended | TC-15, TC-16 |
| SS-14 | Technician acknowledges | Must | TC-03 |
| SS-15 | Resolve dialog with a missing field | Recommended | TC-13 |
| SS-16 | Incident resolved with resolution details | Must | TC-05 |
| SS-17 | Employee verification dialog | Must | TC-05 |
| SS-18 | Closed incident with feedback and timeline | Must | TC-05, TC-24 |
| SS-19 | SLA monitor with breach and violation history | Must | TC-23 |
| SS-20 | Audit log filtered by one incident | Must | TC-24 |
| SS-21 | E-mail outbox (simulated e-mail) | Recommended | TC-25 |
| SS-22 | Administrator dashboard | Must | Dashboards requirement |
| SS-23 | Reports page with CSV buttons | Must | Reports requirement |
| SS-24 | Downloaded CSV file opened | Recommended | Reports requirement |
| SS-25 | Settings page, strategy selection | Optional | Admin operations, strategies |
| SS-26 | API refuses an illegal status change (409) | Must | TC-14 |
| SS-27 | API reports an unknown incident (404) | Recommended | Invalid incident scenario |
| SS-28 | API names missing fields (422) | Must | TC-11 |
| SS-29 | Network failure message, front-end server stopped | Recommended | TC-29 |
| SS-30 | Back end stopped, message shown | Optional | TC-29, Section 3.2 finding |
| SS-31 | Test run output in PowerShell | Must | TC-01 to TC-27, TC-30 |

---

## General preparation (do this once, about 15 minutes)

1. **Start both servers** as in the README (section 1): window 1 `python -m uvicorn app.main:app --port 8000` inside `backend` with the virtual environment active, window 2 `npm run dev` inside `frontend`.
2. **Start from clean demo data.** To get the same incidents as this checklist, stop the backend with Ctrl+C, run `python -m app.utils.seed --reset` inside `backend`, then start the backend again. Do the reset shortly before you capture (the demo incidents are created relative to the time of the reset, and the SLA states change as time passes).
3. **Open Chrome or Edge** at http://localhost:5173. Maximise the window and set the zoom to 100 percent (Ctrl+0). Close other tabs and hide bookmarks so no personal information is visible.
4. **How to take a screenshot on Windows:** press `Win + Shift + S`, drag a rectangle around the browser content (include the address bar when the steps say so), and release. The image is on the clipboard and a notification appears: click it, then use the save icon, or paste into Paint and save. Save as **PNG** with the exact name given in each section, for example `SS-04.png`, in the folder `docs\screenshots\evidence` of the project.
5. **Do not edit the images.** Do not draw on them or blur anything. Crop only.
6. **Demo accounts** (also in the README): administrator `admin@iitsm.example.com` / `Admin@123`. Technicians `arjun.kapoor@iitsm.example.com`, `meera.joshi@iitsm.example.com`, `vikram.singh@iitsm.example.com` / `Tech@1234`. Employees `rahul.verma@iitsm.example.com`, `sneha.iyer@iitsm.example.com`, `karan.malhotra@iitsm.example.com`, `divya.nair@iitsm.example.com` / `Employee@123`. On the login page you can click a line under "Development demo accounts" to fill the form.
7. **Switching accounts:** click your name at the top right, choose **Sign out**, confirm **Sign out**, then sign in as the next account.
8. **Incident numbers.** The demo data has INC-1001 to INC-1012. The incidents you create get the next numbers (INC-1013, INC-1014 if you follow the order below). If your number differs, use the number your screen shows.
9. **Follow the order below.** Later screenshots use incidents created or changed earlier.

---

## SS-01: Administrator signs in, administrator menu

- **Priority:** Must
- **Supports:** TC-01, TC-20
- **Caption:** Successful sign-in as the administrator, with the full administrator menu (Administration and Governance sections).
- **Account:** Administrator
- **Page:** http://localhost:5173/login, then the dashboard
- **Steps:**
  1. Open http://localhost:5173/login.
  2. Click the line `Admin: admin@iitsm.example.com` under "Development demo accounts", then click **Sign in**.
  3. Wait for the dashboard to load.
- **Must be visible:** The page titled with the administrator dashboard, your name at the top right, and the left menu with the groups **Overview**, **Administration** (Users, Technicians and teams, Services, Categories, SLA policies, Settings) and **Governance** (Audit log, E-mail outbox). Include the address bar showing `localhost:5173`.
- **File name:** `docs\screenshots\evidence\SS-01.png`
- **Insert in report:** Section 6.7, Figure 6.1, next to TC-01 and TC-20 in Table 6.4.

## SS-02: Employee menu has no admin pages

- **Priority:** Must
- **Supports:** TC-20
- **Caption:** The employee sees a reduced menu without administration pages, which shows role-based access.
- **Account:** Employee Rahul Verma
- **Page:** The employee dashboard
- **Steps:**
  1. Sign out of the administrator account (see preparation step 7).
  2. On the login page click the line `Employee: rahul.verma@iitsm.example.com`, then **Sign in**.
- **Must be visible:** The employee dashboard and a menu that contains only Overview (Dashboard, Report incident, My incidents) and Account (Notifications, Profile). There must be no Administration or Governance group.
- **File name:** `docs\screenshots\evidence\SS-02.png`
- **Insert in report:** Section 6.7, Figure 6.2, next to TC-20.

## SS-03: Technician menu

- **Priority:** Optional
- **Supports:** TC-20
- **Caption:** The technician menu offers the incident queue and profile, but no administration pages.
- **Account:** Technician Arjun Kapoor
- **Page:** The technician dashboard
- **Steps:**
  1. Sign out, then click the line `Technician: arjun.kapoor@iitsm.example.com` and **Sign in**.
- **Must be visible:** The technician dashboard (My workload, queue) and a menu with Work (My dashboard, Incident queue, Report incident) and Account (Notifications, Profile and availability).
- **File name:** `docs\screenshots\evidence\SS-03.png`
- **Insert in report:** Section 6.7, Figure 6.3.

## SS-04: Invalid login message

- **Priority:** Must
- **Supports:** TC-10
- **Caption:** A wrong password is refused with a clear message and no session is created.
- **Account:** None (signed out)
- **Page:** http://localhost:5173/login
- **Steps:**
  1. Sign out so that you see the login page.
  2. Type the e-mail `admin@iitsm.example.com` and the wrong password `WrongPass1`.
  3. Click **Sign in**.
- **Must be visible:** The login form with a red alert reading **Incorrect e-mail address or password.** You stay on the login page.
- **File name:** `docs\screenshots\evidence\SS-04.png`
- **Insert in report:** Section 6.7, Figure 6.4, next to TC-10 (Section 3.2, invalid login).

## SS-05: Technician refused when reporting an incident

- **Priority:** Must
- **Supports:** TC-19, TC-20
- **Caption:** A technician who tries to report an incident is refused by the server, an example of an unauthorised operation.
- **Account:** Technician Arjun Kapoor
- **Page:** Report incident
- **Steps:**
  1. Sign in as `arjun.kapoor@iitsm.example.com` (password `Tech@1234`).
  2. Click **Report incident** in the left menu.
  3. Title: `Technician test incident`. Description: `This should be refused for a technician account.` Affected service: `Library System`. Leave the other fields.
  4. Click **Submit incident**.
- **Must be visible:** A red alert inside the "Incident details" card reading **Technicians cannot report incidents. Use an employee account.** (the server answers HTTP 403, code PERMISSION_DENIED).
- **File name:** `docs\screenshots\evidence\SS-05.png`
- **Insert in report:** Section 6.7, Figure 6.5, next to TC-19 and TC-20 (Section 3.2, unauthorised operation).

## SS-06: Employee refused another employee's incident

- **Priority:** Must
- **Supports:** TC-18
- **Caption:** An employee cannot open an incident reported by a colleague, the server answers with access denied.
- **Account:** Employee Rahul Verma
- **Page:** The incident INC-1011 (reported by Divya Nair)
- **Steps:**
  1. Sign in as `rahul.verma@iitsm.example.com`.
  2. In the browser address bar type `localhost:5173/incidents/INC-1011` and press Enter.
- **Must be visible:** The error panel titled **Could not load data** with the text **You do not have access to this incident.** and a **Try again** button. Include the address bar showing `/incidents/INC-1011`.
- **File name:** `docs\screenshots\evidence\SS-06.png`
- **Insert in report:** Section 6.7, Figure 6.6, next to TC-18.

## SS-07: Report form with category suggestion and priority preview

- **Priority:** Must
- **Supports:** TC-02, TC-22
- **Caption:** The report form suggests a category from the text and previews the calculated priority with its formula.
- **Account:** Employee Karan Malhotra
- **Page:** Report incident
- **Steps:**
  1. Sign in as `karan.malhotra@iitsm.example.com` (password `Employee@123`).
  2. Click **Report incident**.
  3. Title: `Wifi not connecting in hostel`. Description: `The wireless network drops and I cannot connect to the router.`
  4. Affected service: `Campus Wi-Fi`. Leave Impact `3 - Medium` and Urgency `3 - Medium`. Wait about one second.
  5. Take the screenshot **before** you click Submit.
  6. Then click **Submit incident**, and in the dialog click **Open incident**. Keep this tab for SS-11.
- **Must be visible:** On the right, the card **Priority preview** with the score **27**, the badge P2 and the text `3 x 3 x 3 = 27 -> P2 (High)`, and the card **Category suggestion** with **Network** and the matched words (network, wifi, router).
- **File name:** `docs\screenshots\evidence\SS-07.png`
- **Insert in report:** Section 6.7, Figure 6.7, next to TC-02 and TC-22.

## SS-08: Affected users raise the impact

- **Priority:** Recommended
- **Supports:** TC-28, TC-22
- **Caption:** A large number of affected users raises the impact rating, and the preview explains why.
- **Account:** Employee Karan Malhotra
- **Page:** Report incident (do not submit)
- **Steps:**
  1. Click **Report incident** again.
  2. Title: `Library catalogue is slow`. Description: `Searching the catalogue takes a long time for everybody.`
  3. Affected service: `Library System`. Impact `2 - Low`, Urgency `2 - Low`. In **Users affected (optional)** type `300`.
  4. Wait one second and take the screenshot. Do not submit. Click **Cancel**.
- **Must be visible:** The Priority preview showing score **16**, badge P3, the text `Impact raised from 2 to 4 because 300 users are affected. 4 x 2 x 2 = 16 -> P3 (Medium)` and the blue note that the number of affected users raised the impact rating to 4.
- **File name:** `docs\screenshots\evidence\SS-08.png`
- **Insert in report:** Section 6.7, Figure 6.8, next to TC-28.

## SS-09: Duplicate warning panel

- **Priority:** Must
- **Supports:** TC-26
- **Caption:** While the employee types, the system warns about similar open incidents but still allows submission.
- **Account:** Employee Karan Malhotra
- **Page:** Report incident
- **Steps:**
  1. Click **Report incident**.
  2. Title: `Payment page not working for customers`. Description: `Customers cannot complete payments, the payment application keeps failing.`
  3. Affected service: `Payment Gateway`. Impact `4 - High`, Urgency `5 - Very high`. Wait about one second.
  4. Take the screenshot **before** submitting. Then click **Submit incident** (needed for SS-10).
- **Must be visible:** The card **Possible duplicates** with a yellow warning (`Similar open incidents exist. Check them before submitting. You can still continue.`) listing INC-1012 and INC-1010 with their percentage similarity (about 68 percent and 51 percent). Also the Priority preview showing `4 x 5 x 5 = 100 -> P1 (Critical)`.
- **File name:** `docs\screenshots\evidence\SS-09.png`
- **Insert in report:** Section 6.7, Figure 6.9, next to TC-26 (Section 3.2, duplicate incident).

## SS-10: Incident reported dialog, still created

- **Priority:** Must
- **Supports:** TC-02, TC-26
- **Caption:** The incident is created and assigned automatically, and the dialog repeats the duplicate warning without blocking.
- **Account:** Employee Karan Malhotra
- **Page:** The dialog that appears after you submit the payment incident
- **Steps:**
  1. Submit the form from SS-09.
  2. When the dialog **Incident reported** appears, take the screenshot. Then click **Open incident**.
- **Must be visible:** The heading with the new number (INC-1014 if you followed this order), the P1 badge, the sentence that it was assigned (for example `Assigned to Meera Joshi.`), and the yellow text `Possible duplicates: INC-1012, INC-1010. The incident was still created.` (the numbers listed can differ slightly from the panel in SS-09 because the server also compares categories).
- **File name:** `docs\screenshots\evidence\SS-10.png`
- **Insert in report:** Section 6.7, Figure 6.10, next to TC-26.

## SS-11: Incident detail with priority, SLA deadlines and timeline

- **Priority:** Must
- **Supports:** TC-02, TC-23, TC-24
- **Caption:** The incident page shows the calculated priority, the SLA response and resolution deadlines, and the timeline of automatic classification and assignment.
- **Account:** Employee Karan Malhotra
- **Page:** The Wi-Fi incident from SS-07 (INC-1013 if you followed this order)
- **Steps:**
  1. Click **My incidents** and open the incident titled `Wifi not connecting in hostel`.
  2. Scroll so that the SLA card and the Timeline card are both visible.
- **Must be visible:** The incident number with badges for P2 priority (score 27), status and SLA state, the **SLA** card with Response and Resolution bars and the policy name (starts with `Standard P2`), and the **Timeline** card with entries for creation, classification as Network, priority calculation and automatic assignment.
- **File name:** `docs\screenshots\evidence\SS-11.png`
- **Insert in report:** Section 6.7, Figure 6.11, next to TC-02, TC-23 and TC-24.

## SS-12: Technician recommendations with reasons

- **Priority:** Must
- **Supports:** TC-04
- **Caption:** The administrator sees ranked technician recommendations with scores and reasons, and can change the strategy.
- **Account:** Administrator
- **Page:** The Wi-Fi incident from SS-07
- **Steps:**
  1. Sign in as the administrator.
  2. Click **All incidents** and open `Wifi not connecting in hostel`.
  3. Scroll to the card **Reassign technician**.
- **Must be visible:** The **Recommendation strategy** drop-down (default `Skill then load (balanced)`), at least two ranked technicians (`#1`, `#2`) with a **Score**, bullet reasons and `Workload x/y`, a green **Currently assigned** badge on one of them, and the line `N not eligible (admin may override)`.
- **File name:** `docs\screenshots\evidence\SS-12.png`
- **Insert in report:** Section 6.7, Figure 6.12, next to TC-04.

## SS-13: No eligible technician

- **Priority:** Recommended
- **Supports:** TC-15, TC-16
- **Caption:** When nobody is eligible the incident stays unassigned and the administrator can only assign with an explicit, audited override.
- **Account:** Administrator
- **Page:** INC-1009 (Storage quota exceeded, unassigned)
- **Steps:**
  1. Click **All incidents** and open `INC-1009` (`Storage quota exceeded for the research department`).
  2. In the card **Assign technician** click the line `5 not eligible (admin may override)` to expand it.
- **Must be visible:** The yellow warning `No technician is eligible. Use an override below.` and the expanded list with reasons such as `Lacks the Storage skill` and `Marked unavailable` (Imran Khan), each with an **Override** button.
- **File name:** `docs\screenshots\evidence\SS-13.png`
- **Insert in report:** Section 6.7, Figure 6.13, next to TC-15 and TC-16.

## SS-14: Technician acknowledges

- **Priority:** Must
- **Supports:** TC-03
- **Caption:** The assigned technician acknowledges the incident and the status and timeline change.
- **Account:** Technician Vikram Singh
- **Page:** INC-1011 (Library self-checkout kiosk screen is frozen)
- **Steps:**
  1. Sign out, then sign in as `vikram.singh@iitsm.example.com` (password `Tech@1234`, type it, there is no demo button for him).
  2. Click **Incident queue** and open `INC-1011`.
  3. Click the blue **Acknowledge** button.
  4. Take the screenshot after the page updates.
- **Must be visible:** The status badge **Acknowledged**, a green toast or updated timeline entry for the acknowledgement with Vikram Singh as the actor, and the next action button **Start investigation**.
- **File name:** `docs\screenshots\evidence\SS-14.png`
- **Insert in report:** Section 6.7, Figure 6.14, next to TC-03.

## SS-15: Resolve dialog with a missing field

- **Priority:** Recommended
- **Supports:** TC-13
- **Caption:** The resolve dialog will not accept a resolution without both the summary and the root cause.
- **Account:** Technician Meera Joshi
- **Page:** INC-1010 (Payment application is unavailable)
- **Steps:**
  1. Sign out, then sign in as `meera.joshi@iitsm.example.com` (the demo line `Technician (apps)`).
  2. Click **Incident queue**, open `INC-1010`, click the green **Resolve** button.
  3. In **Resolution summary** type `Restarted the payment service.` Leave **Root cause** empty.
  4. Take the screenshot with the dialog open.
- **Must be visible:** The dialog **Resolve incident** with the summary filled, the root cause empty and the **Resolve** button greyed out (disabled). The server also refuses this case, which is proved by TC-13.
- **File name:** `docs\screenshots\evidence\SS-15.png`
- **Insert in report:** Section 6.7, Figure 6.15, next to TC-13.

## SS-16: Incident resolved with resolution details

- **Priority:** Must
- **Supports:** TC-05
- **Caption:** The technician resolves the incident with a summary and root cause, which are stored and shown on the incident.
- **Account:** Technician Meera Joshi
- **Page:** INC-1010
- **Steps:**
  1. In the same dialog type **Root cause**: `The payment service ran out of connections.`
  2. Click **Resolve**.
  3. Scroll to the **Resolution** card and take the screenshot.
- **Must be visible:** The status badge **Resolved**, the **Resolution** card with Summary, Root cause and Resolved by Meera Joshi, and the timeline entry for the resolution.
- **File name:** `docs\screenshots\evidence\SS-16.png`
- **Insert in report:** Section 6.7, Figure 6.16, next to TC-05.

## SS-17: Employee verification dialog

- **Priority:** Must
- **Supports:** TC-05
- **Caption:** The employee who reported the incident confirms that the problem is fixed.
- **Account:** Employee Rahul Verma (he reported INC-1010)
- **Page:** INC-1010
- **Steps:**
  1. Sign out, sign in as `rahul.verma@iitsm.example.com`.
  2. Click **My incidents**, open `INC-1010`.
  3. Click the green **Verify resolution** button. The dialog **Verify resolution** opens.
  4. Take the screenshot with the dialog open, then click **Yes, it is fixed**.
- **Must be visible:** The dialog with the text `Confirm that the problem is fixed and you can work normally again?`, with the incident page and the **Resolution** card behind it.
- **File name:** `docs\screenshots\evidence\SS-17.png`
- **Insert in report:** Section 6.7, Figure 6.17, next to TC-05.

## SS-18: Closed incident with feedback and timeline

- **Priority:** Must
- **Supports:** TC-05, TC-24
- **Caption:** The incident is verified and closed, the employee rates the resolution, and the timeline records every step.
- **Account:** Employee Rahul Verma
- **Page:** INC-1010
- **Steps:**
  1. After verifying, click the **Close incident** button and confirm with **Close incident** in the dialog.
  2. In the card **How did we do?** click the fourth star, type `Fixed quickly.` and click **Submit feedback**.
  3. Scroll so that the **Employee feedback** card and the **Timeline** are visible, then take the screenshot.
- **Must be visible:** The status badge **Closed**, the **Employee feedback** card with the stars, and the **Timeline** with entries for assignment, acknowledgement, start of work, resolution, verification and closure in time order.
- **File name:** `docs\screenshots\evidence\SS-18.png`
- **Insert in report:** Section 6.7, Figure 6.18, next to TC-05 and TC-24.

## SS-19: SLA monitor with breach and violation history

- **Priority:** Must
- **Supports:** TC-23
- **Caption:** The SLA monitor lists incidents at risk or breached and keeps the history of recorded violations.
- **Account:** Administrator
- **Page:** SLA monitor
- **Steps:**
  1. Sign in as the administrator and click **SLA monitor**.
  2. Click **Run check now** and wait for the toast `Checked ... incident(s)`.
  3. Take the screenshot showing both cards.
- **Must be visible:** The statistic tiles, the card **Incidents needing attention** listing at least INC-1012 (P1, response breached), and the card **SLA violation history** with at least one RESPONSE violation. If the history looks empty, wait one minute and press **Run check now** again.
- **File name:** `docs\screenshots\evidence\SS-19.png`
- **Insert in report:** Section 6.7, Figure 6.19, next to TC-23.

## SS-20: Audit log filtered by one incident

- **Priority:** Must
- **Supports:** TC-24
- **Caption:** The audit log shows who did what to the incident and when, with the previous and new states.
- **Account:** Administrator
- **Page:** Audit log
- **Steps:**
  1. Click **Audit log**.
  2. In the **Incident** box type `INC-1010` and press Enter (or wait for the list to refresh).
- **Must be visible:** The page subtitle `Append-only record of every important action`, the filter box showing INC-1010, and rows for the actions in order (created, assigned, acknowledged, in progress, resolved, verified, closed) with actor names and times.
- **File name:** `docs\screenshots\evidence\SS-20.png`
- **Insert in report:** Section 6.7, Figure 6.20, next to TC-24.

## SS-21: E-mail outbox (simulated e-mail)

- **Priority:** Recommended
- **Supports:** TC-25
- **Caption:** Every notification also produces a simulated e-mail record, nothing is sent over the network.
- **Account:** Administrator
- **Page:** E-mail outbox
- **Steps:**
  1. Click **E-mail outbox**.
- **Must be visible:** The subtitle `Simulated e-mail. Nothing is sent over the network ...` and a list of messages with recipients, subjects and a delivery status.
- **File name:** `docs\screenshots\evidence\SS-21.png`
- **Insert in report:** Section 6.7, Figure 6.21, next to TC-25.

## SS-22: Administrator dashboard

- **Priority:** Must
- **Supports:** Dashboards requirement (Chapter 5 of the main report)
- **Caption:** The administrator dashboard summarises open incidents, SLA state and workload from live database data.
- **Account:** Administrator
- **Page:** Dashboard
- **Steps:**
  1. Click **Dashboard** in the left menu and wait for the charts to appear.
- **Must be visible:** The statistic tiles and the charts (created versus resolved, by priority, by status, by service).
- **File name:** `docs\screenshots\evidence\SS-22.png`
- **Insert in report:** Section 6.7, Figure 6.22.

## SS-23: Reports page with CSV buttons

- **Priority:** Must
- **Supports:** Reports requirement (Chapter 5 of the main report)
- **Caption:** The reports page presents live figures and offers CSV export for the tables.
- **Account:** Administrator
- **Page:** Reports
- **Steps:**
  1. Click **Reports**. Leave the period on the default.
  2. Scroll so that at least two cards with the **CSV** button are visible.
- **Must be visible:** The title **Reports**, the subtitle `All figures are calculated live from the database.`, the cards **Incidents by service** or **Technician workload** each with a **CSV** button.
- **File name:** `docs\screenshots\evidence\SS-23.png`
- **Insert in report:** Section 6.7, Figure 6.23.

## SS-24: Downloaded CSV file opened

- **Priority:** Recommended
- **Supports:** Reports requirement
- **Caption:** The exported CSV file opens as an ordinary spreadsheet with the report rows.
- **Account:** Administrator
- **Page:** Reports, then the downloaded file
- **Steps:**
  1. On the Reports page click the **CSV** button of **Incidents by service**. Your browser downloads `by-service.csv`.
  2. Open the file from the Downloads folder (Excel or Notepad).
- **Must be visible:** The file name in the title bar and the header row with the rows of data below it.
- **File name:** `docs\screenshots\evidence\SS-24.png`
- **Insert in report:** Section 6.7, Figure 6.24.

## SS-25: Settings page, strategy selection

- **Priority:** Optional
- **Supports:** Administrator operations, Strategy pattern (TC-04 context)
- **Caption:** An administrator switches the assignment and priority strategies without changing code.
- **Account:** Administrator
- **Page:** Settings
- **Steps:**
  1. Click **Settings**.
  2. Change **Assignment strategy** to `Load based`, click **Save settings**, wait for the confirmation.
  3. Change it back to `Skill then load (balanced)` and save again after the screenshot.
- **Must be visible:** The card **Strategies** with the selected strategy and its description, and the confirmation toast.
- **File name:** `docs\screenshots\evidence\SS-25.png`
- **Insert in report:** Section 6.7, Figure 6.25.

## SS-26: API refuses an illegal status change (409)

- **Priority:** Must
- **Supports:** TC-14
- **Caption:** The server refuses a transition from Assigned to Closed with a conflict response and an explanatory error code.
- **Account:** Administrator, using the API documentation page
- **Page:** http://localhost:8000/docs
- **Steps:**
  1. Open http://localhost:8000/docs in a new tab (the backend must be running).
  2. Find `POST /api/auth/login`, click it, click **Try it out**. In the body replace the example with `{"email": "admin@iitsm.example.com", "password": "Admin@123"}` and click **Execute**.
  3. In the response body copy the long text after `"access_token":` (without the quotation marks).
  4. Scroll to the top, click the green **Authorize** button, paste the text into the **Value** box, click **Authorize**, then **Close**.
  5. Find `POST /api/incidents/{number}/transition`, click **Try it out**. Set **number** to `INC-1012`. Replace the body with `{"to_status": "CLOSED"}`. Click **Execute**.
  6. Scroll to the **Server response** area and take the screenshot.
- **Must be visible:** Response code **409** and a body with `"detail": "Cannot move an incident from ASSIGNED to CLOSED."` and `"code": "INVALID_STATE_TRANSITION"` (the statuses in your message depend on the current state of INC-1012, ASSIGNED unless someone changed it). Include the request URL line above the response.
- **File name:** `docs\screenshots\evidence\SS-26.png`
- **Insert in report:** Section 6.7, Figure 6.26, next to TC-14 (Section 3.2, invalid state transition).

## SS-27: API reports an unknown incident (404)

- **Priority:** Recommended
- **Supports:** Invalid incident scenario (Section 3.2)
- **Caption:** A request for an incident number that does not exist returns not found with the code INCIDENT_NOT_FOUND.
- **Account:** Administrator, still authorised on the API documentation page
- **Page:** http://localhost:8000/docs
- **Steps:**
  1. Find `GET /api/incidents/{number}`, click **Try it out**.
  2. Set **number** to `INC-9999` and click **Execute**.
  3. Take the screenshot of the response.
- **Must be visible:** Response code **404** and the body `"detail": "Incident INC-9999 was not found."` with `"code": "INCIDENT_NOT_FOUND"`.
- **File name:** `docs\screenshots\evidence\SS-27.png`
- **Insert in report:** Section 6.7, Figure 6.27.

## SS-28: API names missing fields (422)

- **Priority:** Must
- **Supports:** TC-11
- **Caption:** Missing or invalid fields are rejected with a validation error that names every offending field.
- **Account:** Administrator, still authorised on the API documentation page
- **Page:** http://localhost:8000/docs
- **Steps:**
  1. Find `POST /api/incidents`, click **Try it out**.
  2. Replace the body with `{"title": "abc"}` and click **Execute**.
  3. Take the screenshot of the response.
- **Must be visible:** Response code **422** and a body with `"code": "VALIDATION_ERROR"`, a `detail` text such as `title: String should have at least 5 characters; description: Field required; ...` and the `errors` list naming the fields.
- **File name:** `docs\screenshots\evidence\SS-28.png`
- **Insert in report:** Section 6.7, Figure 6.28, next to TC-11.

## SS-29: Network failure message, front-end server stopped

- **Priority:** Recommended
- **Supports:** TC-29
- **Caption:** When the browser cannot reach any server, the application shows a readable message instead of a blank page.
- **Account:** None
- **Page:** The login page that is already open
- **Steps:**
  1. Sign out so that the login page is open in a tab. Do not close or refresh the tab.
  2. In the PowerShell window that runs `npm run dev` press **Ctrl+C** to stop the front-end server.
  3. In the open tab type any e-mail and password and click **Sign in**.
  4. Take the screenshot.
  5. Start the front end again with `npm run dev`.
- **Must be visible:** A red alert reading **Cannot reach the server. Is the backend running on port 8000?** and the login page still displayed. This is the message the code produces when no response arrives. If your browser shows something different, take the screenshot anyway and report what you saw instead of changing the report text.
- **File name:** `docs\screenshots\evidence\SS-29.png`
- **Insert in report:** Section 6.7, Figure 6.29, next to TC-29. After you capture it, tell your teammate to change TC-29 from NOT EXECUTED to PASS in `docs/tools/build_test_cases.py` (see MANUAL_TASKS.md).

## SS-30: Back end stopped, message shown

- **Priority:** Optional
- **Supports:** TC-29 and the finding in Section 3.2
- **Caption:** With only the back end stopped, the development proxy answers with an error and the application shows a short failure message.
- **Account:** None
- **Page:** The login page
- **Steps:**
  1. Make sure the front end is running and the login page is open.
  2. In the PowerShell window of the back end press **Ctrl+C** to stop it.
  3. In the browser type any e-mail and password and click **Sign in**.
  4. Take the screenshot, then start the back end again.
- **Must be visible:** A red alert reading **Request failed (500).** This is the behaviour documented as a finding in Section 3.2 of the report: the clearer message appears only when no response arrives at all.
- **File name:** `docs\screenshots\evidence\SS-30.png`
- **Insert in report:** Section 6.7, Figure 6.30.

## SS-31: Test run output in PowerShell

- **Priority:** Must
- **Supports:** TC-01 to TC-27 (the automated cases), TC-30 if run on Windows
- **Caption:** Output of the complete automated test suite, all tests passing.
- **Account:** None
- **Page:** A PowerShell window
- **Steps:**
  1. Stop the backend with Ctrl+C (or open a third PowerShell window).
  2. Inside the `backend` folder with the virtual environment active, run `python -m pytest -q`.
  3. Wait until the last line appears (about one to two minutes).
- **Must be visible:** The command, the progress dots, and the final line `264 passed` (a warnings count between 0 and 6 is normal). The window title or prompt should show a Windows path if you ran it on Windows.
- **File name:** `docs\screenshots\evidence\SS-31.png`
- **Insert in report:** Section 6.7, Figure 6.31, next to TC-01 to TC-27. If you ran it on Windows, also tell your teammate to change TC-30 to PASS.

---

## After capturing

1. Put all the PNG files in `docs\screenshots\evidence` with the names `SS-01.png` to `SS-31.png`. Skipped screenshots stay as grey placeholder lines in the report.
2. From the project root in PowerShell run:

```
python docs\tools\build_tech_report.py
python docs\tools\build_report.py docs\TECHNOLOGY_SELECTION_REPORT.md docs\TECHNOLOGY_SELECTION_REPORT.pdf "I-ITSM technology selection report" "Technology selection report"
```

3. Open `docs\TECHNOLOGY_SELECTION_REPORT.pdf` and check that every image is readable and in the right place. The first command also re-runs the tests, so it takes one to two minutes.
4. If the build tools (Pandoc, XeLaTeX) are not installed on your computer, put the images in the Markdown report by hand instead: replace each grey placeholder line by `![Figure 6.N: caption](screenshots/evidence/SS-NN.png)` and export the Markdown to PDF with your usual tool.

## Reading the evidence honestly

* The screenshots show the system working. The automated tests (Table 6.4) are the main evidence for the six test categories. Do not describe a screenshot as an automated test.
* SS-29, SS-30 and the Windows part of SS-31 turn the not-executed cases TC-29 and TC-30 into executed ones. Do not mark those cases PASS until you really performed them.
* The demo incidents (INC-1001 to INC-1012) were created by the seed script, not by hand. Say so if a reader asks.

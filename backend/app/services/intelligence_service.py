"""Intelligent features (all rule based, transparent and local):

1. Category suggestion       - keyword matching against configured category keywords
2. Duplicate detection       - normalised token similarity (warn only, BR-14)
3. Technician recommendation - see AssignmentService / strategies
4. SLA risk detection        - explainable LOW / MEDIUM / HIGH rules
5. Incident correlation      - incidents on the same service in a short window
6. Suggested resolution      - resolutions of similar historical incidents
"""
from datetime import timedelta
from typing import Optional

from app.domain.enums import DONE_STATUSES, OPEN_STATUSES, IncidentStatus, Priority, RiskLevel, SlaStatus
from app.models import Incident
from app.utils.text import jaccard, keyword_hits, tokens

DUPLICATE_WINDOW_DAYS = 7
CORRELATION_WINDOW_HOURS = 24


class IntelligenceService:
    def __init__(self, repos, clock, settings_service, sla_service):
        self.repos = repos
        self.clock = clock
        self.settings_service = settings_service
        self.sla = sla_service

    # ------------------------------------------------------------------ 1. category suggestion
    def suggest_category(self, title: str, description: str) -> dict:
        scored = []
        for category in self.repos.categories.list(only_active=True):
            matched, score = [], 0
            for keyword in category.keyword_list:
                hit = keyword_hits(title, description, keyword)
                if hit:
                    matched.append(keyword)
                    score += hit + (1 if " " in keyword else 0)
            if score:
                scored.append((score, category, matched))
        scored.sort(key=lambda r: (-r[0], r[1].name))
        results = [{
            "category_id": c.id, "category_name": c.name, "score": s,
            "confidence": round(s / (s + 3), 2), "matched_keywords": m,
            "reason": f"Matched keyword(s): {', '.join(m)}",
        } for s, c, m in scored[:3]]
        return {"suggestion": results[0] if results else None, "alternatives": results[1:]}

    # ------------------------------------------------------------------ 2. duplicate detection
    def similarity(self, a_title, a_desc, a_service, a_cat, b: Incident) -> tuple:
        title_a, title_b = tokens(a_title), tokens(b.title)
        all_a, all_b = tokens(f"{a_title} {a_desc}"), tokens(f"{b.title} {b.description}")
        text_sim = 0.65 * jaccard(title_a, title_b) + 0.35 * jaccard(all_a, all_b)
        same_service = bool(a_service and a_service == b.service_id)
        same_category = bool(a_cat and a_cat == b.category_id)
        score = min(1.0, text_sim * 0.75 + (0.15 if same_service else 0) + (0.10 if same_category else 0))
        shared = sorted(title_a & title_b or all_a & all_b)
        reasons = []
        if shared:
            reasons.append("Shared terms: " + ", ".join(shared[:6]))
        if same_service:
            reasons.append("Same service")
        if same_category:
            reasons.append("Same category")
        return round(score, 2), reasons

    def find_duplicates(self, title: str, description: str, service_id: Optional[int],
                        category_id: Optional[int] = None, exclude_id: Optional[int] = None,
                        limit: int = 5) -> list:
        threshold = self.settings_service.duplicate_threshold()
        since = self.clock.now() - timedelta(days=DUPLICATE_WINDOW_DAYS)
        matches = []
        for other in self.repos.incidents.recent(since, exclude_id=exclude_id):
            score, reasons = self.similarity(title, description, service_id, category_id, other)
            if score >= threshold:
                matches.append({"incident": other, "similarity": score, "reasons": reasons})
        matches.sort(key=lambda m: -m["similarity"])
        return matches[:limit]

    def duplicates_for(self, incident: Incident) -> list:
        return self.find_duplicates(incident.title, incident.description, incident.service_id,
                                    incident.category_id, exclude_id=incident.id)

    # ------------------------------------------------------------------ 4. SLA risk
    def sla_risk(self, incident: Incident, workload: Optional[dict] = None) -> dict:
        """Explainable risk rules (higher points = more likely to breach).

        points = % of the active SLA window already used
               +20 when nobody is assigned
               +10 for P1/P2 incidents
               +10 when the assigned technician is at their workload limit
               +15 when the technician acknowledged but has not started and 50% of the time is gone
        HIGH >= 75 or already breached, MEDIUM >= 50, otherwise LOW.
        """
        if incident.status in DONE_STATUSES:
            return {"level": RiskLevel.LOW.value, "points": 0, "reasons": ["Incident is already resolved."]}
        info = self.sla.describe(incident)
        phase = info["response"] if info["response"]["pending"] else info["resolution"]
        label = "response" if info["response"]["pending"] else "resolution"
        pct = phase["elapsed_percent"]
        points, reasons = pct, [f"{pct:.0f}% of the {label} time is used"]
        if info["overall"] == SlaStatus.BREACHED.value:
            return {"level": RiskLevel.HIGH.value, "points": round(max(points, 100)),
                    "reasons": ["An SLA deadline has already been breached."] + reasons}
        if incident.assigned_technician_id is None:
            points += 20
            reasons.append("No technician is assigned (+20)")
        if incident.priority in (Priority.P1, Priority.P2):
            points += 10
            reasons.append(f"{incident.priority.value} priority leaves little slack (+10)")
        if incident.assigned_technician_id and workload is not None:
            profile = incident.assigned_technician.technician_profile if incident.assigned_technician else None
            if profile and workload.get(incident.assigned_technician_id, 0) >= profile.workload_limit:
                points += 10
                reasons.append("Assigned technician is at the workload limit (+10)")
        if incident.status == IncidentStatus.ACKNOWLEDGED and pct >= 50:
            points += 15
            reasons.append("Acknowledged but investigation has not started and 50% of the time is gone (+15)")
        level = RiskLevel.HIGH if points >= 75 else RiskLevel.MEDIUM if points >= 50 else RiskLevel.LOW
        return {"level": level.value, "points": round(points), "reasons": reasons}

    # ------------------------------------------------------------------ 5. correlation
    def related(self, incident: Incident) -> dict:
        since = incident.created_at - timedelta(hours=CORRELATION_WINDOW_HOURS)
        peers = self.repos.incidents.open_for_service(incident.service_id, incident.id, since)
        peers = [p for p in peers if abs((p.created_at - incident.created_at).total_seconds()) <= CORRELATION_WINDOW_HOURS * 3600]
        rows = [{"incident": p, "reason": f"Also reported on {incident.service.name} within "
                                          f"{CORRELATION_WINDOW_HOURS} hours"} for p in peers]
        total = len(rows) + 1
        summary = None
        if total >= 3:
            summary = (f"{total} incidents were reported for {incident.service.name} within "
                       f"{CORRELATION_WINDOW_HOURS} hours. This may be a single underlying outage.")
        elif total == 2:
            summary = f"Another incident was reported for {incident.service.name}; they may share a cause."
        return {"related": rows, "summary": summary, "service": incident.service.name}

    # ------------------------------------------------------------------ 6. suggested resolution
    def suggested_resolutions(self, incident: Incident, limit: int = 3) -> list:
        mine = tokens(f"{incident.title} {incident.description}")
        out = []
        for other in self.repos.incidents.resolved_with_resolution(incident.category_id, incident.service_id, incident.id):
            if other.resolution is None:
                continue
            theirs = tokens(f"{other.title} {other.description} {other.resolution.summary}")
            sim = jaccard(mine, theirs)
            if sim >= 0.12:
                out.append({
                    "incident_number": other.number, "title": other.title, "similarity": round(sim, 2),
                    "summary": other.resolution.summary, "root_cause": other.resolution.root_cause,
                })
        out.sort(key=lambda r: -r["similarity"])
        return out[:limit]

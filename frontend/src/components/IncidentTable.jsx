import { useNavigate } from "react-router-dom";
import { ArrowDown, ArrowUp, MessageCircleQuestion } from "lucide-react";
import { PriorityBadge, SlaBadge, StatusBadge, RiskBadge } from "./ui";
import { fmtShort } from "../utils";

/** Reusable incident table. `sort` and `onSort` enable sortable headers. */
export default function IncidentTable({ items, sort, onSort, compact }) {
  const nav = useNavigate();
  const col = (key, label) => {
    if (!onSort) return <th>{label}</th>;
    const active = sort === key || sort === `-${key}`;
    return (
      <th className="sortable" onClick={() => onSort(sort === `-${key}` ? key : `-${key}`)} aria-sort={active ? (sort.startsWith("-") ? "descending" : "ascending") : "none"}>
        {label} {active && (sort.startsWith("-") ? <ArrowDown size={12} /> : <ArrowUp size={12} />)}
      </th>
    );
  };
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>
          {col("number", "ID")}<th>Title</th>{col("priority", "Priority")}{col("status", "Status")}
          {!compact && <th>Service</th>}<th>Technician</th><th>SLA</th>{col("created_at", "Created")}
        </tr></thead>
        <tbody>
          {items.map((i) => (
            <tr key={i.id} className="click" onClick={() => nav(`/incidents/${i.number}`)}>
              <td className="mono"><b>{i.number}</b></td>
              <td style={{ maxWidth: 320 }}>
                {i.title}
                {i.awaiting_info && <span title="Waiting for the reporter" className="badge b-amber" style={{ marginLeft: 8 }}><MessageCircleQuestion size={12} />Info needed</span>}
                {i.escalation_level > 0 && <span className="badge b-red" style={{ marginLeft: 6 }}>Escalated L{i.escalation_level}</span>}
              </td>
              <td><PriorityBadge priority={i.priority} score={i.priority_score} /></td>
              <td><StatusBadge status={i.status} /></td>
              {!compact && <td>{i.service?.name}</td>}
              <td>{i.assigned_technician?.full_name || <span className="muted">Unassigned</span>}</td>
              <td><SlaBadge status={i.sla_status} /> {i.risk_level === "HIGH" && !["BREACHED", "MET"].includes(i.sla_status) && <RiskBadge level="HIGH" />}</td>
              <td className="small muted">{fmtShort(i.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

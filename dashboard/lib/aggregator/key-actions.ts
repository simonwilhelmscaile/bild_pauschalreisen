import { PRIORITY_LEVELS, RESPONSIBLE_PARTIES } from "../constants";

export function buildKeyActions(alerts: Record<string, any[]>, appendices: Record<string, any[]>) {
  const actions: any[] = [];

  for (const alert of (alerts.critical || []).slice(0, 3)) {
    const topic = alert.topic_summary || (alert.title || "").slice(0, 80);
    const recommendation = alert.recommendation || "Problem analysieren und beheben";
    const product = alert.product || "";
    actions.push({
      priority: "urgent",
      priority_label: PRIORITY_LEVELS.urgent.label_de,
      priority_color: PRIORITY_LEVELS.urgent.color,
      action: recommendation || `Kritisches Feedback zu ${product} untersuchen`,
      responsible: RESPONSIBLE_PARTIES.support,
      source: alert.source || "",
      source_url: alert.url || "",
      deadline: PRIORITY_LEVELS.urgent.deadline,
      topic,
    });
  }

  for (const alert of (alerts.monitor || []).slice(0, 2)) {
    const topic = alert.topic_summary || (alert.title || "").slice(0, 80);
    actions.push({
      priority: "high",
      priority_label: PRIORITY_LEVELS.high.label_de,
      priority_color: PRIORITY_LEVELS.high.color,
      action: topic ? `Diskussion beobachten: ${topic.slice(0, 60)}` : "Relevante Diskussion verfolgen",
      responsible: RESPONSIBLE_PARTIES.content,
      source: alert.source || "",
      source_url: alert.url || "",
      deadline: PRIORITY_LEVELS.high.deadline,
      topic,
    });
  }

  for (const alert of (alerts.opportunity || []).slice(0, 2)) {
    const topic = alert.topic_summary || (alert.title || "").slice(0, 80);
    const recommendation = alert.recommendation || "";
    actions.push({
      priority: "normal",
      priority_label: PRIORITY_LEVELS.normal.label_de,
      priority_color: PRIORITY_LEVELS.normal.color,
      action: recommendation || `Positive Erwähnung verstärken: ${topic.slice(0, 50)}`,
      responsible: RESPONSIBLE_PARTIES.marketing,
      source: alert.source || "",
      source_url: alert.url || "",
      deadline: PRIORITY_LEVELS.normal.deadline,
      topic,
    });
  }

  for (const q of (appendices.device_questions || []).slice(0, 2)) {
    if ((q.device_relevance_score || 0) >= 0.8) {
      actions.push({
        priority: "high",
        priority_label: PRIORITY_LEVELS.high.label_de,
        priority_color: PRIORITY_LEVELS.high.color,
        action: `Frage beantworten: ${(q.question || "").slice(0, 50)}`,
        responsible: RESPONSIBLE_PARTIES.content,
        source: q.source || "",
        source_url: q.url || "",
        deadline: PRIORITY_LEVELS.high.deadline,
        topic: q.question || "",
      });
    }
  }

  const priorityOrder: Record<string, number> = { urgent: 0, high: 1, normal: 2 };
  actions.sort((a, b) => (priorityOrder[a.priority] ?? 3) - (priorityOrder[b.priority] ?? 3));
  return actions.slice(0, 7);
}

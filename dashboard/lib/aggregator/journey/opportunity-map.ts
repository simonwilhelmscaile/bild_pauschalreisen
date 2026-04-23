export function buildOpportunityMap(
  painLandscape: any[], solutionDist: any[], bridgeMoments: Record<string, any>
) {
  const opportunities: any[] = [];
  for (const pain of painLandscape.slice(0, 5)) {
    if (pain.count < 2) continue;
    opportunities.push({
      opportunity: `Content für ${pain.label_de}`,
      journey_stage: "awareness → consideration",
      pain_category: pain.label_de,
      volume: pain.count,
      action: `Ratgeber-Content zu ${pain.label_de} mit Beurer-Lösungen erstellen`,
    });
  }
  for (const sol of solutionDist) {
    if (sol.beurer_relevant && sol.count >= 2) {
      opportunities.push({
        opportunity: `${sol.label_de} Vergleich/Guide`,
        journey_stage: "comparison",
        pain_category: "Übergreifend",
        volume: sol.count,
        action: `Vergleichscontent für ${sol.label_de} mit Beurer-Produktvorteilen`,
      });
    }
  }
  const bridgeTotal = bridgeMoments.total_detected || 0;
  if (bridgeTotal > 0) {
    const patterns = bridgeMoments.patterns || [];
    const topPattern = patterns.length > 0 ? ` (häufigstes Muster: ${patterns[0].label_de})` : "";
    opportunities.push({
      opportunity: "Brückenmoment-Content",
      journey_stage: "consideration → comparison",
      pain_category: "Übergreifend",
      volume: bridgeTotal,
      action: `${bridgeTotal} Brückenmomente identifiziert${topPattern} — gezielter Content für Nutzer in Lösungssuche`,
    });
  }
  opportunities.sort((a, b) => b.volume - a.volume);
  return opportunities.slice(0, 8);
}

import type { AnalysisSummary } from "@/types/analysis";

interface AnalysisCardProps {
  analysis: AnalysisSummary;
  onSelect: (id: number) => void;
}

export function AnalysisCard({ analysis, onSelect }: AnalysisCardProps) {
  return (
    <div onClick={() => onSelect(analysis.id)}>
      <h3>{analysis.title}</h3>
      <p>{analysis.description ?? "No description"}</p>
      <time>{analysis.created_at}</time>
    </div>
  );
}

// src/lib/mock-data.ts
import type { User, AnalysisSummary, AnalysisDetailed } from "@/types";

export const MOCK_USER: User = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  username: "demo_user",
  role: "user",
  must_change_password: true,
  is_active: true,
};

export const MOCK_ANALYSES: AnalysisSummary[] = [
  {
    id: 1,
    title: "SaaS Master Agreement",
    description: "Enterprise SaaS contract review",
    created_at: "2026-09-15T10:30:00Z",
  },
  {
    id: 2,
    title: "NDA - Acme Corp",
    description: null,
    created_at: "2026-09-14T08:15:00Z",
  },
  {
    id: 3,
    title: "Employment Contract Template",
    description: "Standard employment agreement",
    created_at: "2026-09-12T14:45:00Z",
  },
];

// Detailed analyses keyed to the same ids as MOCK_ANALYSES.
// This simulates GET /api/v1/analysis/{analysis_id}.
export const MOCK_ANALYSIS_DETAILS: AnalysisDetailed[] = [
  {
    id: 1,
    title: "SaaS Master Agreement",
    description: "Enterprise SaaS contract review",
    text: "This Master Services Agreement is entered into as of September 1, 2026...",
    document_type: "Service Agreement",
    document_summary:
      "An enterprise SaaS agreement covering service levels, data processing, liability, and auto-renewal. Broadly standard, but contains a restrictive liability cap and an aggressive auto-renewal clause that warrant negotiation.",
    overall_risk_score: 7,
    recommendations: [
      "Negotiate the limitation of liability cap in Section 8.2.",
      "Add a data-breach carve-out to the liability exclusions.",
      "Extend the auto-renewal notice period from 30 to 90 days.",
    ],
    clauses: [
      {
        id: 1,
        clause_type: "Limitation of Liability",
        summary:
          "Caps total liability at 12 months of fees paid and excludes all indirect and consequential damages.",
        risk_level: "high",
        key_terms: [
          "liability cap",
          "consequential damages",
          "12 months of fees",
        ],
        suggested_actions: [
          "Raise the cap to 24 months of fees.",
          "Carve out data breaches and confidentiality from the exclusion.",
        ],
      },
      {
        id: 2,
        clause_type: "Auto-Renewal",
        summary:
          "Renews automatically for 12-month terms unless cancelled at least 30 days before renewal.",
        risk_level: "average",
        key_terms: ["auto-renewal", "30-day notice", "12-month term"],
        suggested_actions: [
          "Extend the cancellation notice window to 90 days.",
          "Require written renewal confirmation.",
        ],
      },
      {
        id: 3,
        clause_type: "Data Protection",
        summary:
          "Provider will process customer data in accordance with applicable law and maintain standard security measures.",
        risk_level: "low",
        key_terms: ["data processing", "security measures", "applicable law"],
        suggested_actions: ["Attach a Data Processing Agreement (DPA)."],
      },
    ],
    created_at: "2026-09-15T10:30:00Z",
    updated_at: "2026-09-15T10:32:00Z",
  },
  {
    id: 2,
    title: "NDA - Acme Corp",
    description: null,
    text: "This Non-Disclosure Agreement is entered into between the parties...",
    document_type: "Non-Disclosure Agreement",
    document_summary:
      "A mutual non-disclosure agreement. Low overall risk, though the confidentiality period is longer than typical.",
    overall_risk_score: 3,
    recommendations: [
      "Consider reducing the confidentiality period from 7 to 5 years.",
    ],
    clauses: [
      {
        id: 1,
        clause_type: "Confidentiality Period",
        summary:
          "Confidentiality obligations survive for 7 years after termination.",
        risk_level: "average",
        key_terms: ["confidentiality period", "7 years", "survival"],
        suggested_actions: ["Negotiate the period down to 5 years."],
      },
      {
        id: 2,
        clause_type: "Definition of Confidential Information",
        summary:
          "Defines confidential information broadly to include all disclosed materials.",
        risk_level: "low",
        key_terms: ["confidential information", "broad definition"],
        suggested_actions: ["Ensure standard exclusions are present."],
      },
    ],
    created_at: "2026-09-14T08:15:00Z",
    updated_at: "2026-09-14T08:16:00Z",
  },
  {
    id: 3,
    title: "Employment Contract Template",
    description: "Standard employment agreement",
    text: "This Employment Agreement is made between Employer and Employee...",
    document_type: "Employment Agreement",
    document_summary:
      "A standard employment agreement. Contains a non-compete clause that may be unenforceable depending on jurisdiction.",
    overall_risk_score: 5,
    recommendations: [
      "Review the non-compete scope for enforceability in your jurisdiction.",
    ],
    clauses: [
      {
        id: 1,
        clause_type: "Non-Compete",
        summary:
          "Restricts the employee from working with competitors for 24 months within a broad geographic scope.",
        risk_level: "critical",
        key_terms: ["non-compete", "24 months", "geographic scope"],
        suggested_actions: [
          "Narrow the geographic and temporal scope.",
          "Confirm enforceability under local law.",
        ],
      },
    ],
    created_at: "2026-09-12T14:45:00Z",
    updated_at: "2026-09-12T14:46:00Z",
  },
];

// Simulates the API lookup: GET /api/v1/analysis/{id}
export function getMockAnalysisDetail(
  id: number,
): AnalysisDetailed | undefined {
  return MOCK_ANALYSIS_DETAILS.find((analysis) => analysis.id === id);
}

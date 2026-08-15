from pydantic import BaseModel, Field

from app.core.enums import RiskLevel
from app.infrastructure.logging import get_logger

logger = get_logger(__file__)


class LegalClause(BaseModel):
    """Individual legal clause analysis"""

    clause_type: str = Field(
        description="Type of clause (e.g., 'indemnification', 'termination', 'liability', 'confidentiality')"
    )
    summary: str = Field(description="Brief summary of what this clause does")
    risk_level: RiskLevel
    key_terms: list[str] = Field(
        description="List of important terms or phrases in this clause"
    )
    suggested_actions: list[str] = Field(
        description="Recommended actions or negotiation points"
    )


class LegalDocumentAnalysis(BaseModel):
    """Complete legal document analysis response structure"""

    document_summary: str = Field(
        description="Overall summary of the document's purpose and key points"
    )
    document_type: str = Field(
        description="Type of legal document (e.g., 'NDA', 'Employment Contract', 'Service Agreement')"
    )
    overall_risk_score: int = Field(
        description="Overall risk score from 1-10 (10 being highest risk)",
        ge=1,
        le=10,  # Add validation
    )
    clauses: list[LegalClause]
    recommendations: list[str] = Field(
        description="Overall recommendations for the document"
    )

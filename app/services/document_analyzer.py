import json
import re
from typing import Optional

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.core.config import setting
from app.infrastructure.logging import get_logger
from app.infrastructure.openai.schemas import LegalDocumentAnalysis

logger = get_logger(__name__)


class LegalDocumentAnalyzer:
    """Service for analyzing legal documents using OpenAI"""

    def __init__(
        self,
        client: Optional[AsyncOpenAI] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_document_length: int = 15000,
    ):
        self.client = client or AsyncOpenAI(
            base_url=setting.OPENAI_BASE_URL, api_key=setting.OPENAI_API_KEY
        )
        self.model = model or setting.LLM_MODEL_NAME
        self.max_document_length = max_document_length

        # Build system prompt including schema
        schema_str = json.dumps(LegalDocumentAnalysis.model_json_schema(), indent=2)
        self.system_prompt = (
            system_prompt
            or f"""You are a highly experienced legal document analyst with expertise in corporate law,
contract negotiation, and risk assessment. Your role is to analyze legal documents thoroughly and provide
structured, actionable insights.

When analyzing documents:
1. Identify and categorize all key clauses
2. Assess risks at both clause-level and document-level
3. Highlight critical issues that could have significant legal/financial implications
4. Provide practical recommendations for negotiation or improvement
5. Consider jurisdiction-specific regulations when relevant
6. Flag ambiguous or vague language that could lead to disputes

Always maintain a professional, objective tone and base your analysis on standard legal practices.
For each clause, assess the risk level based on industry standards and common legal precedents.

CRITICAL: Return your response as a valid JSON object ONLY. Do not include any other text, explanations, or markdown formatting.
The JSON must exactly match this schema:
{schema_str}
"""
        )

    def _truncate_document(self, document_text: str) -> str:
        """Truncate document to safe length, trying to cut at paragraph boundaries"""
        if len(document_text) <= self.max_document_length:
            return document_text

        truncated = document_text[: self.max_document_length]
        last_paragraph = truncated.rfind("\n\n")
        if last_paragraph > self.max_document_length * 0.8:
            truncated = truncated[:last_paragraph]

        logger.warning(
            f"Document truncated from {len(document_text)} to {len(truncated)} characters"
        )
        return truncated + "\n\n[Document truncated due to length...]"

    def _build_user_prompt(self, document_text: str) -> str:
        """Build the user prompt with truncated document"""
        truncated_doc = self._truncate_document(document_text)
        return f"""
Please analyze the following legal document in detail:

---DOCUMENT START---
{truncated_doc}
---DOCUMENT END---

Provide a comprehensive analysis covering all key clauses, risks, and recommendations.
Ensure your analysis is structured and actionable.
"""

    def _extract_json_from_response(self, content: str) -> str:
        """
        Extract JSON from the response content.
        Handles markdown code blocks and plain JSON.
        """
        # Try to find JSON in markdown code blocks
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            return json_match.group(1)

        # Try to find JSON object directly (greedy but safe)
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            return json_match.group(0)

        # If no JSON found, return original content (will fail parsing)
        return content

    async def analyze(
        self,
        document_text: str,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        **kwargs,
    ) -> LegalDocumentAnalysis:
        """
        Analyze a legal document with retry logic and proper error handling.
        """
        user_prompt = self._build_user_prompt(document_text)

        try:
            # Make the API call WITHOUT response_format
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,  # allow additional parameters
            )

            response_content = response.choices[0].message.content

            if response_content is None:
                raise ValueError("No response content from LLM provider")

            # Extract JSON from the response
            json_str = self._extract_json_from_response(response_content)

            # Validate and parse with Pydantic
            validated_analysis = LegalDocumentAnalysis.model_validate_json(json_str)

            logger.info(
                f"Successfully analyzed document. "
                f"Risk score: {validated_analysis.overall_risk_score}/10, "
                f"Clauses found: {len(validated_analysis.clauses)}"
            )

            return validated_analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(
                f"Raw content (first 500 chars): {response_content[:500] if response_content else 'None'}"
            )
            raise ValueError(f"Invalid JSON response from LLM: {e}")

        except ValidationError as e:
            logger.error(f"Pydantic validation error: {e}")
            raise ValidationError(f"Response didn't match expected schema: {e}")

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

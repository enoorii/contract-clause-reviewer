# app/repositories/analysis_repository.py

from typing import Sequence, cast
from uuid import UUID

from sqlalchemy.orm import InstrumentedAttribute, selectinload
from sqlalchemy.orm.interfaces import ORMOption
from sqlmodel import asc, col, desc, func, select

from app.core.filters.analysis import AnalysisFilters, AnalysisSortBy, Sort
from app.db.database import DBSession
from app.models.models import Analysis, Clause

# ============== Private Query Builder Functions ==============


def _apply_filters_to_query(stm, filters: AnalysisFilters, user_id: UUID):
    """Apply all filters to the query."""
    # Always filter by user
    stm = stm.where(Analysis.user_id == user_id)

    # Search filter (by title)
    if filters.search:
        search_pattern = f"%{filters.search}%"
        stm = stm.where(col(Analysis.title).ilike(search_pattern))

    # Document type filter
    if filters.document_type:
        stm = stm.where(Analysis.document_type == filters.document_type)

    # Risk score filters
    if filters.min_risk_score is not None:
        stm = stm.where(Analysis.overall_risk_score >= filters.min_risk_score)
    if filters.max_risk_score is not None:
        stm = stm.where(Analysis.overall_risk_score <= filters.max_risk_score)

    # Date filters
    if filters.from_date:
        stm = stm.where(Analysis.created_at >= filters.from_date)
    if filters.to_date:
        stm = stm.where(Analysis.created_at <= filters.to_date)

    return stm


def _apply_ordering_to_query(stm, filters: AnalysisFilters):
    """Apply sorting/ordering to the query."""
    # Map sort_by to ORM column
    sort_by_map = {
        AnalysisSortBy.CREATED_AT: Analysis.created_at,
        AnalysisSortBy.TITLE: Analysis.title,
        AnalysisSortBy.OVERALL_RISK_SCORE: Analysis.overall_risk_score,
        AnalysisSortBy.DOCUMENT_TYPE: Analysis.document_type,
    }

    order_col = sort_by_map.get(
        filters.sort_by or AnalysisSortBy.CREATED_AT, Analysis.created_at
    )

    if filters.sort == Sort.ASC:
        return stm.order_by(asc(order_col))
    else:
        return stm.order_by(desc(order_col))


# ============== Public Repository Functions ==============


async def create_analysis_repo(
    user_id: UUID,
    task_id: str,
    title: str,
    text: str,
    document_summary: str,
    document_type: str,
    overall_risk_score: int,
    recommendations: list[str],
    db: DBSession,
    description: str | None = None,
) -> Analysis:
    """Create a completed analysis record."""
    analysis = Analysis(
        user_id=user_id,
        task_id=task_id,
        title=title,
        description=description,
        text=text,
        document_summary=document_summary,
        document_type=document_type,
        overall_risk_score=overall_risk_score,
        recommendations=recommendations,
    )
    db.add(analysis)
    await db.flush()
    return analysis


async def create_clauses_repo(
    analysis_id: int,
    clauses_data: list[dict],
    db: DBSession,
) -> list[Clause]:
    """Bulk create Clause records."""
    clauses = [
        Clause(
            analysis_id=analysis_id,
            clause_type=item["clause_type"],
            summary=item["summary"],
            risk_level=item["risk_level"],
            key_terms=item.get("key_terms", []),
            suggested_actions=item.get("suggested_actions", []),
        )
        for item in clauses_data
    ]
    db.add_all(clauses)
    await db.flush()
    return clauses


async def get_analysis_by_task_id_repo(
    task_id: str, db: DBSession, options: list[ORMOption] | None = None
) -> Analysis | None:
    """Retrieve analysis by Celery task ID."""
    stm = select(Analysis).where(Analysis.task_id == task_id)
    if options is not None:
        stm = stm.options(*options)
    result = await db.exec(stm)
    return result.first()


async def get_analysis_by_id_repo(
    analysis_id: int, db: DBSession, options: list[ORMOption] | None = None
) -> Analysis | None:
    """Retrieve analysis with clauses eager loaded."""
    stm = select(Analysis).where(Analysis.id == analysis_id)
    if options is not None:
        stm = stm.options(*options)

    result = await db.exec(stm)
    return result.first()


async def get_user_analyses_count_repo(
    filters: AnalysisFilters,
    user_id: UUID,
    db: DBSession,
) -> int:
    """Get total count of analyses matching filters."""
    stm = select(Analysis)
    stm = _apply_filters_to_query(stm, filters, user_id)
    count_stm = select(func.count()).select_from(stm.subquery())
    return await db.scalar(count_stm) or 0


async def get_user_analyses_repo(
    filters: AnalysisFilters,
    user_id: UUID,
    db: DBSession,
) -> Sequence[Analysis]:
    """List analyses for a user with filtering, ordering, and pagination."""
    stm = select(Analysis)
    stm = _apply_filters_to_query(stm, filters, user_id)
    stm = _apply_ordering_to_query(stm, filters)

    if filters.page and filters.size:
        stm = stm.offset((filters.page - 1) * filters.size).limit(filters.size)

    result = await db.exec(stm)
    return result.all()


async def get_distinct_document_types_repo(
    user_id: UUID,
    db: DBSession,
) -> Sequence[str]:
    """Get distinct document types for the user for filter dropdown."""
    stm = (
        select(Analysis.document_type)
        .where(Analysis.user_id == user_id)
        .where(Analysis.document_type != "")
        .distinct()
        .order_by(Analysis.document_type)
    )
    result = await db.exec(stm)
    return result.all()


async def get_analysis_by_report_task_id(
    task_id: str, db: DBSession
) -> Analysis | None:
    options = [selectinload(cast(InstrumentedAttribute, Analysis.clauses))]

    """Retrieve analysis by report_task_id."""
    stmt = select(Analysis).where(Analysis.report_task_id == task_id).options(*options)
    result = await db.exec(stmt)
    return result.one_or_none()

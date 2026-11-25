import json
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import httpx
from loguru import logger

from app.core.config import settings

# __file__ = .../backend/app/retrieval/eval_full.py
# .parent * 3 = .../backend
# ещё .parent = корень проекта
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EVAL_DIR = _PROJECT_ROOT / "eval"

EVAL_SET_PATH = EVAL_DIR / "eval_set.json"
REPORT_PATH = EVAL_DIR / "eval_report.md"
RAW_RESULTS_PATH = EVAL_DIR / "eval_raw.json"

RAG_URL = "http://localhost:8000/chat"


@dataclass
class EvalQuestion:
    id: int
    type: str
    question: str
    expected_keywords: list[str]
    answerable: bool


@dataclass
class EvalResult:
    question: EvalQuestion
    best_score: float
    abstained: bool
    grounded: bool
    citations_count: int
    invalid_citation_markers: int
    answer_preview: str
    retrieval_ms: float
    generation_ms: float
    matched_keywords: list[str]
    model: str


def load_eval_set() -> list[EvalQuestion]:
    with EVAL_SET_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [EvalQuestion(**q) for q in data["questions"]]


def run_question(q: EvalQuestion) -> EvalResult:
    """Отправляет вопрос в RAG и собирает метрики."""
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(RAG_URL, json={"question": q.question, "top_k": 5})
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"Failed to run question {q.id}: {e}")
        return EvalResult(
            question=q,
            best_score=0.0,
            abstained=True,
            grounded=False,
            citations_count=0,
            invalid_citation_markers=0,
            answer_preview="ERROR",
            retrieval_ms=0.0,
            generation_ms=0.0,
            matched_keywords=[],
            model="none",
        )

    answer = data.get("answer", "")
    best_score = max((c["score"] for c in data.get("citations", [])), default=0.0)
    
    # Проверяем, есть ли хотя бы один expected_keyword в ответе
    answer_lower = answer.lower()
    matched = [kw for kw in q.expected_keywords if kw.lower() in answer_lower]

    return EvalResult(
        question=q,
        best_score=best_score,
        abstained=data.get("abstained", False),
        grounded=data.get("grounded", False),
        citations_count=len(data.get("citations", [])),
        invalid_citation_markers=data.get("invalid_citation_markers", 0),
        answer_preview=answer[:200].replace("\n", " "),
        retrieval_ms=data.get("retrieval_ms", 0.0),
        generation_ms=data.get("generation_ms", 0.0),
        matched_keywords=matched,
        model=data.get("model", "unknown"),
    )


def evaluate_retrieval(results: list[EvalResult]) -> dict[str, float]:
    """Метрика 1: retrieval_hit для answerable вопросов.
    
    Считаем hit, если:
    - best_score >= MIN_RELEVANCE_SCORE (не отсечён порогом)
    - хотя бы один expected_keyword есть в ответе
    """
    answerable = [r for r in results if r.question.answerable]
    if not answerable:
        return {"retrieval_hit_rate": 0.0, "total": 0}

    hits = sum(
        1 for r in answerable
        if r.best_score >= settings.MIN_RELEVANCE_SCORE and len(r.matched_keywords) > 0
    )
    return {
        "retrieval_hit_rate": hits / len(answerable),
        "hits": hits,
        "total": len(answerable),
    }


def evaluate_abstention(results: list[EvalResult]) -> dict[str, float]:
    """Метрика 2: false_abstention_rate для answerable вопросов.
    
    Считаем долю вопросов, которые были отсечены порогом (best_score < threshold).
    """
    answerable = [r for r in results if r.question.answerable]
    if not answerable:
        return {"false_abstention_rate": 0.0, "total": 0}

    false_abstentions = sum(
        1 for r in answerable
        if r.best_score < settings.MIN_RELEVANCE_SCORE
    )
    return {
        "false_abstention_rate": false_abstentions / len(answerable),
        "false_abstentions": false_abstentions,
        "total": len(answerable),
    }


def evaluate_grounding(results: list[EvalResult]) -> dict[str, float]:
    """Метрика 3: grounding_accuracy для trap и off-topic.
    
    Считаем долю вопросов, где abstained=true (система отказалась отвечать).
    """
    non_answerable = [r for r in results if not r.question.answerable]
    if not non_answerable:
        return {"grounding_accuracy": 0.0, "total": 0}

    correct_abstentions = sum(1 for r in non_answerable if r.abstained)
    return {
        "grounding_accuracy": correct_abstentions / len(non_answerable),
        "correct": correct_abstentions,
        "total": len(non_answerable),
    }


def evaluate_citations(results: list[EvalResult]) -> dict[str, float]:
    """Метрика 4: citation_validity для answerable вопросов.
    
    Считаем долю вопросов, где invalid_citation_markers=0.
    """
    answerable = [r for r in results if r.question.answerable and not r.abstained]
    if not answerable:
        return {"citation_validity": 0.0, "total": 0}

    valid = sum(1 for r in answerable if r.invalid_citation_markers == 0)
    return {
        "citation_validity": valid / len(answerable),
        "valid": valid,
        "total": len(answerable),
    }


def generate_report(results: list[EvalResult], metrics: dict) -> str:
    """Генерирует Markdown-отчёт с разбивкой по типам вопросов."""
    lines = [
        "# Eval Report",
        "",
        f"**Дата:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Всего вопросов:** {len(results)}",
        f"**MIN_RELEVANCE_SCORE:** {settings.MIN_RELEVANCE_SCORE}",
        "",
        "## Метрики",
        "",
        "| Метрика | Значение | Детали |",
        "|---|---|---|",
    ]

    for key, val in metrics.items():
        if isinstance(val, dict) and "total" in val:
            pct = val.get(f"{key}_rate", val.get("rate", 0.0)) * 100
            detail = f"{val.get('hits', val.get('correct', val.get('valid', 0)))} / {val['total']}"
            lines.append(f"| {key} | {pct:.1f}% | {detail} |")

    lines.extend([
        "",
        "## Разбивка по типам вопросов",
        "",
    ])

    by_type = defaultdict(list)
    for r in results:
        by_type[r.question.type].append(r)

    for qtype in ["fact", "aggregate", "paraphrase", "trap", "off-topic"]:
        group = by_type.get(qtype, [])
        if not group:
            continue

        lines.append(f"### {qtype.upper()} ({len(group)} вопросов)")
        lines.append("")
        lines.append("| # | Вопрос | Score | Abstained | Grounded | Keywords | Preview |")
        lines.append("|---|---|---|---|---|---|---|")

        for r in sorted(group, key=lambda x: x.question.id):
            q = r.question
            score = f"{r.best_score:.4f}" if r.best_score > 0 else "—"
            abstained = "✓" if r.abstained else "✗"
            grounded = "✓" if r.grounded else "✗"
            keywords = ", ".join(q.expected_keywords[:3]) if q.expected_keywords else "—"
            preview = r.answer_preview[:60] + "..." if len(r.answer_preview) > 60 else r.answer_preview
            lines.append(f"| {q.id} | {q.question[:50]} | {score} | {abstained} | {grounded} | {keywords} | {preview} |")

        lines.append("")

    # Слабые места
    lines.extend([
        "## Слабые места",
        "",
    ])

    weak = [r for r in results if r.question.answerable and (r.abstained or not r.matched_keywords)]
    if weak:
        lines.append(f"**{len(weak)} вопросов с проблемами:**")
        lines.append("")
        for r in weak[:10]:
            q = r.question
            reason = "abstained" if r.abstained else "no keywords matched"
            lines.append(f"- **{q.id}** ({q.type}): {q.question} — {reason}, score={r.best_score:.4f}")
    else:
        lines.append("Слабых мест не обнаружено ✓")

    lines.append("")
    return "\n".join(lines)


def main():
    logger.info("Loading eval set...")
    questions = load_eval_set()
    logger.info(f"Loaded {len(questions)} questions")

    results = []
    for i, q in enumerate(questions, 1):
        logger.info(f"[{i}/{len(questions)}] Running: {q.question[:60]}...")
        result = run_question(q)
        results.append(result)
        logger.info(
            f"  → score={result.best_score:.4f}, abstained={result.abstained}, "
            f"keywords={len(result.matched_keywords)}/{len(q.expected_keywords)}"
        )

    # Сохраняем raw results
    raw_data = [
        {
            "id": r.question.id,
            "type": r.question.type,
            "question": r.question.question,
            "best_score": r.best_score,
            "abstained": r.abstained,
            "grounded": r.grounded,
            "citations_count": r.citations_count,
            "invalid_citation_markers": r.invalid_citation_markers,
            "answer_preview": r.answer_preview,
            "matched_keywords": r.matched_keywords,
            "model": r.model,
        }
        for r in results
    ]
    EVAL_DIR.mkdir(parents=True, exist_ok=True)    
    RAW_RESULTS_PATH.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Raw results saved to {RAW_RESULTS_PATH}")

    # Считаем метрики
    metrics = {
        "retrieval_hit": evaluate_retrieval(results),
        "false_abstention": evaluate_abstention(results),
        "grounding": evaluate_grounding(results),
        "citation_validity": evaluate_citations(results),
    }

    # Генерируем отчёт
    report = generate_report(results, metrics)
    REPORT_PATH.write_text(report, encoding="utf-8")
    logger.info(f"Report saved to {REPORT_PATH}")

    # Выводим summary
    logger.info("=" * 60)
    logger.info("EVAL SUMMARY")
    logger.info("=" * 60)
    for key, val in metrics.items():
        if isinstance(val, dict) and "total" in val:
            pct = val.get(f"{key}_rate", val.get("rate", 0.0)) * 100
            detail = val.get("hits", val.get("correct", val.get("valid", 0)))
            logger.info(f"{key:25s}: {pct:5.1f}% ({detail}/{val['total']})")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
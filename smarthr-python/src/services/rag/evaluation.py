"""RAG evaluation service with optional Ragas execution and local fallback."""

import json
import math
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config import settings
from src.services.rag.pipeline import rag_pipeline
from src.services.rag.schemas import (
    RagEvaluationRequest,
    RagEvaluationResponse,
    RagEvaluationSample,
    RagEvaluationSampleResult,
    RagSearchRequest,
)


METRIC_KEYS = ["faithfulness", "answerRelevancy", "contextPrecision", "contextRecall"]


class RagEvaluationService:
    """Run sample-based RAG evaluation and keep the latest Python-side result."""

    def __init__(self):
        self._latest: Optional[RagEvaluationResponse] = None

    def latest(self) -> Optional[RagEvaluationResponse]:
        return self._latest

    async def run(self, request: RagEvaluationRequest) -> RagEvaluationResponse:
        run_id = str(uuid.uuid4())
        started_at = self._now()
        threshold = request.threshold if request.threshold is not None else settings.ragas_threshold
        samples = request.samples or self._default_samples(request.companyId)

        sample_results: List[RagEvaluationSampleResult] = []
        ragas_rows = []

        for sample in samples:
            search_request = RagSearchRequest(
                query=sample.question,
                companyId=sample.companyId or request.companyId,
                sourceTypes=sample.sourceTypes,
                collection=request.collection,
                topK=request.topK,
            )
            try:
                search_response = await rag_pipeline.search(search_request)
                sources = search_response.sources
                contexts = [source.content for source in sources if source.content]
                source_ids = [
                    source.sourceId or source.chunkId
                    for source in sources
                    if source.sourceId or source.chunkId
                ]
                answer = sample.answer or self._build_answer(contexts)
                metrics = self._heuristic_metrics(sample, answer, contexts)
                passed, reason = self._sample_status(metrics, threshold, contexts, sample, source_ids)
                result = RagEvaluationSampleResult(
                    question=sample.question,
                    answer=answer,
                    groundTruth=sample.groundTruth,
                    sourceIds=source_ids,
                    traceId=search_response.traceId,
                    metrics=metrics,
                    passed=passed,
                    reason=reason,
                )
                ragas_rows.append({
                    "question": sample.question,
                    "answer": answer,
                    "contexts": contexts,
                    "ground_truth": sample.groundTruth or sample.question,
                })
            except Exception as exc:
                result = RagEvaluationSampleResult(
                    question=sample.question,
                    groundTruth=sample.groundTruth,
                    metrics={key: 0.0 for key in METRIC_KEYS},
                    passed=False,
                    reason=f"检索失败: {exc}",
                )
            sample_results.append(result)

        evaluator = "heuristic"
        notes = "Ragas 依赖或模型配置不可用，已使用本地启发式评测。"
        ragas_metrics, ragas_sample_metrics = self._try_ragas(ragas_rows)
        if ragas_metrics:
            evaluator = "ragas"
            notes = "已使用 Ragas 评测。"
            for idx, metrics in ragas_sample_metrics.items():
                if idx < len(sample_results):
                    sample_results[idx].metrics = metrics
                    ragas_contexts = ragas_rows[idx]["contexts"] if idx < len(ragas_rows) else []
                    passed, reason = self._sample_status(
                        metrics,
                        threshold,
                        ragas_contexts if isinstance(ragas_contexts, list) else [],
                        samples[idx],
                        sample_results[idx].sourceIds,
                    )
                    sample_results[idx].passed = passed
                    sample_results[idx].reason = reason

        aggregate_metrics = ragas_metrics or self._aggregate(sample_results)
        failed_samples = [sample for sample in sample_results if not sample.passed]
        status = "passed" if sample_results and not failed_samples and self._passes(aggregate_metrics, threshold) else "failed"

        response = RagEvaluationResponse(
            runId=run_id,
            status=status,
            evaluator=evaluator,
            threshold=round(float(threshold), 4),
            sampleCount=len(sample_results),
            metrics=aggregate_metrics,
            failedSamples=failed_samples,
            sampleResults=sample_results,
            startedAt=started_at,
            completedAt=self._now(),
            notes=notes,
        )
        self._latest = response
        return response

    def empty_result(self) -> RagEvaluationResponse:
        now = self._now()
        return RagEvaluationResponse(
            runId="",
            status="empty",
            evaluator="none",
            threshold=round(float(settings.ragas_threshold), 4),
            sampleCount=0,
            startedAt=now,
            completedAt=now,
            notes="暂无评测记录。",
        )

    def _default_samples(self, company_id: Optional[str]) -> List[RagEvaluationSample]:
        file_samples = self._load_sample_file(company_id)
        if file_samples:
            return file_samples
        return [
            RagEvaluationSample(
                companyId=company_id,
                question="候选人的核心技能与岗位要求是否匹配？",
                groundTruth="回答需要引用简历、岗位或知识库上下文，说明技能匹配依据。",
                sourceTypes=["resume", "job", "knowledge"],
            ),
            RagEvaluationSample(
                companyId=company_id,
                question="面试中应该优先追问哪些能力风险？",
                groundTruth="回答需要基于上下文指出能力短板、经验缺口或验证问题。",
                sourceTypes=["resume", "job", "knowledge"],
            ),
            RagEvaluationSample(
                companyId=company_id,
                question="企业知识库中有哪些招聘或面试规范需要遵守？",
                groundTruth="回答需要引用企业知识库中的政策、手册或历史记录。",
                sourceTypes=["knowledge"],
            ),
        ]

    def _load_sample_file(self, company_id: Optional[str]) -> List[RagEvaluationSample]:
        sample_path = Path(__file__).with_name("evaluation_samples.json")
        if not sample_path.exists():
            return []
        try:
            rows = json.loads(sample_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[rag_evaluation] load sample file failed: {exc}")
            return []

        samples = []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict) or not row.get("question"):
                continue
            current = dict(row)
            current["companyId"] = str(company_id) if company_id else current.get("companyId")
            samples.append(RagEvaluationSample(**current))
        return samples

    def _build_answer(self, contexts: List[str]) -> str:
        if not contexts:
            return ""
        snippets = []
        for context in contexts[:3]:
            compact = re.sub(r"\s+", " ", context).strip()
            if compact:
                snippets.append(compact[:260])
        return " ".join(snippets)

    def _heuristic_metrics(
        self,
        sample: RagEvaluationSample,
        answer: str,
        contexts: List[str],
    ) -> Dict[str, float]:
        if not contexts:
            return {key: 0.0 for key in METRIC_KEYS}

        question_tokens = self._tokens(sample.question)
        truth_tokens = self._tokens(sample.groundTruth)
        focus_tokens = question_tokens | truth_tokens
        answer_tokens = self._tokens(answer)
        context_token_sets = [self._tokens(context) for context in contexts]
        context_tokens = set().union(*context_token_sets) if context_token_sets else set()

        context_precision = 0.0
        if context_token_sets and focus_tokens:
            context_precision = sum(self._overlap(focus_tokens, tokens) for tokens in context_token_sets) / len(context_token_sets)

        metrics = {
            "faithfulness": self._overlap(answer_tokens, context_tokens),
            "answerRelevancy": self._overlap(focus_tokens, answer_tokens | context_tokens),
            "contextPrecision": context_precision,
            "contextRecall": self._overlap(truth_tokens or question_tokens, context_tokens),
        }
        return {key: round(float(value), 4) for key, value in metrics.items()}

    def _try_ragas(self, rows: List[Dict[str, object]]) -> Tuple[Dict[str, float], Dict[int, Dict[str, float]]]:
        mode = settings.ragas_mode.lower()
        if not rows or mode in {"off", "false", "none", "heuristic"}:
            return {}, {}
        if mode == "auto" and not (settings.openai_api_key or os.getenv("OPENAI_API_KEY")):
            return {}, {}

        try:
            from datasets import Dataset
            from ragas import evaluate
            from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

            dataset = Dataset.from_dict({
                "question": [row["question"] for row in rows],
                "answer": [row["answer"] for row in rows],
                "contexts": [row["contexts"] for row in rows],
                "ground_truth": [row["ground_truth"] for row in rows],
            })
            score = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            )
            frame = score.to_pandas()
        except Exception:
            return {}, {}

        aliases = {
            "faithfulness": "faithfulness",
            "answer_relevancy": "answerRelevancy",
            "answer_relevance": "answerRelevancy",
            "context_precision": "contextPrecision",
            "context_recall": "contextRecall",
        }
        sample_metrics: Dict[int, Dict[str, float]] = {}
        aggregate_lists: Dict[str, List[float]] = {key: [] for key in METRIC_KEYS}

        for idx, row in frame.iterrows():
            current: Dict[str, float] = {}
            for column, target in aliases.items():
                if column not in row:
                    continue
                value = self._metric_value(row[column])
                current[target] = value
                aggregate_lists[target].append(value)
            if current:
                sample_metrics[int(idx)] = {key: current.get(key, 0.0) for key in METRIC_KEYS}

        aggregate = {}
        for key in METRIC_KEYS:
            values = aggregate_lists.get(key) or []
            aggregate[key] = round(sum(values) / len(values), 4) if values else 0.0
        return aggregate, sample_metrics

    def _sample_status(
        self,
        metrics: Dict[str, float],
        threshold: float,
        contexts: List[object],
        sample: RagEvaluationSample,
        source_ids: List[str],
    ) -> Tuple[bool, str]:
        if not contexts:
            return False, "未召回上下文"
        if sample.expectedSourceIds:
            missing = sorted(set(sample.expectedSourceIds) - set(source_ids))
            if missing:
                return False, "缺少期望来源: " + ", ".join(missing)
        weak_metrics = [key for key, value in metrics.items() if value < threshold]
        if weak_metrics:
            return False, "低于阈值: " + ", ".join(weak_metrics)
        return True, ""

    def _aggregate(self, sample_results: List[RagEvaluationSampleResult]) -> Dict[str, float]:
        if not sample_results:
            return {key: 0.0 for key in METRIC_KEYS}
        aggregate = {}
        for key in METRIC_KEYS:
            values = [result.metrics.get(key, 0.0) for result in sample_results]
            aggregate[key] = round(sum(values) / len(values), 4)
        return aggregate

    def _passes(self, metrics: Dict[str, float], threshold: float) -> bool:
        return all(metrics.get(key, 0.0) >= threshold for key in METRIC_KEYS)

    def _tokens(self, text: str) -> set[str]:
        if not text:
            return set()
        return set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text.lower()))

    def _overlap(self, reference: set[str], candidate: set[str]) -> float:
        if not reference:
            return 1.0 if candidate else 0.0
        if not candidate:
            return 0.0
        return len(reference & candidate) / len(reference)

    def _metric_value(self, value: object) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(number):
            return 0.0
        return round(max(0.0, min(1.0, number)), 4)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


rag_evaluation_service = RagEvaluationService()

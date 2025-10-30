from __future__ import annotations

from typing import Dict, List

from ..models import AITrainingExample, AITrainingExampleStatus


def build_training_dataset(limit: int = 200) -> Dict[str, List[Dict]]:
    """
    Collect approved training examples for downstream fine-tuning jobs.
    Returns a dict with the record list and count for convenience.
    """
    examples = (
        AITrainingExample.objects.filter(status=AITrainingExampleStatus.APPROVED)
        .select_related("company")
        .order_by("-updated_at")[:limit]
    )

    records: List[Dict] = []
    for example in examples:
        records.append(
            {
                "id": example.id,
                "prompt": example.prompt,
                "completion": example.completion,
                "metadata": example.metadata,
                "company_id": getattr(example.company, "id", None),
                "company_code": getattr(example.company, "code", None),
                "updated_at": example.updated_at.isoformat() if example.updated_at else None,
            }
        )

    return {
        "records": records,
        "count": len(records),
    }

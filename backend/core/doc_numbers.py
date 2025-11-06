from __future__ import annotations

from django.db import transaction
from django.utils import timezone


def _fy_value(fmt: str = "YYYY") -> str:
    now = timezone.now()
    if fmt.upper() == "YY":
        return f"{now:%y}"
    return f"{now:%Y}"


@transaction.atomic
def get_next_doc_no(*, company, doc_type: str, prefix: str | None = None, fy_format: str = "YYYY", width: int = 5) -> str:
    """
    Get the next sequential document number for a company and doc type.

    The format is: {prefix or doc_type}-{FY}-{SEQUENCE}
    Example: PO-2025-00001
    """
    # Lazy import to avoid app loading cycles
    from apps.metadata.models import DocumentSequence  # type: ignore

    fy = _fy_value(fy_format)
    seq, _ = (
        DocumentSequence.objects.select_for_update().get_or_create(
            company=company,
            doc_type=doc_type,
            fiscal_year=fy,
            defaults={"current_value": 0},
        )
    )
    seq.current_value += 1
    seq.save(update_fields=["current_value"])
    value = seq.current_value
    pre = prefix or doc_type
    return f"{pre}-{fy}-{value:0{width}d}"


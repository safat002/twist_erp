from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.db.models import Max

from ..models import Account


@dataclass(frozen=True)
class AccountCode:
    value: int

    def __str__(self) -> str:
        return f"{self.value:04d}"


class AccountCodeService:
    """
    Responsible for generating sequential account codes that respect the
    hierarchical rounding rules:

    * Parent accounts are 4-digit rounded numbers (1000, 2000, ...).
    * Child accounts inherit the thousand-range of the parent and increment
      by 10 (1100, 1110, etc.).
    """

    PARENT_INCREMENT = 1000
    CHILD_INCREMENT = 10

    @staticmethod
    def _next_parent_code(company_id: int) -> AccountCode:
        max_code = (
            Account.objects
            .filter(company_id=company_id, parent_account__isnull=True)
            .aggregate(max_code=Max('code'))
            .get('max_code')
        )

        if not max_code:
            return AccountCode(AccountCodeService.PARENT_INCREMENT)

        numeric = int(max_code)
        next_value = ((numeric // AccountCodeService.PARENT_INCREMENT) + 1) * AccountCodeService.PARENT_INCREMENT
        return AccountCode(next_value)

    @staticmethod
    def _next_child_code(parent: Account) -> AccountCode:
        base = (int(parent.code) // AccountCodeService.PARENT_INCREMENT) * AccountCodeService.PARENT_INCREMENT
        max_child = (
            parent.sub_accounts
            .filter(company_id=parent.company_id)
            .aggregate(max_code=Max('code'))
            .get('max_code')
        )
        if not max_child:
            return AccountCode(base + AccountCodeService.CHILD_INCREMENT)
        next_value = int(max_child) + AccountCodeService.CHILD_INCREMENT
        if (next_value // AccountCodeService.PARENT_INCREMENT) != (base // AccountCodeService.PARENT_INCREMENT):
            raise ValueError("Child account code overflow for parent; consider reorganising structure.")
        return AccountCode(next_value)

    @staticmethod
    @transaction.atomic
    def generate_code(company_id: int, parent: Optional[Account] = None) -> str:
        if parent:
            return str(AccountCodeService._next_child_code(parent))
        return str(AccountCodeService._next_parent_code(company_id))

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budgeting', '0019_budget_item_categories'),
    ]

    operations = [
        # If the earlier migration added company-level unique, drop it safely
        migrations.RemoveConstraint(
            model_name='budgetitemcategory',
            name='uniq_budget_cat_company_code',
        ),
        # Normalize codes (trim) and disambiguate duplicates within group before adding new unique constraint
        migrations.RunSQL(
            sql=r"""
                UPDATE budgeting_budgetitemcategory SET code = TRIM(code) WHERE code IS NOT NULL AND code <> TRIM(code);
                WITH ranked AS (
                    SELECT id,
                           company_group_id,
                           TRIM(code) AS code_trim,
                           ROW_NUMBER() OVER (
                               PARTITION BY company_group_id, TRIM(code)
                               ORDER BY id
                           ) AS rn
                    FROM budgeting_budgetitemcategory
                    WHERE company_group_id IS NOT NULL AND code IS NOT NULL
                )
                UPDATE budgeting_budgetitemcategory c
                SET code =
                    SUBSTRING(c.code FROM 1 FOR GREATEST(1, 50 - (LENGTH('-D') + LENGTH(r.rn::text))))
                    || '-D' || r.rn
                FROM ranked r
                WHERE c.id = r.id AND r.rn > 1;
            """,
            reverse_sql=r"""
                SELECT 1;
            """,
        ),
        migrations.AddConstraint(
            model_name='budgetitemcategory',
            constraint=models.UniqueConstraint(fields=('company_group', 'code'), name='uniq_budget_cat_group_code'),
        ),
    ]


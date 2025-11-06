from django.db import migrations, models


def backfill_uom_group(apps, schema_editor):
    UnitOfMeasure = apps.get_model('inventory', 'UnitOfMeasure')
    for u in UnitOfMeasure.objects.all().only('id', 'company_id'):
        company = None
        try:
            Company = apps.get_model('companies', 'Company')
            company = Company.objects.filter(id=u.company_id).select_related('company_group').first()
        except Exception:
            company = None
        if company and getattr(company, 'company_group_id', None):
            UnitOfMeasure.objects.filter(id=u.id).update(company_group_id=company.company_group_id)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('inventory', '10004_fix_deliveryorderline_to_sales_product'),
        ('companies', '__latest__'),
    ]

    operations = [
        migrations.AddField(
            model_name='unitofmeasure',
            name='company_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, to='companies.companygroup'),
        ),
        migrations.RunPython(backfill_uom_group, migrations.RunPython.noop),
        # Normalize codes (trim) and disambiguate duplicates by suffixing "-D{n}"
        migrations.RunSQL(
            sql=r"""
                -- 1) Normalize by trimming whitespace so 'TON ' and 'TON' collapse
                UPDATE inventory_unitofmeasure
                SET code = TRIM(code)
                WHERE code IS NOT NULL AND code <> TRIM(code);

                -- 2) For duplicates within (company_group, TRIM(code)), suffix duplicates deterministically
                WITH ranked AS (
                    SELECT id,
                           company_group_id,
                           TRIM(code) AS code_trim,
                           ROW_NUMBER() OVER (
                               PARTITION BY company_group_id, TRIM(code)
                               ORDER BY id
                           ) AS rn
                    FROM inventory_unitofmeasure
                    WHERE company_group_id IS NOT NULL AND code IS NOT NULL
                )
                UPDATE inventory_unitofmeasure u
                SET code =
                    SUBSTRING(u.code FROM 1 FOR GREATEST(1, 10 - (LENGTH('-D') + LENGTH(r.rn::text))))
                    || '-D' || r.rn
                FROM ranked r
                WHERE u.id = r.id AND r.rn > 1;
            """,
            reverse_sql=r"""
                -- No-op on reverse; duplicates cannot be reconstructed
                SELECT 1;
            """,
        ),
        migrations.AlterField(
            model_name='unitofmeasure',
            name='company_group',
            field=models.ForeignKey(on_delete=models.deletion.PROTECT, to='companies.companygroup'),
        ),
        migrations.AddConstraint(
            model_name='unitofmeasure',
            constraint=models.UniqueConstraint(fields=('company_group', 'code'), name='uom_unique_per_group_code'),
        ),
    ]

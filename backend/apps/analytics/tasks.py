from celery import shared_task

from .services.etl import run_warehouse_etl


@shared_task(name='apps.analytics.tasks.populate_data_warehouse')
def populate_data_warehouse(period: str = '30d'):
    """
    Nightly ETL job that refreshes the analytics warehouse.
    """
    return run_warehouse_etl(period=period)

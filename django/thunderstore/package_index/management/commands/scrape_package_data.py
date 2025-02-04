# Django Management Command to scrape package data from ThunderStore API

from django.core.management.base import BaseCommand

from ...data_scraper import scrape_data_and_store_to_database


class Command(BaseCommand):
    help = "Scrape package data from ThunderStore API"

    def handle(self, *args, **options):
        scrape_data_and_store_to_database()

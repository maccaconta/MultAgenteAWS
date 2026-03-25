from django.core.management.base import BaseCommand

from apps.catalog.seed_data import seed_default_catalog


class Command(BaseCommand):
    help = "Popula o catalogo com dados iniciais (persona, cenario, especialidade, etc.)"

    def handle(self, *args, **options):
        result = seed_default_catalog()
        self.stdout.write(self.style.SUCCESS(f"Seed executado com sucesso: {result}"))
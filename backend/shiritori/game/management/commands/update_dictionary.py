from django.core.management import BaseCommand

from shiritori.game.models import Word


class Command(BaseCommand):
    help = "Updates the word dictionary"

    def add_arguments(self, parser):
        # Add a locale argument that can support multiple locales
        parser.add_argument("locale", nargs="+", type=str, default=["en"])

    def handle(self, *args, **options):
        for locale in options["locale"]:
            self.stdout.write(f"Updating {locale} dictionary")
            Word.load_dictionary(locale)
            self.stdout.write(self.style.SUCCESS(f"Successfully updated {locale} dictionary"))

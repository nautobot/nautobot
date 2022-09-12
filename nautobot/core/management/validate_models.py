from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError


class Command(BaseCommand):
    help = "Validate the current models by running a `full_clean`. This goes through every model and every instance, this may take a long time to run."

    def add_arguments(self, parser):
        parser.add_argument(
            "args",
            metavar="app_label.ModelName",
            nargs="*",
            help="One or more specific models (each prefixed with its app_label) to validate.",
        )

    def _get_models(self, names):
        """
        Compile a list of models, if no names are specified, all models to be included.
        """
        models = []

        if names:
            for name in names:
                try:
                    app_label, model_name = name.split(".")
                except ValueError:
                    raise CommandError(
                        f"Invalid format: {name}. Models must be specified in the form app_label.ModelName."
                    )
                try:
                    app_config = apps.get_app_config(app_label)
                except LookupError as e:
                    raise CommandError(str(e))
                try:
                    model = app_config.get_model(model_name)
                except LookupError:
                    raise CommandError(f"Unknown model: {app_label}.{model_name}")
                models.append(model)

        else:
            for app_config in apps.get_app_configs():
                for model in app_config.models.values():
                    models.append(model)

        return models

    def handle(self, *args, **options):

        models = self._get_models(args)

        if options["verbosity"]:
            self.stdout.write(f"Validating {len(models)} models.")

        for model in models:
            model_name = f"{model._meta.app_label}.{model.__name__}"
            # Most swap out for user_model
            if model_name == "auth.User":
                model = get_user_model()
            # Skip models that aren't actually in the database
            if not model._meta.managed:
                continue

            self.stdout.write(model_name)
            for instance in model.objects.all().iterator():
                try:
                    instance.full_clean()
                except ValidationError as err:
                    self.stdout.write(f"~~~~~ Model: `{model_name}` Instance: `{instance}` Error: `{err}`. ~~~~~")

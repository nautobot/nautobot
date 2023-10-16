import logging
import os

from django.contrib.contenttypes.models import ContentType

from nautobot.extras.choices import LogLevelChoices


logger = logging.getLogger(__name__)


def files_from_contenttype_directories(base_path, job_result, log_grouping):
    """
    Iterate over a directory structure base_path/<app_label>/<model>/ and yield the ContentType and files encountered.

    Returns:
        (Tuple[ContentType, file_path]): A tuple of the ContentType and the file path.
    """
    for app_label in os.listdir(base_path):
        app_label_path = os.path.join(base_path, app_label)
        if not os.path.isdir(app_label_path):
            continue

        for modelname in os.listdir(app_label_path):
            modelname_path = os.path.join(app_label_path, modelname)
            if not os.path.isdir(modelname_path):
                continue

            try:
                model_content_type = ContentType.objects.get(app_label=app_label, model=modelname)
            except ContentType.DoesNotExist:
                msg = f"Skipping `{app_label}.{modelname}` as it isn't a known content type"
                logger.warning(msg)
                job_result.log(msg, level_choice=LogLevelChoices.LOG_WARNING, grouping=log_grouping)
                continue

            for filename in os.listdir(modelname_path):
                yield (model_content_type, os.path.join(modelname_path, filename))

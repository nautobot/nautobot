from collections import OrderedDict

from django import template
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from nautobot.core.utils.data import render_jinja2
from nautobot.extras.models import Job, JobButton, JobQueue

register = template.Library()

GROUP_DROPDOWN = """
<div class="btn-group">
  <button type="button" class="btn btn-sm btn-{group_button_class} dropdown-toggle" data-toggle="dropdown">
    {group_name} <span class="caret"></span>
  </button>
  <ul class="dropdown-menu pull-right">
    {grouped_buttons}
  </ul>
</div>
"""

HIDDEN_INPUTS = """
<input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
<input type="hidden" name="object_pk" value="{object_pk}">
<input type="hidden" name="object_model_name" value="{object_model_name}">
<input type="hidden" name="_schedule_type" value="immediately">
<input type="hidden" name="_job_queue" value="{job_queue}">
<input type="hidden" name="_return_url" value="{redirect_path}">
"""

NO_CONFIRM_BUTTON = """
<button type="submit" form="form_id_{button_id}" class="btn btn-sm btn-{button_class}" {disabled}>{button_text}</button>
"""

NO_CONFIRM_FORM = """
<form id="form_id_{button_id}" action="{button_url}" method="post" class="form">
  {hidden_inputs}
</form>
"""

CONFIRM_BUTTON = """
<button type="button" class="btn btn-sm btn-{button_class}" data-toggle="modal" data-target="#confirm_modal_id_{button_id}" {disabled}>
  {button_text}
</button>
"""

CONFIRM_MODAL = """
<div class="modal fade" id="confirm_modal_id_{button_id}" tabindex="-1" role="dialog" aria-labelledby="confirm_modal_label_{button_id}">
  <div class="modal-dialog" role="document">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h4 class="modal-title" id="confirm_modal_label_{button_id}">Confirmation</h4>
      </div>
      <form id="form_id_{button_id}" action="{button_url}" method="post" class="form">
        <div class="modal-body">
          {hidden_inputs}
          Run Job <strong>'{job}'</strong> with object <strong>'{object}'</strong>?
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Confirm</button>
        </div>
      </form>
    </div>
  </div>
</div>
"""

SAFE_EMPTY_STR = mark_safe("")


def _render_job_button_for_obj(job_button, obj, context, content_type):
    """
    Helper method for job_buttons templatetag to reduce repetition of code.

    Returns:
       (str, str): (button_html, form_html)
    """
    # Pass select context data when rendering the JobButton text as Jinja2
    button_context = {
        "obj": obj,
        "debug": context.get("debug", False),  # django.template.context_processors.debug
        "request": context["request"],  # django.template.context_processors.request
        "user": context["user"],  # django.contrib.auth.context_processors.auth
        "perms": context["perms"],  # django.contrib.auth.context_processors.auth
    }
    try:
        text_rendered = render_jinja2(job_button.text, button_context)
    except Exception as exc:
        return (
            format_html(
                '<a class="btn btn-sm btn-{}" disabled="disabled" title="{}"><i class="mdi mdi-alert"></i> {}</a>\n',
                "default" if not job_button.group_name else "link",
                exc,
                job_button.name,
            ),
            SAFE_EMPTY_STR,
        )

    if not text_rendered:
        return (SAFE_EMPTY_STR, SAFE_EMPTY_STR)

    # Disable buttons if the user doesn't have permission to run the underlying Job.
    has_run_perm = Job.objects.check_perms(context["user"], instance=job_button.job, action="run")
    try:
        job_queues = job_button.job.job_queues.all()
        _job_queue = job_queues[0]
    except IndexError:
        _job_queue = JobQueue.objects.get(name=settings.CELERY_TASK_DEFAULT_QUEUE)
    hidden_inputs = format_html(
        HIDDEN_INPUTS,
        csrf_token=context["csrf_token"],
        object_pk=obj.pk,
        object_model_name=f"{content_type.app_label}.{content_type.model}",
        redirect_path=context["request"].path,
        job_queue=_job_queue.pk,
    )
    template_args = {
        "button_id": job_button.pk,
        "button_text": text_rendered,
        "button_class": job_button.button_class if not job_button.group_name else "link",
        "button_url": reverse("extras:job_run", kwargs={"pk": job_button.job.pk}),
        "object": obj,
        "job": job_button.job,
        "hidden_inputs": hidden_inputs,
        "disabled": "" if (has_run_perm and job_button.job.installed and job_button.job.enabled) else "disabled",
    }

    if job_button.confirmation:
        return (
            format_html(CONFIRM_BUTTON, **template_args),
            format_html(CONFIRM_MODAL, **template_args),
        )
    else:
        return (
            format_html(NO_CONFIRM_BUTTON, **template_args),
            format_html(NO_CONFIRM_FORM, **template_args),
        )


@register.simple_tag(takes_context=True)
def job_buttons(context, obj):
    """
    Render all applicable job buttons for the given object.
    """
    content_type = ContentType.objects.get_for_model(obj)
    # We will enforce "run" permission later in deciding which buttons to show as disabled.
    buttons = JobButton.objects.filter(content_types=content_type, enabled=True)
    if not buttons:
        return SAFE_EMPTY_STR

    buttons_html = forms_html = SAFE_EMPTY_STR
    group_names = OrderedDict()

    for jb in buttons:
        # Organize job buttons by group for later processing
        if jb.group_name:
            group_names.setdefault(jb.group_name, []).append(jb)

        # Render and add non-grouped buttons
        else:
            button_html, form_html = _render_job_button_for_obj(jb, obj, context, content_type)
            buttons_html += button_html
            forms_html += form_html

    # Add grouped buttons to template
    for group_name, buttons in group_names.items():
        group_button_class = buttons[0].button_class

        buttons_rendered = SAFE_EMPTY_STR

        for jb in buttons:
            # Render grouped buttons as list items
            button_html, form_html = _render_job_button_for_obj(jb, obj, context, content_type)
            buttons_rendered += format_html("<li>{}</li>", button_html)
            forms_html += form_html

        if buttons_rendered:
            buttons_html += format_html(
                GROUP_DROPDOWN,
                group_button_class=group_button_class,
                group_name=group_name,
                grouped_buttons=buttons_rendered,
            )

    # We want all of the buttons first and then any modals and forms so the buttons render properly
    return buttons_html + forms_html

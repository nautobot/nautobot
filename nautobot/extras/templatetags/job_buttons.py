from collections import OrderedDict

from django import template
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from nautobot.extras.models import JobButton
from nautobot.core.utils.data import render_jinja2


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
<input type="hidden" name="redirect_path" value="{redirect_path}">
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


@register.simple_tag(takes_context=True)
def job_buttons(context, obj):
    """
    Render all applicable job buttons for the given object.
    """
    content_type = ContentType.objects.get_for_model(obj)
    buttons = JobButton.objects.filter(content_types=content_type)
    if not buttons:
        return ""

    # Pass select context data when rendering the JobButton
    button_context = {
        "obj": obj,
        "debug": context.get("debug", False),  # django.template.context_processors.debug
        "request": context["request"],  # django.template.context_processors.request
        "user": context["user"],  # django.contrib.auth.context_processors.auth
        "perms": context["perms"],  # django.contrib.auth.context_processors.auth
    }
    buttons_html = forms_html = mark_safe("")  # noqa: S308
    group_names = OrderedDict()

    hidden_inputs = format_html(
        HIDDEN_INPUTS,
        csrf_token=context["csrf_token"],
        object_pk=obj.pk,
        object_model_name=f"{content_type.app_label}.{content_type.model}",
        redirect_path=context["request"].path,
    )

    for jb in buttons:
        template_args = {
            "button_id": jb.pk,
            "button_text": jb.text,
            "button_class": jb.button_class,
            "button_url": reverse("extras:jobbutton_run", kwargs={"pk": jb.pk}),
            "object": obj,
            "job": jb.job,
            "hidden_inputs": hidden_inputs,
            "disabled": "" if context["user"].has_perms(("extras.run_jobbutton", "extras.run_job")) else "disabled",
        }

        # Organize job buttons by group
        if jb.group_name:
            group_names.setdefault(jb.group_name, [])
            group_names[jb.group_name].append(jb)

        # Add non-grouped buttons
        else:
            try:
                text_rendered = render_jinja2(jb.text, button_context)
                if text_rendered:
                    template_args["button_text"] = text_rendered
                    if jb.confirmation:
                        buttons_html += format_html(CONFIRM_BUTTON, **template_args)
                        forms_html += format_html(CONFIRM_MODAL, **template_args)
                    else:
                        buttons_html += format_html(NO_CONFIRM_BUTTON, **template_args)
                        forms_html += format_html(NO_CONFIRM_FORM, **template_args)
            except Exception as e:
                buttons_html += format_html(
                    '<a class="btn btn-sm btn-default" disabled="disabled" title="{}">'
                    '<i class="mdi mdi-alert"></i> {}</a>\n',
                    e,
                    jb.name,
                )

    # Add grouped buttons to template
    for group_name, buttons in group_names.items():
        group_button_class = buttons[0].button_class

        buttons_rendered = mark_safe("")  # noqa: S308

        for jb in buttons:
            template_args = {
                "button_id": jb.pk,
                "button_text": jb.text,
                "button_class": "link",
                "button_url": reverse("extras:jobbutton_run", kwargs={"pk": jb.pk}),
                "object": obj,
                "job": jb.job,
                "hidden_inputs": hidden_inputs,
                "disabled": "" if context["user"].has_perms(("extras.run_jobbutton", "extras.run_job")) else "disabled",
            }
            try:
                text_rendered = render_jinja2(jb.text, button_context)
                if text_rendered:
                    template_args["button_text"] = text_rendered
                    if jb.confirmation:
                        buttons_rendered += (
                            mark_safe("<li>")  # noqa: S308
                            + format_html(CONFIRM_BUTTON, **template_args)
                            + mark_safe("</li>")  # noqa: S308
                        )
                        forms_html += format_html(CONFIRM_MODAL, **template_args)
                    else:
                        buttons_rendered += (
                            mark_safe("<li>")  # noqa: S308
                            + format_html(NO_CONFIRM_BUTTON, **template_args)
                            + mark_safe("</li>")  # noqa: S308
                        )
                        forms_html += format_html(NO_CONFIRM_FORM, **template_args)
            except Exception as e:
                buttons_rendered += format_html(
                    '<li><a disabled="disabled" title="{}"><span class="text-muted">'
                    '<i class="mdi mdi-alert"></i> {}</span></a></li>',
                    e,
                    jb.name,
                )

        if buttons_rendered:
            buttons_html += format_html(
                GROUP_DROPDOWN,
                group_button_class=group_button_class,
                group_name=group_name,
                grouped_buttons=buttons_rendered,
            )

    # We want all of the buttons first and then any modals and forms so the buttons render properly
    return buttons_html + forms_html

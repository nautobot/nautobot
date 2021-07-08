from nautobot.core.apps import HomePageColumn, HomePageItem, HomePagePanel
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.models import GitRepository, JobResult, ObjectChange


def get_job_results(request):
    return (
        JobResult.objects.filter(status__in=JobResultStatusChoices.TERMINAL_STATE_CHOICES)
        .defer("data")
        .order_by("-completed")[:10]
    )


def get_changelog(request):
    return ObjectChange.objects.restrict(request.user, "view").prefetch_related("user", "changed_object_type")[:15]


layout = (
    HomePageColumn(
        name="third",
        weight=300,
        panels=(
            HomePagePanel(
                name="Data Sources",
                weight=100,
                items=(
                    HomePageItem(
                        name="Git Repositories",
                        link="dcim:site_list",
                        model=GitRepository,
                        description="Collections of data and/or job files",
                        permissions=["extras.view_gitrepository"],
                        weight=100,
                    ),
                ),
            ),
            HomePagePanel(
                name="Job History",
                weight=200,
                items=(
                    HomePageItem(
                        name="Job History",
                        permissions=["extras.view_jobresult"],
                        weight=100,
                        custom_data={"job_results": get_job_results},
                        custom_code="""
                            {% if job_results and perms.extras.view_jobresult %}
                                {% for result in job_results %}
                                    <div class="list-group-item">
                                        <a href="{% url 'extras:jobresult' pk=result.pk %}">{{ result.obj_type.name }} - {{ result.name }}</a>
                                        <span class="pull-right" title="{{ result.created }}">{% include 'extras/inc/job_label.html' %}</span>
                                        <br>
                                        <small>
                                            <span class="text-muted">{{ result.user }} - {{ result.completed|date:'SHORT_DATETIME_FORMAT' }}</span>
                                        </small>
                                    </div>
                                    {% if forloop.last %}
                                        <div class="list-group-item text-right">
                                            <a href="{% url 'extras:jobresult_list' %}">View All History</a>
                                        </div>
                                    {% endif %}
                                {% endfor %}
                            {% elif perms.extras.view_jobresult %}
                                <div class="panel-body text-muted">
                                    None found
                                </div>
                            {% else %}
                                <div class="panel-body text-muted">
                                    <i class="mdi mdi-lock"></i> No permission
                                </div>
                            {% endif %}
                        """,
                    ),
                ),
            ),
            HomePagePanel(
                name="Change Log",
                weight=300,
                items=(
                    HomePageItem(
                        name="Change Log",
                        permissions=["extras.view_objectchange"],
                        weight=100,
                        custom_data={"changelog": get_changelog},
                        custom_code="""
                            {% load helpers %}
                            {% if changelog and perms.extras.view_objectchange %}
                                {% for change in changelog %}
                                    {% with action=change.get_action_display|lower %}
                                        <div class="list-group-item">
                                            {% if action == 'created' %}
                                                <span class="label label-success">Created</span>
                                            {% elif action == 'updated' %}
                                                <span class="label label-warning">Modified</span>
                                            {% elif action == 'deleted' %}
                                                <span class="label label-danger">Deleted</span>
                                            {% endif %}
                                            {{ change.changed_object_type.name|bettertitle }}
                                            {% if change and change.changed_object and change.changed_object.get_absolute_url %}
                                                <a href="{{ change.changed_object.get_absolute_url }}">{{ change.changed_object }}</a>
                                            {% elif change and change.changed_object %}
                                                {{ change.changed_object|default:change.object_repr }}
                                            {% elif change %}
                                                {{ change.object_repr }}
                                            {% endif %}
                                            <br />
                                            <small>
                                                <span class="text-muted">{{ change.user|default:change.user_name }} -</span>
                                                <a href="{{ change.get_absolute_url }}" class="text-muted">{{ change.time|date:'SHORT_DATETIME_FORMAT' }}</a>
                                            </small>
                                        </div>
                                    {% endwith %}
                                    {% if forloop.last %}
                                        <div class="list-group-item text-right">
                                            <a href="{% url 'extras:objectchange_list' %}">View All Changes</a>
                                        </div>
                                    {% endif %}
                                {% endfor %}
                            {% elif perms.extras.view_objectchange %}
                                <div class="panel-body text-muted">
                                    No change history found
                                </div>
                            {% else %}
                                <div class="panel-body text-muted">
                                    <i class="mdi mdi-lock"></i> No permission
                                </div>
                            {% endif %}
                        """,
                    ),
                ),
            ),
        ),
    ),
)

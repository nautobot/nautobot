from billiard.einfo import ExceptionInfo, ExceptionWithTraceback
from celery import states, Task
from celery.exceptions import Retry
from celery.result import EagerResult
from celery.utils.functional import maybe_list
from celery.utils.nodenames import gethostname
from kombu.utils.uuid import uuid


class NautobotTask(Task):
    """Nautobot extensions to tasks for integrating with Job machinery."""

    def apply(
        self,
        args=None,
        kwargs=None,
        link=None,
        link_error=None,
        task_id=None,
        retries=None,
        throw=None,
        logfile=None,
        loglevel=None,
        headers=None,
        **options,
    ):
        """Fix celery's Task.apply() method to propagate options to the task result just like apply_async does."""
        # trace imports Task, so need to import inline.
        from celery.app.trace import build_tracer

        app = self._get_app()
        args = args or ()
        kwargs = kwargs or {}
        task_id = task_id or uuid()
        retries = retries or 0
        if throw is None:
            throw = app.conf.task_eager_propagates

        # Make sure we get the task instance, not class.
        task = app._tasks[self.name]

        request = {
            "id": task_id,
            "retries": retries,
            "is_eager": True,
            "logfile": logfile,
            "loglevel": loglevel or 0,
            "hostname": gethostname(),
            "callbacks": maybe_list(link),
            "errbacks": maybe_list(link_error),
            "headers": headers,
            "ignore_result": options.get("ignore_result", False),
            "delivery_info": {
                "is_eager": True,
                "exchange": options.get("exchange"),
                "routing_key": options.get("routing_key"),
                "priority": options.get("priority"),
            },
            "properties": options,  # <------- this is the one line fix to the overloaded method
        }
        if "stamped_headers" in options:
            request["stamped_headers"] = maybe_list(options["stamped_headers"])
            request["stamps"] = {header: maybe_list(options.get(header, [])) for header in request["stamped_headers"]}

        tb = None
        tracer = build_tracer(
            task.name,
            task,
            eager=True,
            propagate=throw,
            app=self._get_app(),
        )
        ret = tracer(task_id, args, kwargs, request)
        retval = ret.retval
        if isinstance(retval, ExceptionInfo):
            retval, tb = retval.exception, retval.traceback
            if isinstance(retval, ExceptionWithTraceback):
                retval = retval.exc
        if isinstance(retval, Retry) and retval.sig is not None:
            return retval.sig.apply(retries=retries + 1)
        state = states.SUCCESS if ret.info is None else ret.info.state
        return EagerResult(task_id, retval, state, traceback=tb)


Task = NautobotTask  # So that the class path resolves.

// nautobot/project-static/js/object_lock.js
// Object Lock: accessible blocked controls + release-then-act live counter.
(() => {
  "use strict";

  const announce = (message) => {
    const region = document.querySelector(".object-lock-remaining");
    if (region) {
      region.textContent = message;
    }
  };

  // CSRF token: prefer the submitting form's hidden input; fall back to Django's csrftoken cookie so
  // release still works on a page whose surrounding markup doesn't happen to render a form token.
  const csrfToken = (form) => {
    const input = (form || document).querySelector("input[name=csrfmiddlewaretoken]");
    if (input?.value) {
      return input.value;
    }
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  };

  const isLoginRedirect = (resp) => {
    // The login path is configurable (custom LOGIN_URL / SSO), so read the server-rendered value
    // rather than hardcoding "/login/".
    const region = document.querySelector(".object-lock-remaining");
    const loginUrl = region?.dataset.nbLoginUrl || "/login/";
    try {
      return new URL(resp.url).pathname.indexOf(loginUrl) === 0;
    } catch (e) {
      return false;
    }
  };

  const reportReleaseError = () => {
    // Surface the failure in the polite aria-live region instead of silently leaving the row in place.
    announce("Release failed. Reload the page and try again.");
  };

  const remainingRows = () => Array.from(document.querySelectorAll("tr[data-nb-lock-id]"));

  // no release form => not releasable here (other source, or own lock without delete_objectlock)
  const allRemainingHeldByOthers = () =>
    remainingRows().every((row) => !row.querySelector(".object-lock-release-form"));

  const remainingOtherSources = () => {
    const labels = remainingRows()
      .map((row) => row.getAttribute("data-nb-source-label"))
      .filter(Boolean);
    return labels.length ? Array.from(new Set(labels)).join(", ") : "another source";
  };

  const updateRemaining = () => {
    const region = document.querySelector(".object-lock-remaining");
    if (!region) {
      return;
    }
    const remaining = remainingRows().length;
    region.dataset.nbRemaining = String(remaining);
    const countEl = region.querySelector(".object-lock-remaining-count");
    if (countEl) {
      countEl.textContent = String(remaining);
    }
    if (remaining === 0) {
      // Reload so the server re-renders the now-unblocked Edit/Delete controls with their real URLs
      // (this script doesn't carry them). The brief message lets the aria-live region announce first.
      region.textContent = "0 lock(s) remaining. Reloading…";
      window.setTimeout(() => window.location.reload(), 800);
    } else if (region.dataset.nbBlockingOthers === "true" && allRemainingHeldByOthers()) {
      // Mixed-ownership terminal state: the counter cannot reach zero.
      const sources = remainingOtherSources();
      region.textContent =
        `You've released your locks. ${remaining} remain, held by ${sources}. ` +
        "Contact an administrator to release them.";
    }
  };

  // 1. Turn Edit/Delete actions on a locked object into focusable aria-disabled controls.
  //    A native `disabled` button drops out of the tab order and hides its reason from AT, so we keep
  //    the element focusable and suppress the action ourselves.
  const wireBlockedControls = () => {
    document.querySelectorAll("[data-nb-object-lock-blocked]").forEach((el) => {
      if (el.dataset.nbObjectLockWired === "true") {
        return;
      }
      el.dataset.nbObjectLockWired = "true";
      const explanationId = el.getAttribute("aria-describedby");
      const handle = (event) => {
        if (el.getAttribute("aria-disabled") !== "true") {
          return; // unblocked: let the real action proceed
        }
        event.preventDefault();
        event.stopPropagation();
        const explanation = explanationId ? document.getElementById(explanationId) : null;
        if (explanation) {
          explanation.removeAttribute("hidden");
          explanation.setAttribute("tabindex", "-1");
          explanation.focus();
        } else {
          // No explanation element on the page (render mismatch): still tell AT users why.
          announce("This object is locked; see the lock details below.");
        }
      };
      el.addEventListener("click", handle);
      el.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          handle(event);
        }
      });
    });
  };

  // 2. Inline per-claim release with a live "N remaining" counter.
  //    Each claim renders a real <form method="post"> (so release still works with JS disabled). We
  //    progressively enhance it: intercept submit and POST via fetch so the counter updates in place.
  //    The management delete view needs a ConfirmationForm, so the form already carries confirm=true and
  //    a CSRF token; the view 302-redirects on success and fetch follows it, so resp.ok means released.
  const wireReleaseForms = () => {
    document.querySelectorAll(".object-lock-release-form").forEach((form) => {
      if (form.dataset.nbObjectLockWired === "true") {
        return;
      }
      form.dataset.nbObjectLockWired = "true";
      form.addEventListener("submit", (event) => {
        // Force-release destroys another source's lock irreversibly; require explicit confirmation
        // (parity with the bulk-release confirmation page). Cancelling leaves the form unsubmitted.
        if (
          form.dataset.nbObjectLockForce === "true" &&
          !window.confirm("Force-release this lock held by another source? This cannot be undone.")
        ) {
          event.preventDefault();
          return;
        }
        event.preventDefault(); // enhance: release via fetch so the live counter updates in place
        const btn = form.querySelector("button[type=submit]");
        if (btn?.disabled) {
          return; // release already in flight (guards a double submit that would 404 + report falsely)
        }
        const originalLabel = btn ? btn.textContent : "";
        const reEnable = () => {
          if (btn) {
            btn.disabled = false;
            btn.textContent = originalLabel;
          }
        };
        if (btn) {
          btn.disabled = true;
          btn.textContent = "Releasing…";
        }
        const token = csrfToken(form);
        const params = new URLSearchParams();
        params.set("confirm", "true");
        if (token) {
          params.set("csrfmiddlewaretoken", token);
        }
        fetch(form.action, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRFToken": token,
            "X-Requested-With": "XMLHttpRequest",
          },
          body: params.toString(),
          credentials: "same-origin",
        })
          .then((resp) => {
            // Success is a 302 the fetch follows back to a Nautobot page (resp.ok). A session-timeout
            // 302 instead lands on the login page — detect THAT by the final URL, not resp.redirected,
            // which is also true on the normal success redirect and would reject every release.
            if (!resp.ok || isLoginRedirect(resp)) {
              reportReleaseError();
              reEnable();
              return;
            }
            // Remove the released claim's row.
            const row = form.closest("tr[data-nb-lock-id]");
            if (row) {
              row.parentNode.removeChild(row);
            }
            updateRemaining();
          })
          .catch(() => {
            reportReleaseError();
            reEnable();
          });
      });
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    wireBlockedControls();
    wireReleaseForms();
  });
})();

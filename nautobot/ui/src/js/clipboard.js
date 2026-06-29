import ClipboardJS from 'clipboard';
import { Tooltip } from 'bootstrap';

/**
 * Initialize a single global ClipboardJS instance covering every "copy to clipboard" button on the page.
 *
 * Any element carrying a `data-clipboard-target` (CSS selector of the element whose text to copy) or a
 * `data-clipboard-text` (literal string to copy) attribute is handled. ClipboardJS uses event delegation, so a
 * single instance also handles buttons inserted dynamically into the DOM after initialization.
 *
 * On a successful copy, the trigger button briefly shows a "Copied!" Bootstrap tooltip as visual feedback before
 * reverting to its original title.
 *
 * @returns {function(): void} Destructor function - destroys the ClipboardJS instance and removes listeners.
 */
export const initializeClipboard = () => {
  const clipboard = new ClipboardJS('[data-clipboard-target], [data-clipboard-text]');

  const flashTooltip = (trigger, message) => {
    if (!trigger) {
      return;
    }
    // Copy buttons carry no persistent tooltip; this builds a transient one purely for "copied" feedback.
    // Dispose of it once shown to avoid leaking Bootstrap Tooltip instances.
    const tooltip = Tooltip.getOrCreateInstance(trigger, {
      placement: 'top',
      title: message,
      trigger: 'manual',
    });
    tooltip.setContent({ '.tooltip-inner': message });
    tooltip.show();
    setTimeout(() => tooltip.dispose(), 1500);
  };

  const onSuccess = (event) => {
    flashTooltip(event.trigger, 'Copied!');
    event.clearSelection();
  };

  const isAppleOS = /Mac|iPhone|iPad|iPod/.test(navigator.platform || navigator.userAgent);
  const copyShortcut = isAppleOS ? '⌘C' : 'Ctrl+C';

  const onError = (event) => {
    flashTooltip(event.trigger, `Press ${copyShortcut} to copy`);
  };

  clipboard.on('success', onSuccess);
  clipboard.on('error', onError);

  return () => {
    clipboard.off('success', onSuccess);
    clipboard.off('error', onError);
    clipboard.destroy();
  };
};

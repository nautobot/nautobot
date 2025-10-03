/**
 * Observe pinned state of elements of class `nb-form-sticky-footer` on the page and add drop shadow with `nb-is-pinned`
 * class if they are pinned. This is purely cosmetic and does not affect functionality.
 * @example
 * // Run form sticky footers observer algorithm exactly once, i.e. observe and immediately unobserve.
 * const unobserveFormStickyFooters = observeFormStickyFooters();
 * unobserveFormStickyFooters();
 * @returns {function(): void} Unobserve function - disconnect all resize observers created during function call.
 */
export const observeFormStickyFooters = () => {
  // Form sticky footers pinned state detection with `IntersectionObserver` based on: https://stackoverflow.com/a/57991537.
  const intersectionObserver = new IntersectionObserver(
    ([entry]) => entry.target.classList.toggle('nb-is-pinned', entry.intersectionRatio < 1),
    { threshold: [1] },
  );

  const formStickyFooters = [...document.querySelectorAll('.nb-form-sticky-footer')];
  formStickyFooters.forEach((formStickyFooter) => intersectionObserver.observe(formStickyFooter));

  return () => {
    intersectionObserver.disconnect();
  };
};

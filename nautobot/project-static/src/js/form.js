export const observeFormStickyFooters = () => {
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

document.addEventListener('DOMContentLoaded', function() {
    document.querySelector('.sidenav-toggler').addEventListener('click', (event) => {
        const toggler = event.currentTarget;

        const controls = toggler.getAttribute('aria-controls');
        const expanded = toggler.getAttribute('aria-expanded') === 'true';

        toggler.setAttribute('aria-expanded', String(!expanded));

        const sidenav = document.getElementById(controls);
        sidenav.classList.toggle('sidenav-collapsed', expanded)
    });
});

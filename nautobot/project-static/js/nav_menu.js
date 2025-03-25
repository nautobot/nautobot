document.addEventListener('DOMContentLoaded', function() {
    document.querySelector('.sidenav-toggler').addEventListener('click', (event) => {
        const toggler = event.currentTarget;

        const controls = toggler.getAttribute('aria-controls');
        const expanded = toggler.getAttribute('aria-expanded') === 'true';

        toggler.setAttribute('aria-expanded', String(!expanded));

        const sidenav = document.getElementById(controls);
        sidenav.classList.toggle('sidenav-collapsed', expanded)
    });

    [...document.querySelectorAll('.sidenav-list-item')].forEach(sidenavListItem => {
        sidenavListItem.addEventListener('click', (event) => {
            const controls = sidenavListItem.getAttribute('aria-controls');
            const expanded = sidenavListItem.getAttribute('aria-expanded') === 'true';

            sidenavListItem.setAttribute('aria-expanded', String(!expanded));

            const onClickDocument = (documentClickEvent) => {
                const { target: documentClickTarget } = documentClickEvent;
                const sidenavFlyout = document.getElementById(controls);

                const isClickOutside = !sidenavListItem.contains(documentClickTarget)
                    && !sidenavFlyout.contains(documentClickTarget);

                if (isClickOutside) {
                    sidenavListItem.setAttribute('aria-expanded', 'false');
                    document.removeEventListener('click', onClickDocument);
                }
            };

            expanded
                ? document.removeEventListener('click', onClickDocument)
                : document.addEventListener('click', onClickDocument);
        });
    });
});

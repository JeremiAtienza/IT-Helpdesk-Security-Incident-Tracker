document.addEventListener('DOMContentLoaded', function () {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.classList.add('fade-up');
        card.style.animationDelay = `${index * 60}ms`;
    });

    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    const currentPath = window.location.pathname;
    navLinks.forEach((link) => {
        if (link.pathname === currentPath) {
            link.classList.add('active');
        }
    });

    const collapsible = document.querySelector('.navbar-collapse');
    const toggler = document.querySelector('.navbar-toggler');
    if (toggler && collapsible) {
        toggler.addEventListener('click', () => {
            collapsible.classList.toggle('show');
        });
    }
});

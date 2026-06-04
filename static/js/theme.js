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

    // Signup password helpers: toggle visibility, strength meter, and match indicator
    const pwd1 = document.querySelector('input[name="password1"]');
    const pwd2 = document.querySelector('input[name="password2"]');
    const toggleBtn = document.getElementById('togglePassword');
    const strengthBar = document.getElementById('passwordStrength');
    const strengthText = document.getElementById('passwordStrengthText');
    const matchText = document.getElementById('passwordMatch');

    function scorePassword(p) {
        let score = 0;
        if (!p) return score;
        // length
        if (p.length >= 8) score += 1;
        if (p.length >= 12) score += 1;
        // variety
        if (/[A-Z]/.test(p)) score += 1;
        if (/[a-z]/.test(p)) score += 1;
        if (/[0-9]/.test(p)) score += 1;
        if (/[^A-Za-z0-9]/.test(p)) score += 1;
        return score; // range 0-6
    }

    function updateStrength() {
        if (!pwd1 || !strengthBar || !strengthText) return;
        const s = scorePassword(pwd1.value);
        const pct = Math.min(100, Math.round((s / 6) * 100));
        strengthBar.style.width = pct + '%';
        strengthBar.className = 'progress-bar';
        if (s <= 2) strengthBar.classList.add('bg-danger');
        else if (s <= 4) strengthBar.classList.add('bg-warning');
        else strengthBar.classList.add('bg-success');

        let label = 'Very weak';
        if (s <= 1) label = 'Very weak';
        else if (s === 2) label = 'Weak';
        else if (s <= 4) label = 'Good';
        else label = 'Strong';
        strengthText.textContent = label;
    }

    function updateMatch() {
        if (!pwd1 || !pwd2 || !matchText) return;
        if (!pwd2.value) {
            matchText.textContent = '';
            return;
        }
        if (pwd1.value === pwd2.value) {
            matchText.textContent = 'Passwords match';
            matchText.classList.remove('text-danger');
            matchText.classList.add('text-success');
        } else {
            matchText.textContent = 'Passwords do not match';
            matchText.classList.remove('text-success');
            matchText.classList.add('text-danger');
        }
    }

    if (toggleBtn && pwd1) {
        toggleBtn.addEventListener('click', () => {
            const t = pwd1.getAttribute('type') === 'password' ? 'text' : 'password';
            pwd1.setAttribute('type', t);
            pwd2 && pwd2.setAttribute('type', t);
            toggleBtn.textContent = t === 'text' ? 'Hide' : 'Show';
        });
    }

    if (pwd1) pwd1.addEventListener('input', () => { updateStrength(); updateMatch(); });
    if (pwd2) pwd2.addEventListener('input', updateMatch);
});

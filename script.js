/* ============================================
   夢進堂 - JavaScript
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {

    /* ---------- ヘッダースクロール制御 ---------- */
    const header = document.getElementById('header');

    const onScroll = () => {
        if (window.scrollY > 80) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    /* ---------- ハンバーガーメニュー ---------- */
    const hamburger = document.getElementById('hamburger');
    const nav = document.getElementById('nav');

    // オーバーレイ要素を動的に追加
    const overlay = document.createElement('div');
    overlay.className = 'nav-overlay';
    document.body.appendChild(overlay);

    const toggleMenu = () => {
        hamburger.classList.toggle('active');
        nav.classList.toggle('open');
        overlay.classList.toggle('open');
        document.body.style.overflow = nav.classList.contains('open') ? 'hidden' : '';
    };

    hamburger.addEventListener('click', toggleMenu);
    overlay.addEventListener('click', toggleMenu);

    // ナビリンククリックで閉じる
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            if (nav.classList.contains('open')) {
                toggleMenu();
            }
        });
    });

    /* ---------- スムーズスクロール ---------- */
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
            e.preventDefault();
            const target = document.querySelector(anchor.getAttribute('href'));
            if (target) {
                const headerHeight = header.offsetHeight;
                const top = target.getBoundingClientRect().top + window.scrollY - headerHeight;
                window.scrollTo({
                    top: top,
                    behavior: 'smooth'
                });
            }
        });
    });

    /* ---------- スクロールフェードイン ---------- */
    const fadeElements = document.querySelectorAll('.fade-in');

    const observerOptions = {
        root: null,
        rootMargin: '0px 0px -60px 0px',
        threshold: 0.15
    };

    const fadeObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                fadeObserver.unobserve(entry.target);
            }
        });
    }, observerOptions);

    fadeElements.forEach(el => fadeObserver.observe(el));

    /* ---------- お問い合わせフォーム（AJAX） ---------- */
    const contactForm = document.getElementById('contactForm');
    const formStatus = document.getElementById('formStatus');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');

    if (contactForm) {
        contactForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            // 状態のリセット
            formStatus.style.display = 'none';
            formStatus.className = 'form-status';
            submitBtn.disabled = true;
            btnText.classList.add('loading');
            btnText.textContent = '送信中...';

            const formData = new FormData(contactForm);

            try {
                const response = await fetch('contact.php', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.status === 'success') {
                    formStatus.textContent = result.message;
                    formStatus.classList.add('success');
                    contactForm.reset();
                } else {
                    formStatus.textContent = result.message;
                    formStatus.classList.add('error');
                }
            } catch (error) {
                formStatus.textContent = '通信エラーが発生しました。時間を置いて再度お試しください。';
                formStatus.classList.add('error');
                console.error('Submission error:', error);
            } finally {
                formStatus.style.display = 'block';
                submitBtn.disabled = false;
                btnText.classList.remove('loading');
                btnText.textContent = 'この内容で送信する';
            }
        });
    }
});

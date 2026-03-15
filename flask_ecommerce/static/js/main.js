/**
 * main.js - JavaScript chính cho LUXE Fashion E-commerce
 * Vanilla JS - Không cần framework
 */

document.addEventListener('DOMContentLoaded', function () {

    // ========================================================
    //  MOBILE MENU TOGGLE
    // ========================================================
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');

    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', function () {
            mobileMenu.classList.toggle('hidden');
            // Đóng search bar nếu đang mở
            const searchBar = document.getElementById('mobile-search-bar');
            if (searchBar) searchBar.classList.add('hidden');
        });
    }

    // ========================================================
    //  MOBILE SEARCH TOGGLE
    // ========================================================
    const mobileSearchBtn = document.getElementById('mobile-search-btn');
    const mobileSearchBar = document.getElementById('mobile-search-bar');

    if (mobileSearchBtn && mobileSearchBar) {
        mobileSearchBtn.addEventListener('click', function () {
            mobileSearchBar.classList.toggle('hidden');
            if (!mobileSearchBar.classList.contains('hidden')) {
                mobileSearchBar.querySelector('input').focus();
            }
            // Đóng mobile menu nếu đang mở
            if (mobileMenu) mobileMenu.classList.add('hidden');
        });
    }

    // ========================================================
    //  HEADER SCROLL SHADOW
    // ========================================================
    const header = document.getElementById('main-header');
    if (header) {
        let lastScroll = 0;
        window.addEventListener('scroll', function () {
            const currentScroll = window.pageYOffset;
            if (currentScroll > 10) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
            lastScroll = currentScroll;
        }, { passive: true });
    }

    // ========================================================
    //  AJAX ADD TO CART (Không reload trang)
    // ========================================================
    document.querySelectorAll('.add-to-cart-form').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const url = form.action;
            const formData = new FormData(form);

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success) {
                    // Cập nhật cart badge
                    updateCartBadge(data.cart_count);

                    // Hiệu ứng thông báo
                    showToast('Đã thêm vào giỏ hàng!');

                    // Animation cho button
                    const btn = form.querySelector('button');
                    btn.textContent = '✓ Đã thêm';
                    btn.classList.add('bg-emerald-500');
                    setTimeout(function () {
                        btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/></svg> Thêm vào giỏ';
                        btn.classList.remove('bg-emerald-500');
                    }, 1500);
                }
            })
            .catch(function () {
                // Fallback: submit form bình thường
                form.submit();
            });
        });
    });

    // ========================================================
    //  CẬP NHẬT CART BADGE
    // ========================================================
    function updateCartBadge(count) {
        let badge = document.getElementById('cart-badge');
        if (count > 0) {
            if (!badge) {
                // Tạo badge mới nếu chưa có
                const cartLink = document.querySelector('a[href*="/cart"]');
                if (cartLink) {
                    badge = document.createElement('span');
                    badge.id = 'cart-badge';
                    badge.className = 'absolute -top-0.5 -right-0.5 bg-pink-600 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-medium';
                    cartLink.appendChild(badge);
                }
            }
            if (badge) {
                badge.textContent = count;
                // Bounce animation
                badge.style.transform = 'scale(1.3)';
                setTimeout(function () {
                    badge.style.transform = 'scale(1)';
                }, 200);
            }
        }
    }

    // ========================================================
    //  TOAST NOTIFICATION
    // ========================================================
    function showToast(message) {
        // Tạo toast element
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-6 right-6 z-50 bg-gray-900 text-white px-5 py-3 rounded-xl shadow-2xl text-sm font-medium flex items-center gap-2 transition-all duration-300';
        toast.style.transform = 'translateY(20px)';
        toast.style.opacity = '0';
        toast.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-emerald-400"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>' + message;

        document.body.appendChild(toast);

        // Animate in
        requestAnimationFrame(function () {
            toast.style.transform = 'translateY(0)';
            toast.style.opacity = '1';
        });

        // Auto remove
        setTimeout(function () {
            toast.style.transform = 'translateY(20px)';
            toast.style.opacity = '0';
            setTimeout(function () {
                toast.remove();
            }, 300);
        }, 2500);
    }

    // ========================================================
    //  AUTO-DISMISS FLASH MESSAGES
    // ========================================================
    const flashContainer = document.getElementById('flash-messages');
    if (flashContainer) {
        setTimeout(function () {
            flashContainer.querySelectorAll('.flash-msg').forEach(function (msg, i) {
                setTimeout(function () {
                    msg.style.opacity = '0';
                    msg.style.transform = 'translateY(-10px)';
                    msg.style.transition = 'all 0.3s ease';
                    setTimeout(function () { msg.remove(); }, 300);
                }, i * 100);
            });
        }, 4000);
    }

    // ========================================================
    //  RE-INITIALIZE LUCIDE ICONS (cho nội dung động)
    // ========================================================
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
});

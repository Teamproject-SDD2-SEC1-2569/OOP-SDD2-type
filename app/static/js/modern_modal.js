/**
 * modern_modal.js
 * ระบบกล่องข้อความแจ้งเตือน (Modal / Dialog / Popup) สไตล์ Modern
 * ใช้แทน browser alert(), confirm(), prompt() เดิมของระบบ
 */
(function (window, document) {
    'use strict';

    // ตรวจสอบและแทรก CSS หากยังไม่มีการโหลด
    function ensureStyles() {
        if (document.getElementById('modern-modal-styles') || document.querySelector('link[href*="modern_modal.css"]')) {
            return;
        }
        const link = document.createElement('link');
        link.id = 'modern-modal-styles';
        link.rel = 'stylesheet';
        link.href = '/static/css/modern_modal.css';
        document.head.appendChild(link);
    }

    // สร้าง Element ของ Modal ใน DOM หากยังไม่มี
    function ensureModalDOM() {
        let backdrop = document.getElementById('modernPopupModal');
        if (backdrop) return backdrop;

        backdrop = document.createElement('div');
        backdrop.className = 'modern-modal-backdrop';
        backdrop.id = 'modernPopupModal';
        backdrop.setAttribute('role', 'dialog');
        backdrop.setAttribute('aria-modal', 'true');
        backdrop.innerHTML = `
            <div class="modern-modal-card" id="modernPopupCard">
                <div class="modern-modal-icon info" id="modernPopupIcon">✦</div>
                <h3 class="modern-modal-title" id="modernPopupTitle">แจ้งเตือน</h3>
                <p class="modern-modal-message" id="modernPopupMessage"></p>
                <div class="modern-modal-input-wrap" id="modernPopupInputWrap" style="display: none;">
                    <input type="text" class="modern-modal-input" id="modernPopupInput" />
                </div>
                <div class="modern-modal-actions" id="modernPopupActions">
                    <button type="button" class="modern-modal-cancel" id="modernPopupCancelBtn" style="display: none;">ยกเลิก</button>
                    <button type="button" class="modern-modal-btn info" id="modernPopupConfirmBtn">ตกลง</button>
                </div>
            </div>
        `;
        document.body.appendChild(backdrop);

        backdrop.addEventListener('click', function (e) {
            if (e.target === backdrop) {
                if (window._currentModalMode === 'alert') {
                    window.closeModernPopup();
                } else if (window._currentModalMode === 'confirm') {
                    window.closeModernPopup(false);
                } else if (window._currentModalMode === 'prompt') {
                    window.closeModernPopup(null);
                }
            }
        });

        document.addEventListener('keydown', function (e) {
            if (!backdrop.classList.contains('show')) return;
            if (e.key === 'Escape') {
                e.preventDefault();
                if (window._currentModalMode === 'alert') {
                    window.closeModernPopup();
                } else if (window._currentModalMode === 'confirm') {
                    window.closeModernPopup(false);
                } else if (window._currentModalMode === 'prompt') {
                    window.closeModernPopup(null);
                }
            } else if (e.key === 'Enter') {
                const input = document.getElementById('modernPopupInput');
                if (window._currentModalMode === 'prompt' && document.activeElement === input) {
                    e.preventDefault();
                    document.getElementById('modernPopupConfirmBtn').click();
                }
            }
        });

        return backdrop;
    }

    let activeResolve = null;
    let activeConfirmCallback = null;

    /**
     * ปิด Modal และคืนค่าผลลัพธ์
     */
    window.closeModernPopup = function (resultVal) {
        const backdrop = document.getElementById('modernPopupModal');
        if (backdrop) {
            backdrop.classList.remove('show');
        }

        if (typeof activeConfirmCallback === 'function') {
            const cb = activeConfirmCallback;
            activeConfirmCallback = null;
            try { cb(resultVal); } catch (e) { console.error(e); }
        }

        if (typeof activeResolve === 'function') {
            const res = activeResolve;
            activeResolve = null;
            res(resultVal);
        }
    };

    /**
     * แสดง Popup แจ้งเตือน (แทน alert)
     */
    window.showModernPopup = function ({
        type = 'info',
        title = 'แจ้งเตือน',
        message = '',
        buttonText = 'ตกลง',
        onConfirm = null
    } = {}) {
        ensureStyles();
        const backdrop = ensureModalDOM();
        const icon = document.getElementById('modernPopupIcon');
        const titleEl = document.getElementById('modernPopupTitle');
        const msgEl = document.getElementById('modernPopupMessage');
        const inputWrap = document.getElementById('modernPopupInputWrap');
        const cancelBtn = document.getElementById('modernPopupCancelBtn');
        const confirmBtn = document.getElementById('modernPopupConfirmBtn');

        window._currentModalMode = 'alert';
        activeConfirmCallback = onConfirm;

        const safeType = ['success', 'error', 'warning', 'info'].includes(type) ? type : 'info';
        icon.className = `modern-modal-icon ${safeType}`;
        confirmBtn.className = `modern-modal-btn ${safeType}`;

        if (safeType === 'success') {
            icon.innerText = '✓';
        } else if (safeType === 'error') {
            icon.innerText = '!';
        } else if (safeType === 'warning') {
            icon.innerText = '!';
        } else {
            icon.innerText = '✦';
        }

        titleEl.innerText = title;
        msgEl.innerText = message;
        confirmBtn.innerText = buttonText;

        inputWrap.style.display = 'none';
        cancelBtn.style.display = 'none';

        confirmBtn.onclick = function () {
            window.closeModernPopup(true);
        };

        backdrop.classList.add('show');
        setTimeout(() => confirmBtn.focus(), 60);

        return new Promise((resolve) => {
            activeResolve = resolve;
        });
    };

    /**
     * แสดง Popup ยืนยัน (แทน confirm)
     * คืนค่า Promise<boolean>
     */
    window.showModernConfirm = function ({
        type = 'warning',
        title = 'ยืนยันการทำรายการ',
        message = '',
        confirmText = 'ยืนยัน',
        cancelText = 'ยกเลิก',
        danger = false
    } = {}) {
        ensureStyles();
        const backdrop = ensureModalDOM();
        const icon = document.getElementById('modernPopupIcon');
        const titleEl = document.getElementById('modernPopupTitle');
        const msgEl = document.getElementById('modernPopupMessage');
        const inputWrap = document.getElementById('modernPopupInputWrap');
        const cancelBtn = document.getElementById('modernPopupCancelBtn');
        const confirmBtn = document.getElementById('modernPopupConfirmBtn');

        window._currentModalMode = 'confirm';
        activeConfirmCallback = null;

        const effectiveType = danger ? 'error' : (['success', 'error', 'warning', 'info'].includes(type) ? type : 'warning');
        icon.className = `modern-modal-icon ${effectiveType}`;
        confirmBtn.className = `modern-modal-btn ${effectiveType}`;

        if (effectiveType === 'success') {
            icon.innerText = '✓';
        } else if (effectiveType === 'error' || danger) {
            icon.innerText = '!';
        } else if (effectiveType === 'warning') {
            icon.innerText = '!';
        } else {
            icon.innerText = '?';
        }

        titleEl.innerText = title;
        msgEl.innerText = message;
        confirmBtn.innerText = confirmText;
        cancelBtn.innerText = cancelText;

        inputWrap.style.display = 'none';
        cancelBtn.style.display = 'block';

        confirmBtn.onclick = function () {
            window.closeModernPopup(true);
        };
        cancelBtn.onclick = function () {
            window.closeModernPopup(false);
        };

        backdrop.classList.add('show');
        setTimeout(() => confirmBtn.focus(), 60);

        return new Promise((resolve) => {
            activeResolve = resolve;
        });
    };

    /**
     * แสดง Prompt ให้กรอกข้อความ (แทน prompt)
     * คืนค่า Promise<string | null>
     */
    window.showModernPrompt = function ({
        type = 'info',
        title = 'กรอกข้อมูล',
        message = '',
        placeholder = '',
        defaultValue = '',
        confirmText = 'ตกลง',
        cancelText = 'ยกเลิก',
        danger = false
    } = {}) {
        ensureStyles();
        const backdrop = ensureModalDOM();
        const icon = document.getElementById('modernPopupIcon');
        const titleEl = document.getElementById('modernPopupTitle');
        const msgEl = document.getElementById('modernPopupMessage');
        const inputWrap = document.getElementById('modernPopupInputWrap');
        const input = document.getElementById('modernPopupInput');
        const cancelBtn = document.getElementById('modernPopupCancelBtn');
        const confirmBtn = document.getElementById('modernPopupConfirmBtn');

        window._currentModalMode = 'prompt';
        activeConfirmCallback = null;

        const effectiveType = danger ? 'error' : type;
        icon.className = `modern-modal-icon ${effectiveType}`;
        confirmBtn.className = `modern-modal-btn ${effectiveType}`;
        icon.innerText = danger ? '!' : '✎';

        titleEl.innerText = title;
        msgEl.innerText = message;
        input.value = defaultValue || '';
        input.placeholder = placeholder || '';
        confirmBtn.innerText = confirmText;
        cancelBtn.innerText = cancelText;

        inputWrap.style.display = 'block';
        cancelBtn.style.display = 'block';

        confirmBtn.onclick = function () {
            window.closeModernPopup(input.value);
        };
        cancelBtn.onclick = function () {
            window.closeModernPopup(null);
        };

        backdrop.classList.add('show');
        setTimeout(() => {
            input.focus();
            input.select();
        }, 60);

        return new Promise((resolve) => {
            activeResolve = resolve;
        });
    };

    /**
     * ฟังก์ชันทางลัด modernAlert
     */
    window.modernAlert = function (message, type = 'info', title = 'แจ้งเตือน') {
        return window.showModernPopup({ type, title, message });
    };

    /**
     * ดักจับและแทนที่ window.alert ปกติของ Browser อัตโนมัติ
     * เพื่อให้ alert() เดิมทุกจุดแสดงผลเป็น Modern Modal ทันที
     */
    const originalAlert = window.alert;
    window.alert = function (msg) {
        const text = String(msg || '');
        let type = 'info';
        let title = 'แจ้งเตือน';

        if (/ไม่สำเร็จ|ล้มเหลว|ผิดพลาด|ข้อผิดพลาด|ไม่พบ|error|fail|invalid/i.test(text)) {
            type = 'error';
            title = 'แจ้งเตือน';
        } else if (/สำเร็จ|เรียบร้อย|เสร็จ|success/i.test(text)) {
            type = 'success';
            title = 'สำเร็จ';
        } else if (/กรุณา|โปรด|เตือน|warning|ระวัง/i.test(text)) {
            type = 'warning';
            title = 'แจ้งเตือน';
        }

        return window.showModernPopup({
            type: type,
            title: title,
            message: text
        });
    };

    // Auto-init DOM เมื่อโหลดเสร็จ
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            ensureStyles();
            ensureModalDOM();
        });
    } else {
        ensureStyles();
        ensureModalDOM();
    }
})(window, document);


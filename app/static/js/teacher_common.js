/**
 * teacher_common.js
 * ฟังก์ชันส่วนกลางสำหรับหน้าอาจารย์: ตรวจสิทธิ์, เรียก API พร้อม JWT,
 * แสดงชื่ออาจารย์ใน Sidebar, Toast และกล่องยืนยันแบบสมัยใหม่
 */
(function (window, document) {
    'use strict';

    const TC = {};

    TC.token = localStorage.getItem('token') || localStorage.getItem('accessToken');

    TC.getUser = function () {
        try {
            return JSON.parse(localStorage.getItem('user') || '{}');
        } catch (e) {
            return {};
        }
    };

    TC.logout = function () {
        localStorage.clear();
        window.location.href = '/';
    };

    /** ป้องกันบัญชีที่ไม่ใช่อาจารย์เข้าหน้าอาจารย์ */
    TC.guardTeacher = function () {
        const user = TC.getUser();
        if (!TC.token || !user || !user.role) {
            TC.logout();
            return false;
        }
        if (String(user.role).toLowerCase() !== 'teacher') {
            window.location.href = '/';
            return false;
        }
        return true;
    };

    TC.escape = function (value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };

    TC.initials = function (name) {
        const cleaned = String(name || '').trim();
        if (!cleaned) return 'อจ';
        const parts = cleaned.split(/\s+/);
        if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
        return cleaned.slice(0, 2).toUpperCase();
    };

    /** แสดงชื่อและตัวย่อของอาจารย์ที่ล็อกอินอยู่ใน Sidebar */
    TC.renderSidebarUser = function () {
        const user = TC.getUser();
        const fullName = (user.full_name || user.username || 'อาจารย์').trim();
        const titlePrefix = user.academic_title || 'อ.';
        const displayName = fullName.startsWith(titlePrefix) ? fullName : `${titlePrefix}${fullName}`;
        const nameEl = document.querySelector('.user-profile .name');
        const avatarEl = document.querySelector('.user-profile .avatar');
        if (nameEl) nameEl.innerText = displayName;
        if (avatarEl) avatarEl.innerText = TC.initials(fullName);

        document.querySelectorAll('[data-logout]').forEach((el) => {
            el.addEventListener('click', (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                TC.logout();
            });
        });
    };

    /** เรียก API พร้อมแนบ JWT และจัดการ Token หมดอายุ */
    TC.api = async function (url, options = {}) {
        const headers = Object.assign({ 'Authorization': `Bearer ${TC.token}` }, options.headers || {});
        if (options.body && typeof options.body !== 'string') {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(options.body);
        }
        let res;
        try {
            res = await fetch(url, Object.assign({}, options, { headers }));
        } catch (err) {
            return { ok: false, status: 0, data: { error: 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้' } };
        }
        if (res.status === 401 || res.status === 422) {
            TC.logout();
            return { ok: false, status: res.status, data: {} };
        }
        let data = {};
        try { data = await res.json(); } catch (e) { data = {}; }
        return { ok: res.ok, status: res.status, data };
    };

    /* ---------------- Modern UI: Toast & Confirm ---------------- */
    function injectStyles() {
        if (document.getElementById('tc-ui-styles')) return;
        const style = document.createElement('style');
        style.id = 'tc-ui-styles';
        style.textContent = `
            .tc-toast-wrap { position: fixed; top: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px; }
            .tc-toast { min-width: 260px; max-width: 380px; background: #fff; border-radius: 14px; padding: 14px 18px; display: flex; align-items: center; gap: 12px;
                        box-shadow: 0 10px 30px rgba(6,51,118,0.15); border-left: 5px solid #288CF0; font-size: 14px; color: #17345C; font-weight: 500;
                        animation: tcSlideIn .25s ease-out; }
            .tc-toast.success { border-left-color: #20A873; } .tc-toast.success i { color: #20A873; }
            .tc-toast.error { border-left-color: #E95C68; } .tc-toast.error i { color: #E95C68; }
            .tc-toast.info i { color: #288CF0; }
            .tc-toast i { font-size: 18px; }
            .tc-toast.hide { animation: tcSlideOut .25s ease-in forwards; }
            @keyframes tcSlideIn { from { opacity: 0; transform: translateX(40px); } to { opacity: 1; transform: none; } }
            @keyframes tcSlideOut { to { opacity: 0; transform: translateX(40px); } }
            .tc-confirm-overlay { position: fixed; inset: 0; background: rgba(6,51,118,0.45); backdrop-filter: blur(3px); display: flex; justify-content: center; align-items: center; z-index: 9998; animation: tcFade .2s; }
            .tc-confirm { background: #fff; border-radius: 20px; padding: 28px; width: 92%; max-width: 420px; text-align: center; box-shadow: 0 20px 50px rgba(0,0,0,0.2); animation: tcPop .2s ease-out; }
            .tc-confirm .tc-icon { width: 60px; height: 60px; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center; font-size: 26px; background: #E7F3FE; color: #288CF0; }
            .tc-confirm.danger .tc-icon { background: #FDEBED; color: #E95C68; }
            .tc-confirm h3 { color: #063376; font-size: 19px; margin-bottom: 8px; }
            .tc-confirm p { color: #71829B; font-size: 14px; line-height: 1.6; margin-bottom: 22px; white-space: pre-line; }
            .tc-confirm .tc-actions { display: flex; gap: 10px; }
            .tc-confirm button { flex: 1; padding: 12px; border-radius: 12px; font-size: 14px; font-weight: 600; cursor: pointer; border: 1px solid #D8E7F4; background: #fff; color: #71829B; font-family: inherit; }
            .tc-confirm button.tc-ok { background: #288CF0; border-color: #288CF0; color: #fff; }
            .tc-confirm.danger button.tc-ok { background: #E95C68; border-color: #E95C68; }
            @keyframes tcFade { from { opacity: 0; } to { opacity: 1; } }
            @keyframes tcPop { from { opacity: 0; transform: scale(.92); } to { opacity: 1; transform: none; } }
        `;
        document.head.appendChild(style);
    }

    TC.toast = function (message, type = 'info', timeout = 3000) {
        injectStyles();
        let wrap = document.querySelector('.tc-toast-wrap');
        if (!wrap) {
            wrap = document.createElement('div');
            wrap.className = 'tc-toast-wrap';
            document.body.appendChild(wrap);
        }
        const icons = { success: 'fa-circle-check', error: 'fa-circle-exclamation', info: 'fa-circle-info' };
        const el = document.createElement('div');
        el.className = `tc-toast ${type}`;
        el.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i><span>${TC.escape(message)}</span>`;
        wrap.appendChild(el);
        setTimeout(() => {
            el.classList.add('hide');
            setTimeout(() => el.remove(), 260);
        }, timeout);
    };

    TC.confirm = function ({ title = 'ยืนยันการทำรายการ', message = '', confirmText = 'ยืนยัน', cancelText = 'ยกเลิก', danger = false, icon } = {}) {
        injectStyles();
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'tc-confirm-overlay';
            const iconClass = icon || (danger ? 'fa-triangle-exclamation' : 'fa-circle-question');
            overlay.innerHTML = `
                <div class="tc-confirm ${danger ? 'danger' : ''}">
                    <div class="tc-icon"><i class="fa-solid ${iconClass}"></i></div>
                    <h3>${TC.escape(title)}</h3>
                    <p>${TC.escape(message)}</p>
                    <div class="tc-actions">
                        <button type="button" class="tc-cancel">${TC.escape(cancelText)}</button>
                        <button type="button" class="tc-ok">${TC.escape(confirmText)}</button>
                    </div>
                </div>`;
            const close = (result) => { overlay.remove(); resolve(result); };
            overlay.querySelector('.tc-cancel').onclick = () => close(false);
            overlay.querySelector('.tc-ok').onclick = () => close(true);
            overlay.addEventListener('click', (e) => { if (e.target === overlay) close(false); });
            document.body.appendChild(overlay);
        });
    };

    TC.formatSeconds = function (totalSeconds) {
        const s = Math.max(0, parseInt(totalSeconds || 0, 10));
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        const sec = s % 60;
        const pad = (n) => String(n).padStart(2, '0');
        return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`;
    };

    TC.downloadCSV = function (filename, rows) {
        const csv = rows.map((row) => row.map((cell) => {
            const v = String(cell ?? '');
            return /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
        }).join(',')).join('\n');
        const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    };

    window.TC = TC;
})(window, document);


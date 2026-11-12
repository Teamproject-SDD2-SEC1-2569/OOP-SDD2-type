/**
 * auth_guard.js
 * ป้องกันการเข้าถึงหน้าเว็บผ่าน URL โดยไม่ได้เข้าสู่ระบบ
 * ทำงานทันทีใน <head> ก่อนที่หน้าเว็บจะแสดงผล เพื่อป้องกันหน้ากระพริบ
 */
(function (window, document) {
    'use strict';

    function getCookie(name) {
        try {
            const matches = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, '\\$1') + '=([^;]*)'));
            return matches ? decodeURIComponent(matches[1]) : null;
        } catch (e) {
            return null;
        }
    }

    function setCookie(name, value, days) {
        try {
            let expires = '';
            if (days) {
                const date = new Date();
                date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
                expires = '; expires=' + date.toUTCString();
            }
            document.cookie = name + '=' + (encodeURIComponent(value) || '') + expires + '; path=/; SameSite=Lax';
        } catch (e) {}
    }

    function clearCookie(name) {
        try {
            document.cookie = name + '=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax';
        } catch (e) {}
    }

    function isTokenExpired(token) {
        if (!token) return true;
        try {
            const parts = token.split('.');
            if (parts.length !== 3) return true;
            // Decode base64url payload
            const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function (c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            const payload = JSON.parse(jsonPayload);
            if (payload && payload.exp) {
                // เผื่อเวลา 10 วินาที
                return (payload.exp * 1000) < (Date.now() + 10000);
            }
            return false;
        } catch (e) {
            return true;
        }
    }

    function getAuth() {
        try {
            let token = localStorage.getItem('token') || localStorage.getItem('accessToken') || getCookie('access_token');
            const userStr = localStorage.getItem('user');
            let user = userStr ? JSON.parse(userStr) : null;

            // ถ้า Token หมดอายุ ให้ล้างค่าทิ้งทันที
            if (token && isTokenExpired(token)) {
                window.logout(false);
                return { token: null, user: null };
            }

            // Sync ลง Cookie ให้ Backend นำไปตรวจสอบในการเปิด URL รอบถัดไปได้ทันที
            if (token && !getCookie('access_token')) {
                setCookie('access_token', token, 1);
            }
            if (user && user.role && !getCookie('user_role')) {
                setCookie('user_role', user.role, 1);
            }

            return { token, user };
        } catch (e) {
            return { token: null, user: null };
        }
    }

    function revealPage() {
        const hideStyle = document.getElementById('auth-guard-style');
        if (hideStyle) {
            hideStyle.remove();
        }
    }

    /**
     * ฟังก์ชันออกจากระบบส่วนกลาง
     * ล้าง localStorage, sessionStorage และ Cookies ทั้งหมด แล้วพาไปหน้าแรก
     */
    window.logout = function (shouldRedirect = true) {
        try {
            localStorage.clear();
            sessionStorage.clear();
        } catch (e) {}
        clearCookie('access_token');
        clearCookie('user_role');
        if (shouldRedirect) {
            window.location.replace('/');
        }
    };

    /**
     * ตรวจสอบว่าผู้ใช้ล็อกอินแล้วและมี Role ตรงกับที่กำหนดหรือไม่
     * หากไม่มีสิทธิ์ จะ Redirect ทันทีด้วย window.location.replace
     */
    window.requireAuth = function (allowedRole) {
        const { token, user } = getAuth();

        // 1. ถ้าไม่มี Token หรือข้อมูลผู้ใช้ หรือ Token หมดอายุ -> ส่งกลับไปหน้าแรก (Login)
        if (!token || !user || !user.role || isTokenExpired(token)) {
            window.logout(true);
            return false;
        }

        const currentRole = String(user.role).trim().toLowerCase();
        const targetRole = allowedRole ? String(allowedRole).trim().toLowerCase() : null;

        // 2. ถ้ากำหนด Role แล้วไม่ตรงกัน -> ส่งไปหน้า Dashboard ของ Role ที่ถูกต้อง
        if (targetRole && currentRole !== targetRole) {
            if (currentRole === 'teacher') {
                window.location.replace('/teacher/dashboard');
            } else {
                window.location.replace('/classroom');
            }
            return false;
        }

        // 3. ผ่านการตรวจสอบ ปลด display: none เพื่อแสดงหน้าจอ
        revealPage();
        return true;
    };

    /**
     * สำหรับหน้า Login หรือ Register:
     * หากผู้ใช้ล็อกอินค้างไว้อยู่แล้ว ให้พาไปยังหน้าของตัวเองทันที
     */
    window.redirectIfAuthenticated = function () {
        const { token, user } = getAuth();
        if (token && user && user.role && !isTokenExpired(token)) {
            const currentRole = String(user.role).trim().toLowerCase();
            if (currentRole === 'teacher') {
                window.location.replace('/teacher/dashboard');
            } else {
                window.location.replace('/classroom');
            }
            return true;
        }

        // ถ้ายังไม่ได้ล็อกอิน ให้ปลดซ่อนหน้า Login/Register เพื่อให้ผู้ใช้กรอกข้อมูล
        revealPage();
        return false;
    };
})(window, document);

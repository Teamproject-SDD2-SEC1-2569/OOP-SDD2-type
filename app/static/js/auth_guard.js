/**
 * auth_guard.js
 * ป้องกันการเข้าถึงหน้าเว็บผ่าน URL โดยไม่ได้เข้าสู่ระบบ
 * ทำงานทันทีใน <head> ก่อนที่ <body> จะแสดงผล เพื่อป้องกันหน้ากระพริบ
 */
(function (window) {
    'use strict';

    function getAuth() {
        try {
            const token = localStorage.getItem('token') || localStorage.getItem('accessToken');
            const userStr = localStorage.getItem('user');
            const user = userStr ? JSON.parse(userStr) : null;
            return { token, user };
        } catch (e) {
            return { token: null, user: null };
        }
    }

    /**
     * ตรวจสอบว่าผู้ใช้ล็อกอินแล้วและมี Role ตรงกับที่กำหนดหรือไม่
     * หากไม่มีสิทธิ์ จะ Redirect ทันทีด้วย window.location.replace
     */
    window.requireAuth = function (allowedRole) {
        const { token, user } = getAuth();

        // 1. ถ้าไม่มี Token หรือข้อมูลผู้ใช้ -> ส่งกลับไปหน้าแรก (Login)
        if (!token || !user || !user.role) {
            try { localStorage.clear(); } catch(e) {}
            window.location.replace('/');
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

        return true;
    };

    /**
     * สำหรับหน้า Login หรือ Register:
     * หากผู้ใช้ล็อกอินค้างไว้อยู่แล้ว ให้พาไปยังหน้าของตัวเองทันที
     */
    window.redirectIfAuthenticated = function () {
        const { token, user } = getAuth();
        if (token && user && user.role) {
            const currentRole = String(user.role).trim().toLowerCase();
            if (currentRole === 'teacher') {
                window.location.replace('/teacher/dashboard');
            } else {
                window.location.replace('/classroom');
            }
            return true;
        }
        return false;
    };
})(window);

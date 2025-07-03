// static/main.js
import { initializeEventHandlers } from './eventHandlers.js';

document.addEventListener('DOMContentLoaded', () => {
    let isAuthenticated = false;
    const authDataScript = document.getElementById('serverAuthData');
    if (authDataScript) {
        try {
            const authData = JSON.parse(authDataScript.textContent);
            isAuthenticated = authData.isAuthenticated;
        } catch (e) {
            console.error("无法解析服务器认证数据:", e);
        }
    }
    window.current_user_is_authenticated_from_server = isAuthenticated;
    initializeEventHandlers();
    console.log("MSUT芯片逻辑图应用已初始化 (v3.1 - UI/UX 修复)。");
});
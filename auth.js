// --- AUTH MANAGEMENT ---
const API_BASE_URL = 'http://127.0.0.1:8000/api';

function getAuth() {
    return JSON.parse(localStorage.getItem('currentUser')) || null;
}

function checkAuthAndRedirect() {
    const user = getAuth();
    const isMainPage = window.location.pathname.includes('main.html');

    if (!user && isMainPage) {
        window.location.href = '../index.html';
    } else if (user && !isMainPage) {
        window.location.href = 'html/main.html';
    }
}

async function handleLogin() {
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const errorMsg = document.getElementById('login-error');

    const username = usernameInput.value;
    const password = passwordInput.value;

    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('currentUser', JSON.stringify(data.user));
            window.location.href = 'html/main.html';
        } else {
            errorMsg.style.display = 'block';
        }
    } catch (error) {
        console.error("Login failed:", error);
        alert("서버 연결에 실패했습니다.");
    }
}

function logout() {
    localStorage.removeItem('currentUser');
    // Redirect to root index.html
    const isMainPage = window.location.pathname.includes('main.html');
    window.location.href = isMainPage ? '../index.html' : 'index.html';
}

// Automatically check auth on load
document.addEventListener('DOMContentLoaded', () => {
    const loginSubmit = document.getElementById('login-submit');
    if (loginSubmit) {
        loginSubmit.addEventListener('click', handleLogin);
        document.getElementById('password').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleLogin();
        });
    }

    checkAuthAndRedirect();
});

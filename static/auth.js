/**
 * ReportMaster AI — Authentication Module
 * Client-side session management using localStorage.
 */

const AUTH_STORAGE_KEY = 'rm_users';
const SESSION_KEY = 'rm_session';
const SESSION_DURATION = 7 * 24 * 60 * 60 * 1000; // 7 days

// ============ Crypto Helpers ============
async function hashPassword(password) {
    const encoder = new TextEncoder();
    const data = encoder.encode(password + '_rm_salt_2026');
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

function generateSessionToken() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array).map(b => b.toString(16).padStart(2, '0')).join('');
}

// ============ User Store ============
function getUsers() {
    try {
        return JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY) || '{}');
    } catch {
        return {};
    }
}

function saveUsers(users) {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(users));
}

// ============ Session Management ============
function getSession() {
    try {
        const session = JSON.parse(localStorage.getItem(SESSION_KEY));
        if (!session) return null;
        if (Date.now() > session.expiresAt) {
            localStorage.removeItem(SESSION_KEY);
            return null;
        }
        return session;
    } catch {
        return null;
    }
}

function createSession(user) {
    const session = {
        token: generateSessionToken(),
        email: user.email,
        name: user.name,
        createdAt: Date.now(),
        expiresAt: Date.now() + SESSION_DURATION
    };
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    return session;
}

function destroySession() {
    localStorage.removeItem(SESSION_KEY);
}

// ============ Auth Operations ============
async function registerUser(name, email, password) {
    const users = getUsers();
    const emailKey = email.toLowerCase().trim();

    if (users[emailKey]) {
        return { success: false, error: 'An account with this email already exists.' };
    }

    const hashedPassword = await hashPassword(password);
    users[emailKey] = {
        name: name.trim(),
        email: emailKey,
        password: hashedPassword,
        createdAt: new Date().toISOString(),
        queryCount: 0,
        totalResponseTime: 0,
        conversations: []
    };

    saveUsers(users);
    return { success: true };
}

async function loginUser(email, password) {
    const users = getUsers();
    const emailKey = email.toLowerCase().trim();
    const user = users[emailKey];

    if (!user) {
        return { success: false, error: 'No account found with this email address.' };
    }

    const hashedPassword = await hashPassword(password);
    if (user.password !== hashedPassword) {
        return { success: false, error: 'Incorrect password. Please try again.' };
    }

    const session = createSession(user);
    return { success: true, session };
}

function logoutUser() {
    destroySession();
    window.location.href = '/login';
}

function getCurrentUser() {
    const session = getSession();
    if (!session) return null;

    const users = getUsers();
    return users[session.email] || null;
}

function updateUserData(updates) {
    const session = getSession();
    if (!session) return;

    const users = getUsers();
    if (users[session.email]) {
        Object.assign(users[session.email], updates);
        saveUsers(users);
    }
}

// ============ Auth Guards ============
function requireAuth() {
    const session = getSession();
    if (!session) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

function redirectIfAuthenticated() {
    const session = getSession();
    if (session) {
        window.location.href = '/';
        return true;
    }
    return false;
}

// ============ Password Strength ============
function getPasswordStrength(password) {
    let score = 0;
    if (password.length >= 6) score++;
    if (password.length >= 10) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;

    if (score <= 2) return { level: 'weak', label: 'Weak password', bars: 1 };
    if (score <= 3) return { level: 'medium', label: 'Fair password', bars: 2 };
    if (score <= 4) return { level: 'strong', label: 'Strong password', bars: 3 };
    return { level: 'strong', label: 'Very strong', bars: 4 };
}

// ============ Conversation History ============
function saveConversation(messages) {
    const session = getSession();
    if (!session) return;

    const users = getUsers();
    const user = users[session.email];
    if (!user) return;

    if (!user.conversations) user.conversations = [];

    const conversation = {
        id: Date.now().toString(36) + Math.random().toString(36).substr(2, 5),
        timestamp: new Date().toISOString(),
        preview: messages[0]?.text?.substring(0, 60) || 'New conversation',
        messages: messages
    };

    user.conversations.unshift(conversation);
    // Keep only last 50 conversations
    if (user.conversations.length > 50) {
        user.conversations = user.conversations.slice(0, 50);
    }

    saveUsers(users);
    return conversation.id;
}

function getConversations() {
    const user = getCurrentUser();
    if (!user) return [];
    return user.conversations || [];
}

function getConversation(id) {
    const convs = getConversations();
    return convs.find(c => c.id === id) || null;
}

function deleteConversation(id) {
    const session = getSession();
    if (!session) return;

    const users = getUsers();
    const user = users[session.email];
    if (!user || !user.conversations) return;

    user.conversations = user.conversations.filter(c => c.id !== id);
    saveUsers(users);
}

// ============ User Analytics ============
function trackQuery(responseTime) {
    const session = getSession();
    if (!session) return;

    const users = getUsers();
    const user = users[session.email];
    if (!user) return;

    user.queryCount = (user.queryCount || 0) + 1;
    user.totalResponseTime = (user.totalResponseTime || 0) + responseTime;
    saveUsers(users);
}

function getUserStats() {
    const user = getCurrentUser();
    if (!user) return { queries: 0, avgTime: 0, conversations: 0, joined: '' };

    return {
        queries: user.queryCount || 0,
        avgTime: user.queryCount > 0 ? (user.totalResponseTime / user.queryCount).toFixed(2) : 0,
        conversations: (user.conversations || []).length,
        joined: user.createdAt ? new Date(user.createdAt).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : ''
    };
}

// ============ Theme Management ============
function getTheme() {
    return localStorage.getItem('rm_theme') || 'light';
}

function setTheme(theme) {
    localStorage.setItem('rm_theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
}

function toggleTheme() {
    const current = getTheme();
    const next = current === 'light' ? 'dark' : 'light';
    setTheme(next);
    return next;
}

function initTheme() {
    const saved = getTheme();
    document.documentElement.setAttribute('data-theme', saved);
}

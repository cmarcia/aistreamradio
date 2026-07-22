/**
 * Standalone Reusable OAuth2 / OIDC Auth Client SDK (JavaScript / Node.js)
 * Zero external dependencies. Works in Browsers and Node environments.
 */
export class AuthClient {
    /**
     * @param {Object} [options={}] Configuration options
     * @param {string} [options.baseUrl=''] Base URL of the auth server API
     * @param {'cookie'|'token'} [options.mode='cookie'] Session mode ('cookie' or 'token')
     */
    constructor(options = {}) {
        this.baseUrl = (options.baseUrl || '').replace(/\/$/, '');
        this.mode = options.mode || 'cookie';
        this.token = typeof localStorage !== 'undefined' ? localStorage.getItem('auth_token') : null;
        this.listeners = new Set();
        this.currentUser = null;
    }

    /**
     * Subscribe to authentication state changes.
     * @param {Function} callback Callback receiving (user | null)
     * @returns {Function} Unsubscribe function
     */
    onAuthStateChanged(callback) {
        this.listeners.add(callback);
        // Fire immediately with current state
        callback(this.currentUser);
        return () => this.listeners.delete(callback);
    }

    _notify(user) {
        this.currentUser = user;
        this.listeners.forEach(cb => {
            try {
                cb(user);
            } catch (err) {
                console.error('[AuthClient] Callback error:', err);
            }
        });
    }

    /**
     * Set access token manually when using 'token' mode.
     * @param {string|null} token Access token string
     */
    setToken(token) {
        this.token = token;
        if (typeof localStorage !== 'undefined') {
            if (token) {
                localStorage.setItem('auth_token', token);
            } else {
                localStorage.removeItem('auth_token');
            }
        }
    }

    /**
     * Redirects browser to initiate OAuth login for specified provider.
     * @param {string} provider Provider ID ('google', 'microsoft', etc.)
     */
    login(provider) {
        if (!provider) {
            throw new Error('Provider name is required for login.');
        }
        const loginUrl = `${this.baseUrl}/auth/login/${provider}`;
        if (typeof window !== 'undefined') {
            window.location.href = loginUrl;
        }
        return loginUrl;
    }

    /**
     * Fetches current available identity providers.
     * @returns {Promise<Array<{id: string, name: string, icon_url?: string}>>}
     */
    async getProviders() {
        try {
            const response = await fetch(`${this.baseUrl}/auth/providers`, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });
            if (!response.ok) return [];
            const data = await response.json();
            return data.providers || [];
        } catch (err) {
            console.error('[AuthClient] Error fetching providers:', err);
            return [];
        }
    }

    /**
     * Fetches current authenticated user profile.
     * @returns {Promise<Object|null>} User profile object or null if unauthenticated
     */
    async getUser() {
        try {
            const headers = { 'Accept': 'application/json' };
            if (this.mode === 'token' && this.token) {
                headers['Authorization'] = `Bearer ${this.token}`;
            }

            const response = await fetch(`${this.baseUrl}/auth/me`, {
                method: 'GET',
                headers,
                credentials: this.mode === 'cookie' ? 'include' : 'same-origin'
            });

            if (!response.ok) {
                this._notify(null);
                return null;
            }

            const user = await response.json();
            this._notify(user);
            return user;
        } catch (err) {
            console.error('[AuthClient] Error fetching current user:', err);
            this._notify(null);
            return null;
        }
    }

    /**
     * Registers a new user with email and password.
     * @param {string} email
     * @param {string} password
     * @param {string} [fullName]
     * @returns {Promise<Object>} User object
     */
    async registerEmailPassword(email, password, fullName) {
        const response = await fetch(`${this.baseUrl}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: this.mode === 'cookie' ? 'include' : 'same-origin',
            body: JSON.stringify({ email, password, full_name: fullName || null })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Registration failed.');
        }

        this._notify(data);
        return data;
    }

    /**
     * Authenticates existing user with email and password.
     * @param {string} email
     * @param {string} password
     * @returns {Promise<Object>} User object
     */
    async loginEmailPassword(email, password) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: this.mode === 'cookie' ? 'include' : 'same-origin',
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Login failed.');
        }

        this._notify(data);
        return data;
    }

    /**
     * Logs out current user and invalidates session.
     */
    async logout() {
        try {
            await fetch(`${this.baseUrl}/auth/logout`, {
                method: 'POST',
                headers: { 'Accept': 'application/json' },
                credentials: this.mode === 'cookie' ? 'include' : 'same-origin'
            });
        } catch (err) {
            console.warn('[AuthClient] Logout request warning:', err);
        } finally {
            if (this.mode === 'token') {
                this.setToken(null);
            }
            this._notify(null);
        }
    }
}


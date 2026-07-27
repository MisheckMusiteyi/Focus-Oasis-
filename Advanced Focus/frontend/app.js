/**
 * Advanced Focus Portal JS Controller
 * Handles token storage, security, session lifecycle, and communication with the FastAPI Backend.
 */

const API_BASE_URL = "http://127.0.0.1:8000";

const AppController = {
    // Save authentication details in secure LocalStorage
    saveSession(token, userType, username, displayName) {
        localStorage.setItem("af_access_token", token);
        localStorage.setItem("af_user_type", userType);
        localStorage.setItem("af_username", username);
        localStorage.setItem("af_display_name", displayName);
    },

    // Clear local cache session on Logout
    logout() {
        localStorage.removeItem("af_access_token");
        localStorage.removeItem("af_user_type");
        localStorage.removeItem("af_username");
        localStorage.removeItem("af_display_name");
    },

    isAuthenticated() {
        return localStorage.getItem("af_access_token") !== null;
    },

    getSession() {
        return {
            token: localStorage.getItem("af_access_token"),
            userType: localStorage.getItem("af_user_type"),
            username: localStorage.getItem("af_username"),
            displayName: localStorage.getItem("af_display_name")
        };
    },

    // General-purpose request wrapper with JWT Header attachments
    async request(endpoint, options = {}) {
        const session = this.getSession();
        const headers = {
            "Content-Type": "application/json",
            ...(options.headers || {})
        };

        if (session.token) {
            headers["Authorization"] = `Bearer ${session.token}`;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
            if (response.status === 401) {
                // Token expired or invalid, force logout
                this.logout();
                window.location.href = "index.html";
                return { success: false, error: "Session expired. Please log in again." };
            }

            if (!response.ok) {
                const errorData = await response.json();
                return { success: false, error: errorData.detail || "An error occurred." };
            }

            if (response.status === 204) {
                return { success: true };
            }

            const data = await response.json().catch(() => ({}));
            return { success: true, data };
        } catch (err) {
            return { success: false, error: "Network error or backend is offline." };
        }
    },

    // Log in action
    async login(username, password) {
        const params = new URLSearchParams();
        params.append("username", username);
        params.append("password", password);

        try {
            const res = await fetch(`${API_BASE_URL}/api/token`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: params
            });

            if (!res.ok) {
                const errorData = await res.json();
                return { success: false, error: errorData.detail || "Invalid credentials." };
            }

            const data = await res.json();
            this.saveSession(data.access_token, data.user_type, data.username, data.display_name);
            return { success: true };
        } catch (err) {
            return { success: false, error: "Failed to connect to API server." };
        }
    },

    // Seed Initial Admin
    async seedAdmin(username, email, password) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/setup/admin`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, email, password })
            });

            if (!response.ok) {
                const errorData = await response.json();
                return { success: false, error: errorData.detail || "Failed to setup administrator." };
            }
            return { success: true };
        } catch (err) {
            return { success: false, error: "API connection failed." };
        }
    },

    // ============================================
    // STUDENT API INTERFACES
    // ============================================
    async getStudentProfile() {
        return await this.request("/api/student/profile");
    },

    async updateStudentProfile(payload) {
        return await this.request("/api/student/profile", {
            method: "PUT",
            body: JSON.stringify(payload)
        });
    },

    // ============================================
    // ADMIN API INTERFACES (CRUD)
    // ============================================
    async getAdminOverview() {
        return await this.request("/api/admin/overview");
    },

    async getAdminStudentsList() {
        return await this.request("/api/admin/students");
    },

    async createStudent(payload) {
        return await this.request("/api/admin/students", {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },

    async deleteStudent(studentId) {
        try {
            const session = this.getSession();
            const res = await fetch(`${API_BASE_URL}/api/admin/students/${studentId}`, {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${session.token}`
                }
            });
            if (res.status === 204 || res.ok) {
                return { success: true };
            }
            const errorData = await res.json();
            return { success: false, error: errorData.detail || "Delete operation failed." };
        } catch (err) {
            return { success: false, error: "API connection failed." };
        }
    },

    async addFeePayment(payload) {
        return await this.request("/api/admin/payments", {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },

    async addPerformance(payload) {
        return await this.request("/api/admin/performances", {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },

    async addAttendance(payload) {
        return await this.request("/api/admin/attendances", {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },

    async addExpense(payload) {
        return await this.request("/api/admin/expenses", {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },

    async getAdminExpensesList() {
        return await this.request("/api/admin/expenses");
    },

    async addIncome(payload) {
        return await this.request("/api/admin/income", {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },

    async getAdminIncomeList() {
        return await this.request("/api/admin/income");
    },

    // Utility helper to extract dynamic initials (e.g. "John Doe" -> "JD")
    getInitials(name) {
        if (!name) return "?";
        const parts = name.trim().split(/\s+/);
        if (parts.length === 1) return parts[0][0].toUpperCase();
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
};

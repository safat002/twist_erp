import axios from 'axios';

const API_URL = '/api/v1/auth/';

// A mock login function
export const login = async (username, password) => {
    // In a real app, you'd make a POST request to your auth endpoint
    // For now, we'll simulate a successful login for a specific user
    // and a failure for any other.
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            if (username === 'admin' && password === 'password') {
                // Simulate setting a token
                localStorage.setItem('userToken', 'fake-jwt-token');
                resolve({ message: "Login successful" });
            } else {
                reject({ message: "Invalid credentials" });
            }
        }, 1000);
    });

    /*
    // Example of a real API call with axios:
    try {
        const response = await axios.post(API_URL + 'login/', {
            username,
            password,
        });
        if (response.data.token) {
            localStorage.setItem('userToken', response.data.token);
        }
        return response.data;
    } catch (error) {
        throw error;
    }
    */
};

export const logout = () => {
    localStorage.removeItem('userToken');
};

export const isAuthenticated = () => {
    return localStorage.getItem('userToken') !== null;
};

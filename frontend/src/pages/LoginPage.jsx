import React, { useState } from 'react';
import '../styles/LoginPage.css';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const success = await login(username, password);
      if (success) {
        navigate('/');
      } else {
        setError('Invalid username or password. Please try again.');
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again later.');
      console.error('Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-pattern" />
      <div className="login-hero">
        <div className="hero-brand">
          <span className="logo-glow">TWIST</span>
          <span className="brand-subtitle">Visual ERP Control Tower</span>
        </div>
        <div className="hero-copy">
          <h1>
            Design your ERP workspace<span> visually.</span>
          </h1>
          <p>
            Drag-and-drop dashboards, AI-assisted workflows, and multi-company insights — crafted for teams
            that want configurability without the chaos.
          </p>
        </div>
        <div className="hero-metrics">
          <div className="metric-card">
            <span className="metric-value">24</span>
            <span className="metric-label">Composable modules</span>
          </div>
          <div className="metric-card">
            <span className="metric-value">8x</span>
            <span className="metric-label">Faster go-live</span>
          </div>
          <div className="metric-card">
            <span className="metric-value">∞</span>
            <span className="metric-label">Drag & drop layouts</span>
          </div>
        </div>
        <div className="hero-chips">
          <span className="chip">AI companion on every screen</span>
          <span className="chip">Visual form builder</span>
          <span className="chip">Multi-company sandbox</span>
          <span className="chip">Real-time control towers</span>
        </div>
      </div>

      <div className="login-panel">
        <div className="login-card">
          <header className="login-card__header">
            <h2>Sign in to Twist ERP</h2>
            <p>Enter your credentials to continue your workspace session.</p>
          </header>
          <form onSubmit={handleSubmit} className="login-form">
            {error ? <p className="login-form__error">{error}</p> : null}
            <label htmlFor="username" className="login-form__label">
              Work email or username
            </label>
            <input
              id="username"
              type="text"
              className="login-form__input"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="john.doe@twist.co"
              required
              disabled={loading}
              autoComplete="username"
            />

            <label htmlFor="password" className="login-form__label">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="login-form__input"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
              autoComplete="current-password"
            />

            <div className="login-form__actions">
              <a href="#" className="login-form__link">
                Forgot password?
              </a>
            </div>

            <button type="submit" className="login-form__submit" disabled={loading}>
              {loading ? 'Launching control tower…' : 'Enter workspace'}
            </button>
          </form>

          <footer className="login-card__footer">
            <span>New to Twist?</span>
            <a href="#">Request a sandbox</a>
          </footer>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;

import React, { useState, useEffect } from 'react';
import api, { auth } from './api';
import Timetable from './Timetable';
import Manage from './Manage';

export default function App() {
  const [user, setUser] = useState(() => auth.getUser());
  const [currentTab, setCurrentTab] = useState('timetable'); // 'timetable' | 'manage' | 'overview'

  // Login / Signup Form state
  const [isSignUp, setIsSignUp] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [signupBatch, setSignupBatch] = useState('Batch-A1');
  const [loginError, setLoginError] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);

  // Overview stats state
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (user && currentTab === 'overview') {
      api.get('/dashboard/stats/')
        .then((res) => setStats(res.data))
        .catch(() => {});
    }
  }, [user, currentTab]);

  const handleLogin = async (e) => {
    if (e) e.preventDefault();
    setLoginError('');
    setLoggingIn(true);
    try {
      const loggedUser = await auth.login(username, password);
      setUser(loggedUser);
    } catch (err) {
      setLoginError(err.response?.data?.detail || 'Invalid username or password.');
    } finally {
      setLoggingIn(false);
    }
  };

  const handleSignUp = async (e) => {
    if (e) e.preventDefault();
    setLoginError('');
    if (!username.trim()) {
      setLoginError('Please enter a username.');
      return;
    }
    if (password.length < 4) {
      setLoginError('Password must be at least 4 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setLoginError('Passwords do not match. Please re-enter.');
      return;
    }
    setLoggingIn(true);
    try {
      const loggedUser = await auth.register(username.trim(), password, signupBatch);
      setUser(loggedUser);
    } catch (err) {
      const msg = err.response?.data?.username?.[0] || err.response?.data?.error || err.response?.data?.detail || 'Sign up failed. Please try again.';
      setLoginError(msg);
    } finally {
      setLoggingIn(false);
    }
  };

  const handleQuickLogin = async (u, p) => {
    setUsername(u);
    setPassword(p);
    setLoginError('');
    setLoggingIn(true);
    try {
      const loggedUser = await auth.login(u, p);
      setUser(loggedUser);
    } catch (err) {
      setLoginError(err.response?.data?.detail || 'Login failed.');
    } finally {
      setLoggingIn(false);
    }
  };

  const handleLogout = () => {
    auth.logout();
    setUser(null);
    setCurrentTab('timetable');
  };

  // 1. If not logged in, render simple clean Login / Sign Up Screen
  if (!user) {
    return (
      <div className="login-screen">
        <div className="login-card">
          <div className="login-header">
            <div className="college-badge">🏛️ MITS GWALIOR</div>
            <h1>Automated Classroom Scheduling</h1>
            <p>Department of Information Technology</p>
          </div>

          {/* Toggle between Sign In and Student Sign Up */}
          <div className="auth-tabs">
            <button
              type="button"
              className={`auth-tab ${!isSignUp ? 'active' : ''}`}
              onClick={() => { setIsSignUp(false); setLoginError(''); }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`auth-tab ${isSignUp ? 'active' : ''}`}
              onClick={() => { setIsSignUp(true); setLoginError(''); }}
            >
              Student Sign Up
            </button>
          </div>

          {loginError && <div className="alert-banner alert-error">{loginError}</div>}

          {!isSignUp ? (
            /* Sign In Form */
            <form onSubmit={handleLogin} className="login-form">
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter username"
                />
              </div>

              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                />
              </div>

              <button type="submit" className="btn btn-primary btn-block" disabled={loggingIn}>
                {loggingIn ? 'Signing in...' : 'Sign In'}
              </button>

              <div className="auth-switch-link">
                Don't have an account?{' '}
                <button type="button" onClick={() => { setIsSignUp(true); setLoginError(''); }}>
                  Sign up with your Batch
                </button>
              </div>

              <div className="quick-login-section">
                <small>Quick Demo Login:</small>
                <div className="quick-login-buttons">
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => handleQuickLogin('admin', 'admin123')}
                  >
                    🔑 Admin Demo (admin / admin123)
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => handleQuickLogin('viewer', 'viewer123')}
                  >
                    👁️ Viewer Demo (viewer / viewer123)
                  </button>
                </div>
              </div>
            </form>
          ) : (
            /* Student Sign Up Form */
            <form onSubmit={handleSignUp} className="login-form">
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Choose username (e.g. rahul_a1)"
                />
              </div>

              <div className="form-group">
                <label>Your Student Batch / Section</label>
                <select
                  value={signupBatch}
                  onChange={(e) => setSignupBatch(e.target.value)}
                  className="auth-select"
                >
                  <option value="Batch-A1">Batch A1 (Sec A Theory + A1 Labs)</option>
                  <option value="Batch-A2">Batch A2 (Sec A Theory + A2 Labs)</option>
                  <option value="Batch-B1">Batch B1 (Sec B Theory + B1 Labs)</option>
                  <option value="Batch-B2">Batch B2 (Sec B Theory + B2 Labs)</option>
                  <option value="SEC-A">Section A (Complete Section A)</option>
                  <option value="SEC-B">Section B (Complete Section B)</option>
                </select>
                <small style={{ color: '#64748b', fontSize: '11px', marginTop: '4px', display: 'block' }}>
                  You will only see the timetable classes for this selected batch.
                </small>
              </div>

              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Create password (min 4 characters)"
                />
              </div>

              <div className="form-group">
                <label>Confirm Password</label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter password"
                />
              </div>

              <button type="submit" className="btn btn-primary btn-block" disabled={loggingIn}>
                {loggingIn ? 'Registering...' : '🎓 Create Account & View Timetable'}
              </button>

              <div className="auth-switch-link">
                Already registered?{' '}
                <button type="button" onClick={() => { setIsSignUp(false); setLoginError(''); }}>
                  Sign in here
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    );
  }

  const isAdmin = user.role === 'ADMIN' || user.is_staff;

  // 2. Main Authenticated Application
  return (
    <div className="app-layout">
      {/* Top Navigation Bar */}
      <header className="navbar">
        <div className="nav-brand">
          <span className="brand-logo">🏛️</span>
          <div>
            <strong>MITS Gwalior</strong>
            <small>Classroom Scheduler</small>
          </div>
        </div>

        <nav className="nav-tabs">
          <button
            className={`nav-tab ${currentTab === 'timetable' ? 'active' : ''}`}
            onClick={() => setCurrentTab('timetable')}
          >
            📅 Timetable
          </button>
          <button
            className={`nav-tab ${currentTab === 'manage' ? 'active' : ''}`}
            onClick={() => setCurrentTab('manage')}
          >
            📂 Manage Campus (Upload)
          </button>
          <button
            className={`nav-tab ${currentTab === 'overview' ? 'active' : ''}`}
            onClick={() => setCurrentTab('overview')}
          >
            📊 Overview
          </button>
        </nav>

        <div className="nav-user">
          <span className={`user-badge ${isAdmin ? 'badge-admin' : 'badge-viewer'}`}>
            👤 {user.username} ({isAdmin ? 'Admin' : (user.batch ? `${user.batch.replace('Batch-', 'Batch ').replace('SEC-', 'Sec ')}` : 'Viewer')})
          </span>
          <button className="btn-logout" onClick={handleLogout} title="Sign Out">
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {currentTab === 'timetable' && <Timetable user={user} />}
        {currentTab === 'manage' && <Manage user={user} />}
        {currentTab === 'overview' && (
          <div className="tab-container">
            <h2>Campus & Timetable Overview</h2>
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-icon">🏛️</span>
                <div>
                  <div className="stat-num">{stats?.counts?.rooms ?? 0}</div>
                  <div className="stat-title">Classrooms & Labs</div>
                </div>
              </div>

              <div className="stat-card">
                <span className="stat-icon">👤</span>
                <div>
                  <div className="stat-num">{stats?.counts?.teachers ?? 0}</div>
                  <div className="stat-title">Faculty Instructors</div>
                </div>
              </div>

              <div className="stat-card">
                <span className="stat-icon">📚</span>
                <div>
                  <div className="stat-num">{stats?.counts?.courses ?? 0}</div>
                  <div className="stat-title">Total Subjects</div>
                </div>
              </div>

              <div className="stat-card">
                <span className="stat-icon">📅</span>
                <div>
                  <div className="stat-num">{stats?.counts?.total_scheduled_sessions ?? 0}</div>
                  <div className="stat-title">Scheduled Sessions</div>
                </div>
              </div>
            </div>

            <div className="table-card" style={{ marginTop: '24px' }}>
              <h3>Timetable Health & Constraints Status</h3>
              <table className="data-table">
                <tbody>
                  <tr>
                    <td><strong>Hard Conflicts:</strong></td>
                    <td><span className="badge badge-lecture">0 Clashes</span></td>
                  </tr>
                  <tr>
                    <td><strong>Solver Method:</strong></td>
                    <td>Constraint Satisfaction Problem (CSP) Backtracking with Forward Checking</td>
                  </tr>
                  <tr>
                    <td><strong>Room Utilization:</strong></td>
                    <td>Smallest suitable room heuristic to reduce empty seating</td>
                  </tr>
                  <tr>
                    <td><strong>Export Features:</strong></td>
                    <td>Instant PDF export, Multi-Tab Excel (.xlsx) export, CSV download</td>
                  </tr>
                  <tr>
                    <td><strong>Database Concurrency:</strong></td>
                    <td>SQLite default demo mode + PostgreSQL supported via <code>DATABASE_URL</code></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

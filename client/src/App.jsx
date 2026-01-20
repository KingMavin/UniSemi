import { useState, useEffect, useCallback } from 'react';
import authFetch from './utils/authFetch';
import Admin from './Admin';
import './App.css';

// --- CONFIGURATION ---
const SESSION_TIMEOUT = 9 * 60 * 1000; // 5 Minutes (in milliseconds)

// Helpers
function getStudentName(s) {
  if (!s) return '';
  return s.name || [s.surname, s.othernames].join(' ') || s.matricNumber || '';
}
function getSemesterGPA(sem) { return sem.gpa ?? sem.semesterGPA ?? sem.semGPA ?? 0; }

// --- LOGIN COMPONENT ---
function Login({ onLogin }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setError(''); setLoading(true);
    try {
      const body = await authFetch('/api/login', { method: 'POST', body: JSON.stringify({ passcode: password }) });
      if (body.success) onLogin(password);
      else setError(body.error || 'Access Denied');
    } catch (err) { setError('Login failed. Check server connection.'); } 
    finally { setLoading(false); }
  };

  return (
    <div className="login-card" style={{ maxWidth: '400px', margin: '40px auto', textAlign: 'center' }}>
      <h2 style={{ color: 'var(--primary-color)' }}>Admin Portal</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '20px' }}>Please authenticate to continue.</p>
      
      <input type="password" placeholder="Enter Admin Passcode" value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleLogin()} />
      <button className="primary-btn" onClick={handleLogin} style={{ width: '100%', marginTop: '10px' }}>
        {loading && <div className="loading-spinner" style={{ marginRight: '8px' }}></div>}
        Login
      </button>
      {error && <div className="error-msg">{error}</div>}
    </div>
  );
}

// --- MAIN APP ---
function App() {
  const [view, setView] = useState('student');
  const [isAuthenticated, setIsAuthenticated] = useState(false); // Default to false initially
  const [serverConnected, setServerConnected] = useState(null);
  
  // Search State
  const [matricNumber, setMatricNumber] = useState('');
  const [studentData, setStudentData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // --- SESSION LOGIC ---
  const handleLogout = useCallback(() => {
    localStorage.removeItem('admin_passcode');
    localStorage.removeItem('session_expiry'); // Clear the timer
    setIsAuthenticated(false);
    setView('student');
    setStudentData(null);
  }, []);

  const handleLoginSuccess = (passcode) => {
    const expiryTime = Date.now() + SESSION_TIMEOUT;
    localStorage.setItem('admin_passcode', passcode);
    localStorage.setItem('session_expiry', expiryTime); // Save the timer
    setIsAuthenticated(true);
    setView('admin');
  };

  // Reset timer on user interaction (Click or Keypress)
  const updateActivity = () => {
    if (isAuthenticated) {
      const newExpiry = Date.now() + SESSION_TIMEOUT;
      localStorage.setItem('session_expiry', newExpiry);
    }
  };

  // Check session on Load and periodically
  useEffect(() => {
    const checkSession = () => {
      const passcode = localStorage.getItem('admin_passcode');
      const expiry = localStorage.getItem('session_expiry');
      
      if (passcode && expiry) {
        if (Date.now() > parseInt(expiry)) {
          // Time expired!
          console.log("Session expired due to inactivity");
          handleLogout();
        } else {
          // Still valid
          setIsAuthenticated(true);
        }
      } else {
        setIsAuthenticated(false);
      }
    };

    // Run once on mount
    checkSession();

    // Run every 1 minute to auto-logout if window is left open
    const interval = setInterval(checkSession, 60000); 
    
    // Listen for activity to reset timer
    window.addEventListener('click', updateActivity);
    window.addEventListener('keypress', updateActivity);

    return () => {
      clearInterval(interval);
      window.removeEventListener('click', updateActivity);
      window.removeEventListener('keypress', updateActivity);
    };
  }, [isAuthenticated, handleLogout]);
  // ---------------------

  const handleSearch = async () => {
    if (!matricNumber) return;
    setLoading(true); setError(''); setStudentData(null);
    try {
      const body = await authFetch(`/api/results/${matricNumber}`);
      setStudentData(body.data ?? body);
    } catch (err) { setError('Student not found or invalid Matric Number.'); } 
    finally { setLoading(false); }
  };

  useEffect(() => {
    let mounted = true;
    const ping = async () => {
      try {
        await authFetch('/api/results/SEED001', { method: 'GET', timeout: 3000 });
        if (mounted) setServerConnected(true);
      } catch (err) { if (mounted) setServerConnected(err && err.response ? true : false); }
    };
    ping();
    const id = setInterval(ping, 10000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  return (
    <div className="container">
      <header>
        <div className="header-content">
          <h1>University Portal</h1>
          <p>Academic Records System</p>
        </div>
        <div className="status-indicator">
          <span className="status-dot" style={{ backgroundColor: serverConnected ? 'var(--success)' : 'var(--danger)' }}></span>
          {serverConnected === null ? 'Checking...' : serverConnected ? 'Online' : 'Offline'}
        </div>
      </header>

      <nav>
        <div className="nav-group">
          <button className={view === 'student' ? 'nav-active' : 'secondary-btn'} onClick={() => setView('student')}>
            Student Portal
          </button>
          <button className={view === 'admin' || view === 'login' ? 'nav-active' : 'secondary-btn'} onClick={() => setView(isAuthenticated ? 'admin' : 'login')}>
            Admin Dashboard
          </button>
        </div>
        {isAuthenticated && <button className="danger-btn" style={{ borderColor: 'rgba(255,255,255,0.5)', color: 'white', backgroundColor: 'rgba(220, 53, 69, 0.8)' }} onClick={handleLogout}>Logout</button>}
      </nav>

      {/* VIEWS */}
      {view === 'login' && <Login onLogin={handleLoginSuccess} />}
      {view === 'admin' && isAuthenticated && <Admin />}

      {view === 'student' && (
        <>
          <div className="search-card" style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <input placeholder="Enter Matric Number (e.g., U2024-001)" value={matricNumber} onChange={(e) => setMatricNumber(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && !loading && handleSearch()} style={{ marginBottom: 0 }} />
            <button className="primary-btn" onClick={handleSearch} disabled={loading} style={{ minWidth: '140px', height: '45px' }}>
              {loading ? 'Searching...' : 'Check Result'}
            </button>
          </div>
          
          {error && <div className="error-msg">{error}</div>}

          {studentData && (
            <div className="result-card">
              <div style={{ borderBottom: '2px solid var(--primary-color)', paddingBottom: '20px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' }}>
                <div>
                  <h2 style={{ margin: 0, color: 'var(--primary-color)' }}>{getStudentName(studentData)}</h2>
                  <p style={{ margin: '5px 0', color: 'var(--text-muted)' }}>Matric No: {studentData.matricNumber}</p>
                  <p style={{ margin: 0 }}>Department: <strong>{studentData.department}</strong></p>
                </div>
                <div style={{ textAlign: 'center', background: '#f0f4f8', padding: '15px 25px', borderRadius: '8px' }}>
                  <span style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Current CGPA</span>
                  <span style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--primary-color)' }}>{studentData.cgpa}</span>
                </div>
              </div>

              {studentData.academicHistory?.length > 0 ? (
                studentData.academicHistory.map((semester, idx) => (
                  <div key={idx} style={{ marginBottom: '30px' }}>
                    <div style={{ background: 'var(--primary-color)', color: 'white', padding: '10px 15px', borderRadius: '4px 4px 0 0', display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: '600' }}>{semester.level} Level - {semester.semester} Semester</span>
                      <span>GPA: {getSemesterGPA(semester)}</span>
                    </div>
                    <div className="table-container" style={{ borderRadius: '0 0 4px 4px' }}>
                      <table>
                        <thead>
                          <tr>
                            <th>Course Code</th>
                            <th>Unit</th>
                            <th>Score</th>
                            <th>Grade</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(semester.courses || semester.processedCourses || []).map((c, i) => (
                            <tr key={i}>
                              <td>{c.courseCode || c.code}</td>
                              <td>{c.unit || c.units}</td>
                              <td>{c.score}</td>
                              <td style={{ fontWeight: 'bold', color: c.grade === 'F' ? 'var(--danger)' : 'var(--success)' }}>{c.grade || c.letter}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>No academic records found.</div>
              )}
              
              <div style={{ marginTop: '20px', textAlign: 'right' }}>
                <button className="secondary-btn" onClick={() => window.print()} style={{ color: 'var(--primary-color)', borderColor: 'var(--primary-color)' }}>Print Transcript</button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default App;
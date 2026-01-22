import React, { useState, useEffect } from 'react';
import authFetch from './utils/authFetch';
import './App.css';

export default function Admin() {
  const [formData, setFormData] = useState({
    matricNumber: '', name: '', department: '', level: '', semester: 'First',
    yearOfAdmission: new Date().getFullYear(),
    courses: [{ courseCode: '', score: '', grade: '', unit: '3', scoreError: false }]
  });

  const [message, setMessage] = useState('');
  const [logs, setLogs] = useState([]);      
  const [students, setStudents] = useState([]); 
  const [stats, setStats] = useState({ total: 0, avgCGPA: '0.00', highestCGPA: '0.00' });
  
  // History Modal State
  const [showHistory, setShowHistory] = useState(false);
  const [historyData, setHistoryData] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState('');

  // INNOVATION: Action Menu State
  const [activeDropdown, setActiveDropdown] = useState(null);

  // --- API CALLS ---
  const fetchLogs = async () => {
    try { 
        const response = await authFetch('/api/logs'); 
        setLogs(Array.isArray(response.data) ? response.data : response || []); 
    } catch (err) { console.error(err); }
  };

  const fetchStudents = async () => {
    try {
      const response = await authFetch('/api/students');
      const studentsList = Array.isArray(response.data) ? response.data : response || [];
      setStudents(studentsList);
      calculateStats(studentsList);
    } catch (err) { console.error(err); }
  };

  const calculateStats = (list) => {
    if (list.length === 0) return;
    const total = list.length;
    const sumCGPA = list.reduce((acc, curr) => acc + parseFloat(curr.cgpa || 0), 0);
    const avg = (sumCGPA / total).toFixed(2);
    const highest = Math.max(...list.map(s => parseFloat(s.cgpa || 0))).toFixed(2);
    setStats({ total, avgCGPA: avg, highestCGPA: highest });
  };

  useEffect(() => { 
      fetchLogs(); 
      fetchStudents();
      
      // Close dropdown if clicking anywhere else
      const closeMenu = () => setActiveDropdown(null);
      window.addEventListener('click', closeMenu);
      return () => window.removeEventListener('click', closeMenu);
  }, []);

  // --- FORM LOGIC ---
  const getGradePoint = (score) => {
    const s = parseInt(score);
    if (isNaN(s)) return 0;
    if (s >= 70) return { grade: 'A', point: 5 };
    if (s >= 60) return { grade: 'B', point: 4 };
    if (s >= 50) return { grade: 'C', point: 3 };
    if (s >= 45) return { grade: 'D', point: 2 };
    return { grade: 'F', point: 0 };
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    const uppercasedValue = (name === 'matricNumber' || name === 'department' || name === 'level') 
      ? value.toUpperCase() : value; 
    setFormData({ ...formData, [name]: uppercasedValue });
  };

  const handleCourseChange = (index, e) => {
    const { name, value } = e.target;
    const newCourses = [...formData.courses];
    
    if (name === 'score') {
        const numericValue = value === '' ? '' : parseInt(value);
        newCourses[index][name] = (numericValue !== '' && numericValue > 100) ? 100 : numericValue;
        newCourses[index].scoreError = (numericValue > 100);
    } else if (name === 'courseCode') {
        newCourses[index][name] = value.toUpperCase();
    } else {
        newCourses[index][name] = value;
    }
    setFormData({ ...formData, courses: newCourses });
  };

  const addCourse = () => setFormData({ ...formData, courses: [...formData.courses, { courseCode: '', score: '', grade: '', unit: '3', scoreError: false }] });

  const removeCourse = (index) => {
    if (formData.courses.length === 1) return alert("You must have at least one course.");
    setFormData({ ...formData, courses: formData.courses.filter((_, i) => i !== index) });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await authFetch('/api/results', { method: 'POST', body: JSON.stringify(formData) });
      setMessage('✅ Result Processed Successfully!');
      fetchLogs(); fetchStudents();
      setFormData({
        matricNumber: '', name: '', department: '', level: '', semester: 'First',
        yearOfAdmission: new Date().getFullYear(),
        courses: [{ courseCode: '', score: '', grade: '', unit: '3', scoreError: false }]
      });
    } catch (err) { setMessage(`❌ Operation Failed: ${err.message || 'Unknown error'}`); }
  };

  const handleDeleteStudent = async (matric) => {
    if(!window.confirm(`Delete record for ${matric}?`)) return;
    try { 
        await authFetch(`/api/results/${matric}`, { method: 'DELETE' }); 
        fetchStudents(); fetchLogs(); 
    } catch (err) { setMessage(`❌ Delete failed: ${err.message}`); }
  };

  const handleEditStudent = async (matric) => {
    try {
        const response = await authFetch(`/api/results/${matric}`);
        const data = response.data || response;
        
        let lastCourses = [{ courseCode: '', score: '', grade: '', unit: '3' }];
        let lastLevel = '';
        let lastSemester = 'First';

        if (data.academicHistory && data.academicHistory.length > 0) {
            const lastEntry = data.academicHistory[data.academicHistory.length - 1];
            lastCourses = lastEntry.courses || lastCourses;
            lastLevel = lastEntry.level;
            lastSemester = lastEntry.semester;
        }

        setFormData({
            matricNumber: data.matricNumber,
            name: data.name,
            department: data.department,
            level: lastLevel,
            semester: lastSemester,
            yearOfAdmission: new Date().getFullYear(),
            courses: lastCourses
        });
        window.scrollTo(0, 0); 
        setMessage('✏️ Loaded student data for editing.');
    } catch (err) { setMessage(`❌ Fetch failed: ${err.message}`); }
  };

  const handleViewHistory = async (matric) => {
      setSelectedStudent(matric);
      try {
          const response = await authFetch(`/api/history/${matric}`);
          setHistoryData(response.data || response || []);
          setShowHistory(true);
      } catch (err) { console.error(err); }
  };

  const clearAllLogs = async () => {
    const password = prompt("Enter Admin Passcode to confirm clear:");
    if (password !== 'admin123') return alert("Wrong Passcode");
    try {
      await authFetch('/api/logs', { method: 'DELETE' });
      fetchLogs(); setMessage('✅ Logs cleared successfully');
    } catch (err) { setMessage(`❌ Failed to clear logs: ${err.message}`); }
  };
  
  // Toggle Menu helper
  const toggleMenu = (e, matric) => {
      e.stopPropagation(); // Stop click from bubbling to window (which closes it)
      setActiveDropdown(activeDropdown === matric ? null : matric);
  };

  return (
    <div className="result-card">
      <h2 style={{ color: 'var(--primary-color)', marginBottom: '20px' }}>⚙️ Admin Dashboard</h2>
      
      {/* STATS */}
      <div className="stats-grid">
        <div className="stats-card"><h3>{stats.total}</h3><span>Total Students</span></div>
        <div className="stats-card"><h3>{stats.avgCGPA}</h3><span>Average CGPA</span></div>
        <div className="stats-card"><h3>{stats.highestCGPA}</h3><span>Highest CGPA</span></div>
      </div>

      {message && <div className={message.includes('✅') || message.includes('✏️') ? 'message-success' : 'message-error'}>{message}</div>}
      
      {/* UPLOAD FORM */}
      <form onSubmit={handleSubmit} style={{ marginBottom: '40px' }}>
        <h3 style={{ marginBottom: '15px', color: 'var(--text-main)' }}>📝 Upload / Update Result</h3>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '15px' }}>
            <input name="matricNumber" placeholder="Matric Number" value={formData.matricNumber} onChange={handleChange} required />
            <input name="name" placeholder="Student Name" value={formData.name} onChange={handleChange} required />
            <input name="department" placeholder="Department" value={formData.department} onChange={handleChange} required />
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                <select name="level" value={formData.level} onChange={handleChange} required>
                    <option value="">Select Level</option>
                    {[100,200,300,400,500].map(l => <option key={l} value={l}>{l} Level</option>)}
                </select>
                <select name="semester" value={formData.semester} onChange={handleChange}>
                    <option value="First">First Semester</option>
                    <option value="Second">Second Semester</option>
                </select>
            </div>
        </div>

        {/* COURSES */}
        <div style={{ marginBottom: '20px' }}>
            {formData.courses.map((course, index) => (
            <div key={index} className="course-row">
                <div style={{ flex: 2 }}>
                    <input placeholder="Course Code" name="courseCode" value={course.courseCode} onChange={(e) => handleCourseChange(index, e)} required />
                </div>
                <div style={{ width: '80px' }}>
                    <input placeholder="Unit" name="unit" type="number" value={course.unit} onChange={(e) => handleCourseChange(index, e)} min="1" max="10" />
                </div>
                <div style={{ flex: 1 }}>
                    <input placeholder="Score" name="score" type="number" value={course.score} onChange={(e) => handleCourseChange(index, e)} required 
                           style={{ borderColor: course.scoreError ? 'var(--danger)' : '' }} />
                </div>
                <div style={{ width: '60px', textAlign: 'center', fontWeight: 'bold' }}>
                    {getGradePoint(course.score).grade}
                </div>
                <button type="button" className="danger-btn" onClick={() => removeCourse(index)} style={{ height: '40px', width: '40px', padding: 0 }}>×</button>
            </div>
            ))}
        </div>
        
        <div style={{ display: 'flex', gap: '15px' }}>
            <button type="button" className="secondary-btn" onClick={addCourse}>+ Add Course</button>
            <button type="submit" className="primary-btn" style={{ flex: 1 }}>Submit Result</button>
        </div>
      </form>

      {/* STUDENTS LIST TABLE */}
      <div>
        <h3 style={{ marginBottom: '15px' }}>📂 Student Records</h3>
        <div className="table-container" style={{ minHeight: '300px' }}> {/* MinHeight helps dropdown visibility */}
            <table>
                <thead>
                    <tr>
                        <th>Matric No</th>
                        <th>Name</th>
                        <th>CGPA</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {students.map((student) => (
                        <tr key={student.matricNumber}>
                            <td style={{ fontWeight: 'bold' }}>{student.matricNumber}</td>
                            <td>{student.name}</td>
                            <td style={{ color: 'var(--success)', fontWeight: 'bold' }}>{student.cgpa}</td>
                            <td style={{ textAlign: 'center' }}>
                                {/* THE THREE DOTS MENU */}
                                <div className="action-menu">
                                    <button className="menu-btn" onClick={(e) => toggleMenu(e, student.matricNumber)}>⋮</button>
                                    
                                    {activeDropdown === student.matricNumber && (
                                        <div className="dropdown-content">
                                            <div className="dropdown-item" onClick={() => handleEditStudent(student.matricNumber)}>
                                                ✏️ Edit Result
                                            </div>
                                            <div className="dropdown-item" onClick={() => handleViewHistory(student.matricNumber)}>
                                                📜 View History
                                            </div>
                                            <div className="dropdown-item delete" onClick={() => handleDeleteStudent(student.matricNumber)}>
                                                🗑️ Delete
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
      </div>

      {/* SYSTEM LOGS */}
      <div style={{ marginTop: '40px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
            <h3>🔒 System Audit Logs</h3>
            <button onClick={clearAllLogs} className="secondary-btn" style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}>Clear Logs</button>
        </div>
        <div className="table-container" style={{ maxHeight: '300px', overflowY: 'auto' }}>
            <table>
                <thead><tr><th>Action</th><th>Details</th><th>Timestamp</th></tr></thead>
                <tbody>
                    {logs.map((log, i) => (
                        <tr key={i}>
                            <td style={{ fontWeight: 'bold', color: 'var(--primary-color)' }}>{log.action}</td>
                            <td>{log.details}</td>
                            <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{new Date(log.timestamp).toLocaleString()}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
      </div>

      {/* HISTORY MODAL POPUP */}
      {showHistory && (
          <div className="modal-overlay">
              <div className="modal-content">
                  <h3>📜 Grade History: {selectedStudent}</h3>
                  <div className="table-container" style={{maxHeight: '300px', overflowY: 'auto'}}>
                    <table>
                        <thead><tr><th>Time</th><th>Action</th><th>Semester Count</th></tr></thead>
                        <tbody>
                            {historyData.map((h, i) => (
                                <tr key={i}>
                                    <td>{h.timestamp}</td>
                                    <td>{h.action}</td>
                                    <td>{h.total_semesters}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                  </div>
                  <button className="primary-btn" onClick={() => setShowHistory(false)} style={{marginTop: '20px', width: '100%'}}>Close</button>
              </div>
          </div>
      )}
    </div>
  );
}
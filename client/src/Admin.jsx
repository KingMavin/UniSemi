import React, { useState, useEffect } from 'react';
import authFetch from './utils/authFetch';
import './App.css';

export default function Admin() {
  const [formData, setFormData] = useState({
    matricNumber: '',
    name: '',
    department: '',
    level: '',
    semester: 'First',
    yearOfAdmission: new Date().getFullYear(),
    courses: [{ courseCode: '', score: '', grade: '', unit: '3', scoreError: false }]
  });

  const [message, setMessage] = useState('');
  const [logs, setLogs] = useState([]);      
  const [students, setStudents] = useState([]); 
  const [stats, setStats] = useState({ total: 0, avgCGPA: '0.00', highestCGPA: '0.00' });

  // --- API CALLS ---
  const fetchLogs = async () => {
    try { 
        const response = await authFetch('/api/logs'); 
        const logsData = response.data || response; 
        setLogs(Array.isArray(logsData) ? logsData : []); 
    } catch (err) { console.error(err); }
  };

  const fetchStudents = async () => {
    try {
      const response = await authFetch('/api/students');
      const studentsData = response.data || response;
      const studentsList = Array.isArray(studentsData) ? studentsData : [];
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

  useEffect(() => { fetchLogs(); fetchStudents(); }, []);

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
      ? value.toUpperCase() 
      : value; 
    setFormData({ ...formData, [name]: uppercasedValue });
  };

  const handleCourseChange = (index, e) => {
    const { name, value } = e.target;
    const newCourses = [...formData.courses];
    
    if (name === 'score') {
        const numericValue = value === '' ? '' : parseInt(value);
        if (numericValue !== '' && numericValue > 100) {
            newCourses[index][name] = 100;
            newCourses[index].scoreError = true;
        } else {
            newCourses[index][name] = value === '' ? '' : numericValue;
            newCourses[index].scoreError = false;
        }
    } else if (name === 'courseCode') {
        newCourses[index][name] = value.toUpperCase();
    } else if (name === 'unit') {
        newCourses[index][name] = value === '' ? '' : parseInt(value) || 0;
    } else {
        newCourses[index][name] = value;
    }
    
    setFormData({ ...formData, courses: newCourses });
  };

  const addCourse = () => setFormData({ ...formData, courses: [...formData.courses, { courseCode: '', score: '', grade: '', unit: '3', scoreError: false }] });

  const removeCourse = (index) => {
    if (formData.courses.length === 1) {
        alert("You must have at least one course.");
        return;
    }
    const newCourses = formData.courses.filter((_, i) => i !== index);
    setFormData({ ...formData, courses: newCourses });
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

  const handleDeleteStudent = async (id, matric) => {
    if(!window.confirm(`Delete ${matric}?`)) return;
    try { 
        await authFetch(`/api/results/${id}`, { method: 'DELETE' }); 
        fetchStudents(); fetchLogs(); 
    } catch (err) { setMessage(`❌ Failed to delete student: ${err.message || 'Unknown error'}`); }
  };

  const clearAllLogs = async () => {
    const password = prompt("Enter Admin Passcode to confirm clear:");
    const storedPasscode = localStorage.getItem('admin_passcode');
    if (!password || password !== storedPasscode) return alert("Wrong Passcode");
    try {
      await authFetch('/api/logs', { method: 'DELETE' });
      fetchLogs(); setMessage('✅ Logs cleared successfully');
    } catch (err) { setMessage(`❌ Failed to clear logs: ${err.message || 'Unknown error'}`); }
  };

  return (
    <div className="result-card">
      <h2 style={{ color: 'var(--primary-color)', marginBottom: '20px' }}>⚙️ Admin Dashboard</h2>
      
      {/* ANALYTICS */}
      <div className="stats-grid">
        <div className="stats-card">
            <h3>{stats.total}</h3>
            <span>Total Students</span>
        </div>
        <div className="stats-card">
            <h3>{stats.avgCGPA}</h3>
            <span>Average CGPA</span>
        </div>
        <div className="stats-card">
            <h3>{stats.highestCGPA}</h3>
            <span>Highest CGPA</span>
        </div>
      </div>

      {message && <div className={message.includes('✅') ? 'message-success' : 'message-error'}>{message}</div>}
      
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
                    <option value="100">100 Level</option>
                    <option value="200">200 Level</option>
                    <option value="300">300 Level</option>
                    <option value="400">400 Level</option>
                    <option value="500">500 Level</option>
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
                    <label style={{fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)'}}>Course Code</label>
                    <input name="courseCode" value={course.courseCode} onChange={(e) => handleCourseChange(index, e)} required />
                </div>
                <div style={{ width: '80px' }}>
                    <label style={{fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)'}}>Unit</label>
                    <input name="unit" type="number" value={course.unit} onChange={(e) => handleCourseChange(index, e)} min="1" max="10" />
                </div>
                <div style={{ flex: 1 }}>
                    <label style={{fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)'}}>Score (0-100)</label>
                    <input name="score" type="number" value={course.score} onChange={(e) => handleCourseChange(index, e)} required 
                           style={{ borderColor: course.scoreError ? 'var(--danger)' : '' }} />
                </div>
                <div style={{ width: '60px', textAlign: 'center' }}>
                    <label style={{fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)'}}>Grade</label>
                    <div style={{ fontSize: '1.2rem', fontWeight: 'bold', padding: '10px 0' }}>{getGradePoint(course.score).grade}</div>
                </div>
                
                <button type="button" className="danger-btn" onClick={() => removeCourse(index)} style={{ height: '40px', width: '40px', padding: 0 }}>
                  ×
                </button>
            </div>
            ))}
        </div>
        
        <div style={{ display: 'flex', gap: '15px' }}>
            <button type="button" className="secondary-btn" onClick={addCourse} style={{ color: 'var(--primary-color)', borderColor: 'var(--primary-color)' }}>
              + Add Another Course
            </button>
            <button type="submit" className="primary-btn" style={{ flex: 1 }}>
              Submit Result
            </button>
        </div>
      </form>

      {/* STUDENTS LIST TABLE */}
      <div>
        <h3 style={{ marginBottom: '15px' }}>📂 Student Records</h3>
        <div className="table-container">
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
                        <tr key={student._id}>
                            <td style={{ fontWeight: 'bold' }}>{student.matricNumber}</td>
                            <td>{student.name}</td>
                            <td style={{ color: 'var(--success)', fontWeight: 'bold' }}>{student.cgpa}</td>
                            <td>
                                <button className="danger-btn" onClick={() => handleDeleteStudent(student._id, student.matricNumber)} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
                                  Delete
                                </button>
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
                <thead>
                    <tr>
                        <th>Action</th>
                        <th>Details</th>
                        <th>Timestamp</th>
                    </tr>
                </thead>
                <tbody>
                    {logs.map((log) => (
                        <tr key={log._id}>
                            <td style={{ fontWeight: 'bold', color: 'var(--primary-color)' }}>{log.action}</td>
                            <td>{log.details}</td>
                            <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                                {new Date(log.timestamp).toLocaleString()}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
      </div>
    </div>
  );
}
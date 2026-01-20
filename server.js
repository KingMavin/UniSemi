// TOP OF FILE: Load Environment Variables
require('dotenv').config();

const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const path = require('path');

const app = express();

// --- 1. MIDDLEWARE (Run this first) ---
const CLIENT_ORIGIN = process.env.CLIENT_ORIGIN || 'http://localhost:5173';
app.use(express.json({ limit: '100kb' }));
app.use(cors({ origin: CLIENT_ORIGIN }));

// --- 2. SERVE STATIC REACT FILES (Performance Boost) ---
// Serve images/css instantly
app.use(express.static(path.join(__dirname, 'client/dist')));

// --- 3. DATABASE CONNECTION ---
const MONGO_URI = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/uni_records_v2';
const PORT = process.env.PORT || 5000;
const ADMIN_PASSCODE = process.env.ADMIN_PASSCODE || 'admin123';

mongoose.connect(MONGO_URI)
  .then(() => console.log('✅ Database Connected'))
  .catch(err => console.error('❌ Database Error:', err));

// --- 4. IMPORT MODELS & UTILS ---
const Student = require('./models/Student');
const SystemLog = require('./models/SystemLog');
const { computeSemesterStats } = require('./utils/grades');

// --- HELPER FUNCTIONS ---
function sendResponse(res, { success = true, data = null, error = null, status = 200 } = {}) {
  return res.status(status).json({ success, data, error });
}

function validateResultPayload(body) {
  const errors = [];
  if (!body.matricNumber || typeof body.matricNumber !== 'string') errors.push('matricNumber is required');
  if (!body.semester || typeof body.semester !== 'string') errors.push('semester is required');
  if (!Array.isArray(body.courses) || body.courses.length === 0) errors.push('courses is required');
  return errors;
}

// --- AUTH MIDDLEWARE (Must be before protected routes) ---
function authenticateToken(req, res, next) {
  const auth = req.headers && req.headers.authorization;
  if (!auth) return sendResponse(res, { success: false, error: 'Missing Authorization header', status: 401 });
  
  const parts = auth.split(' ');
  const credential = parts.length === 2 ? parts[1] : null;

  if (credential === ADMIN_PASSCODE) {
    req.user = { role: 'admin' };
    return next();
  }
  return sendResponse(res, { success: false, error: 'Invalid passcode', status: 401 });
}

// --- 5. API ROUTES (The "Brains") ---

// Login Route
app.post('/api/login', (req, res) => {
  const { passcode } = req.body || {};
  if (!passcode) return sendResponse(res, { success: false, error: 'Passcode required', status: 400 });
  if (passcode !== ADMIN_PASSCODE) return sendResponse(res, { success: false, error: 'Invalid passcode', status: 401 });
  return sendResponse(res, { success: true, data: { authenticated: true } });
});

// GET: Search Student (Public)
app.get('/api/results/:matricNumber', async (req, res) => {
    try {
        const student = await Student.findOne({ matricNumber: req.params.matricNumber });
        if (!student) return res.status(404).json({ message: 'Student not found' });
        
        // Normalize data for frontend
        const obj = student.toObject ? student.toObject() : student;
        if (Array.isArray(obj.academicHistory)) {
          obj.academicHistory = obj.academicHistory.map(h => {
            const courses = Array.isArray(h.courses) ? h.courses : [];
            const normCourses = courses.map(c => ({
              code: c.code || c.courseCode || '',
              unit: c.unit || 0,
              score: c.score || 0,
              grade: c.grade || ''
            }));
            return Object.assign({}, h, { courses: normCourses });
          });
        }
        return sendResponse(res, { success: true, data: obj });
    } catch (error) {
        res.status(500).json({ message: 'Server Error' });
    }
});

// GET: All Students (Protected)
app.get('/api/students', authenticateToken, async (req, res) => {
    try {
        const students = await Student.find({}, 'matricNumber surname othernames department cgpa');
        const formatted = students.map(s => {
            const obj = s.toObject ? s.toObject() : s;
            return {
                ...obj,
                name: [obj.surname, obj.othernames].filter(Boolean).join(' ') || obj.matricNumber
            };
        });
        return sendResponse(res, { success: true, data: formatted });
    } catch (error) {
        return sendResponse(res, { success: false, error: error.message, status: 500 });
    }
});

// POST: Upload/Update Result (Protected)
app.post('/api/results', authenticateToken, async (req, res) => {
  const payload = req.body || {};
  const errors = validateResultPayload(payload);
  if (errors.length) return sendResponse(res, { success: false, error: errors, status: 400 });

  const semesterId = payload.semester;
  const matric = payload.matricNumber.trim();

  try {
    const stats = computeSemesterStats(payload.courses);
    const coursesArr = (stats.processedCourses || []).map(c => ({ 
        code: c.courseCode || c.code, 
        unit: c.unit, 
        score: c.score, 
        grade: c.grade 
    }));

    const semesterRecord = {
      semester: semesterId,
      semesterUnits: stats.semesterUnits,
      semesterPoints: stats.semesterPoints,
      semesterGPA: stats.semesterGPA,
      courses: coursesArr
    };

    let student = await Student.findOne({ matricNumber: matric });

    if (!student) {
      // Create New
      let surname = payload.surname || '';
      let othernames = payload.othernames || '';
      if (payload.name && !payload.surname) {
        const nameParts = payload.name.trim().split(/\s+/);
        surname = nameParts[0] || '';
        othernames = nameParts.slice(1).join(' ') || '';
      }

      student = new Student({
        matricNumber: matric,
        surname: surname,
        othernames: othernames,
        department: payload.department,
        level: payload.level,
        yearOfAdmission: payload.yearOfAdmission ? Number(payload.yearOfAdmission) : new Date().getFullYear(),
        academicHistory: [semesterRecord],
        cgpa: stats.semesterGPA
      });
      await student.save();
      try { await SystemLog.create({ action: 'NEW_STUDENT', details: `Created ${matric}` }); } catch (e) {}
      return sendResponse(res, { success: true, data: student, status: 201 });
    }

    // Update Existing
    const idx = (student.academicHistory || []).findIndex(s => s.semester === semesterId);
    if (idx >= 0) {
      student.academicHistory[idx] = semesterRecord;
    } else {
      student.academicHistory.push(semesterRecord);
    }

    // Recalculate CGPA
    let totalUnits = 0;
    let totalPoints = 0;
    (student.academicHistory || []).forEach(h => {
      totalUnits += Number(h.semesterUnits || 0);
      totalPoints += Number(h.semesterPoints || 0);
    });
    student.cgpa = totalUnits > 0 ? +(totalPoints / totalUnits).toFixed(2) : 0;

    // Update meta
    if (payload.department) student.department = payload.department;
    if (payload.level) student.level = payload.level;
    
    await student.save();
    try { await SystemLog.create({ action: 'UPDATE_STUDENT', details: `Updated ${matric} - ${semesterId}` }); } catch (e) {}
    return sendResponse(res, { success: true, data: student, status: 200 });

  } catch (err) {
    console.error('POST /api/results error', err);
    return sendResponse(res, { success: false, error: err.message, status: 500 });
  }
});

// DELETE: Student (Protected)
app.delete('/api/results/:id', authenticateToken, async (req, res) => {
  const { id } = req.params;
  if (!mongoose.Types.ObjectId.isValid(id)) return sendResponse(res, { success: false, error: 'Invalid id', status: 400 });

  try {
    const removed = await Student.findByIdAndDelete(id);
    if (!removed) return sendResponse(res, { success: false, error: 'Student not found', status: 404 });
    try { await SystemLog.create({ action: 'DELETE_STUDENT', details: `Deleted ${removed.matricNumber}` }); } catch (e) {}
    return sendResponse(res, { success: true, data: removed });
  } catch (err) {
    return sendResponse(res, { success: false, error: err.message, status: 500 });
  }
});

// GET: Logs (Protected)
app.get('/api/logs', authenticateToken, async (req, res) => {
    try {
        const logs = await SystemLog.find().sort({ timestamp: -1 }).limit(20);
        return sendResponse(res, { success: true, data: logs });
    } catch (err) {
        return sendResponse(res, { success: false, error: err.message, status: 500 });
    }
});

// DELETE: Logs (Protected)
app.delete('/api/logs', authenticateToken, async (req, res) => {
    try {
        await SystemLog.deleteMany({});
        await SystemLog.create({ action: "SYSTEM_RESET", details: "Admin cleared history" });
        res.json({ message: 'Cleared' });
    } catch (err) {
        return sendResponse(res, { success: false, error: err.message, status: 500 });
    }
});


// --- 6. REACT FALLBACK ROUTE (The "Safety Net") ---
// Using Regex to fix Express 5 "Missing parameter" error
app.get(/(.*)/, (req, res) => {
  res.sendFile(path.join(__dirname, 'client/dist', 'index.html'));
});

// --- 7. START SERVER ---
if (require.main === module) {
    app.listen(PORT, () => console.log(`🚀 Server running on port ${PORT}`));
}

module.exports = app;
const mongoose = require('mongoose');

const studentSchema = new mongoose.Schema({
  matricNumber: { type: String, required: true, unique: true },
  surname: String,
  othernames: String,
  department: String,
  level: String,
  yearOfAdmission: Number,
  cgpa: Number,
  academicHistory: [
    {
      semester: String,
      semesterUnits: Number,
      semesterPoints: Number,
      semesterGPA: Number,
      courses: [
        {
          code: String,
          unit: Number,
          score: Number,
          grade: String
        }
      ]
    }
  ]
}, { timestamps: true });

module.exports = mongoose.model('Student', studentSchema);
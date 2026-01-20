require('dotenv').config();
const mongoose = require('mongoose');
const Student = require('./models/Student');

const MONGO = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/uni_records_v2';

async function seed() {
  try {
    await mongoose.connect(MONGO);
    console.log('Connected to', MONGO);

    await Student.deleteMany({ matricNumber: /^(SEED|U)/ });

    const sample = {
      matricNumber: 'SEED001',
      surname: 'Doe',
      othernames: 'Jane',
      department: 'Computer Science',
      level: '300',
      yearOfAdmission: 2021,
      academicHistory: [
        {
          semester: '2023-1',
          semesterUnits: 15,
          semesterPoints: 45,
          semesterGPA: 3.0,
          courses: [
            { code: 'CSC301', unit: 3, score: 72, grade: 'A' },
            { code: 'CSC302', unit: 3, score: 65, grade: 'B' },
            { code: 'MAT301', unit: 3, score: 58, grade: 'C' },
            { code: 'GST301', unit: 2, score: 70, grade: 'A' },
            { code: 'PHY301', unit: 4, score: 60, grade: 'B' }
          ]
        }
      ],
      cgpa: 3.0
    };

    await Student.create(sample);
    console.log('Seed complete: inserted sample student SEED001');
  } catch (err) {
    console.error('Seed error:', err);
  } finally {
    await mongoose.disconnect();
    process.exit(0);
  }
}

seed();
const { computeSemesterStats } = require('../utils/grades');
const assert = require('assert');

function almostEqual(a, b, eps = 1e-6) {
  return Math.abs(a - b) < eps;
}

// Simple scenario: two courses, 3 units each, scores 75(A) and 65(B)
// Points: 3*5 + 3*4 = 15 + 12 = 27; units = 6 => GPA = 4.5
const courses = [
  { courseCode: 'CSC401', unit: 3, score: 75 },
  { courseCode: 'CSC402', unit: 3, score: 65 }
];

const res = computeSemesterStats(courses);
assert.strictEqual(res.semesterUnits, 6);
assert.strictEqual(res.semesterPoints, 27);
if (!almostEqual(res.semesterGPA, 4.5)) throw new Error(`Expected GPA 4.5, got ${res.semesterGPA}`);

console.log('grades.test.js: OK');
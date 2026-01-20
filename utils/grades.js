function scoreToGrade(score) {
  if (score >= 70) return 'A';
  if (score >= 60) return 'B';
  if (score >= 50) return 'C';
  if (score >= 45) return 'D';
  return 'F';
}
function gradePointFromGrade(g) {
  switch (g) {
    case 'A': return 5;
    case 'B': return 4;
    case 'C': return 3;
    case 'D': return 2;
    default: return 0;
  }
}

/**
 * computeSemesterStats(courses)
 * - courses: [{ courseCode, unit, score, grade? }]
 * returns { semesterUnits, semesterPoints, semesterGPA, processedCourses }
 */
function computeSemesterStats(courses = []) {
  let semesterUnits = 0;
  let semesterPoints = 0;
  const processed = (courses || []).map(c => {
    const unit = Number(c.unit) || 0;
    const score = Number(c.score) || 0;
    const grade = (c.grade && String(c.grade)) || scoreToGrade(score);
    const gp = gradePointFromGrade(grade);
    semesterUnits += unit;
    semesterPoints += unit * gp;
    return {
      courseCode: c.courseCode || c.code || c.course,
      unit,
      score,
      grade
    };
  });
  const semesterGPA = semesterUnits > 0 ? +(semesterPoints / semesterUnits) : 0;
  return { semesterUnits, semesterPoints, semesterGPA, processedCourses: processed };
}

module.exports = { computeSemesterStats, scoreToGrade, gradePointFromGrade };
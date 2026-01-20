# University Records System — Comprehensive Documentation

## 📋 Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Project Structure](#project-structure)
4. [Detailed Component Documentation](#detailed-component-documentation)
5. [API Endpoints](#api-endpoints)
6. [Data Models](#data-models)
7. [Key Features & Workflows](#key-features--workflows)
8. [Installation & Setup](#installation--setup)
9. [Development Guide](#development-guide)
10. [Testing](#testing)

---

## Overview

**University Records System** is a full-stack MERN (MongoDB, Express, React, Node.js) web application designed for managing university student academic records. The system provides two main interfaces:

1. **Student Portal** (Public): Allows students to search and view their academic records by matriculation number
2. **Admin Dashboard** (Protected): Enables administrators to upload/update semester results, manage student records, and view system audit logs

### Core Functionality
- **Student Search**: Public access to view academic transcripts with CGPA and semester-by-semester breakdown
- **Result Management**: Admin can create new student records or update existing semester results
- **Automatic GPA Calculation**: Server-side computation of semester GPA and cumulative CGPA
- **Audit Logging**: System tracks all administrative actions (create, update, delete)
- **Session Management**: Admin sessions with automatic timeout after inactivity

---

## System Architecture

### Technology Stack
- **Frontend**: React 19, Vite (build tool), CSS3 with modern animations
- **Backend**: Express.js 5, Node.js
- **Database**: MongoDB with Mongoose ODM
- **Authentication**: Passcode-based (dev-level, not production-ready)

### Architecture Pattern
The application follows a **client-server architecture** with clear separation:
- **Client** (`client/`): React SPA that communicates with REST API
- **Server** (`server.js`): Express REST API that handles business logic and database operations
- **Shared Utilities**: Grade calculation logic is centralized in `utils/grades.js`

### Data Flow
```
User Input → React Component → authFetch → Express API → Mongoose Model → MongoDB
                                                              ↓
User Interface ← React State ← JSON Response ← Business Logic ← Database Query
```

---

## Project Structure

```
UniversityRecordsSystem/
├── client/                          # React frontend application
│   ├── src/
│   │   ├── App.jsx                  # Main application component (Student Portal + Login)
│   │   ├── Admin.jsx                # Admin dashboard component
│   │   ├── ErrorBoundary.jsx        # React error boundary for error handling
│   │   ├── main.jsx                 # Application entry point
│   │   ├── App.css                  # Main stylesheet with animations
│   │   ├── index.css                # Global styles
│   │   └── utils/
│   │       └── authFetch.js         # HTTP client with authentication
│   ├── vite.config.js               # Vite configuration (proxy setup)
│   └── package.json                 # Frontend dependencies
│
├── models/                          # Mongoose data models
│   ├── Student.js                   # Student schema definition
│   └── SystemLog.js                 # Audit log schema
│
├── utils/                           # Shared utility functions
│   └── grades.js                    # Grade calculation logic
│
├── tests/                           # Test files
│   ├── grades.test.js               # Unit tests for grade calculations
│   └── integration.test.js         # (Placeholder for integration tests)
│
├── server.js                        # Express server & API routes
├── seed.js                          # Database seeding script
├── package.json                     # Server dependencies & scripts
└── README.md                        # This file
```

---

## Detailed Component Documentation

### Frontend Components

#### `client/src/App.jsx` — Main Application Component

**Purpose**: Root component that manages application state, routing between Student Portal and Admin Dashboard, and handles authentication.

**Key State Variables**:
- `view`: Controls which view is displayed ('student', 'admin', 'login')
- `isAuthenticated`: Tracks admin authentication status
- `serverConnected`: Monitors backend server connectivity
- `matricNumber`: Input for student search
- `studentData`: Fetched student record data

**Important Functions**:

1. **`Login` Component** (Lines 17-45)
   - Handles admin authentication
   - Sends passcode to `/api/login` endpoint
   - On success, calls `onLogin` callback to establish session
   - Displays error messages for failed login attempts

2. **`handleLoginSuccess(passcode)`** (Lines 68-74)
   - Stores passcode in localStorage
   - Sets session expiry timestamp (9 minutes from login)
   - Updates authentication state and switches to admin view
   - **Session Management**: Uses `SESSION_TIMEOUT` constant (9 minutes)

3. **`handleLogout()`** (Lines 60-66)
   - Clears localStorage (passcode and session expiry)
   - Resets authentication state
   - Returns user to student portal view

4. **Session Management Logic** (Lines 84-119)
   - **`checkSession()`**: Validates if session is still active by comparing current time with stored expiry
   - **`updateActivity()`**: Resets session timer on user interaction (click/keypress)
   - Runs every 60 seconds to auto-logout expired sessions
   - Listens for user activity to extend session

5. **`handleSearch()`** (Lines 122-130)
   - Fetches student record by matric number
   - Calls `GET /api/results/:matricNumber`
   - Updates UI with student data or error message

6. **Server Connectivity Check** (Lines 132-143)
   - Periodically pings `/api/results/SEED001` every 10 seconds
   - Updates `serverConnected` state to show online/offline status
   - Displays connection indicator in header

**Helper Functions**:
- `getStudentName(s)`: Extracts student name from various possible formats (name, surname+othernames, matricNumber)
- `getSemesterGPA(sem)`: Gets GPA from semester object (handles different property names for compatibility)

---

#### `client/src/Admin.jsx` — Admin Dashboard Component

**Purpose**: Comprehensive admin interface for managing student records, uploading results, and viewing system logs.

**Key State Variables**:
- `formData`: Form state for uploading/updating results
  - Contains: matricNumber, name, department, level, semester, yearOfAdmission, courses array
- `message`: Success/error feedback messages
- `logs`: System audit logs array
- `students`: List of all students
- `stats`: Calculated statistics (total students, average CGPA, highest CGPA)

**Important Functions**:

1. **`getGradePoint(score)`** (Lines 52-60)
   - Converts numeric score to letter grade and grade point
   - **Grading Scale**:
     - 70-100: A (5 points)
     - 60-69: B (4 points)
     - 50-59: C (3 points)
     - 45-49: D (2 points)
     - 0-44: F (0 points)
   - Returns `{ grade, point }` object
   - Used for real-time grade display in form

2. **`handleChange(e)`** (Lines 62-68)
   - Handles input changes for main form fields
   - Auto-uppercases: matricNumber, department, level
   - Updates formData state

3. **`handleCourseChange(index, e)`** (Lines 70-92)
   - Handles changes to course fields (courseCode, unit, score)
   - **Score Validation**:
     - Parses input to integer
     - Caps maximum at 100
     - Sets `scoreError` flag for invalid input (though currently has a bug - see notes)
   - **Course Code**: Auto-uppercases
   - **Unit**: Parses to integer, defaults to 0 if empty

4. **`addCourse()`** (Line 94)
   - Adds new course row to form
   - Initializes with default values: courseCode='', score='', grade='', unit='3', scoreError=false

5. **`removeCourse(index)`** (Lines 96-103)
   - Removes course at specified index
   - Prevents removal if only one course remains (validation)

6. **`handleSubmit(e)`** (Lines 105-117)
   - Submits form data to `POST /api/results`
   - On success: shows success message, refreshes logs/students, resets form
   - On error: displays error message

7. **`fetchLogs()`** (Lines 22-28)
   - Fetches system audit logs from `GET /api/logs`
   - Handles both `{ data: [...] }` and direct array responses

8. **`fetchStudents()`** (Lines 30-38)
   - Fetches all students from `GET /api/students`
   - Calls `calculateStats()` to update statistics

9. **`calculateStats(list)`** (Lines 40-47)
   - Calculates aggregate statistics from student list
   - Computes: total count, average CGPA, highest CGPA
   - Updates `stats` state

10. **`handleDeleteStudent(id, matric)`** (Lines 119-125)
    - Deletes student record via `DELETE /api/results/:id`
    - Requires confirmation dialog
    - Refreshes student list and logs after deletion

11. **`clearAllLogs()`** (Lines 127-135)
    - Clears all system logs via `DELETE /api/logs`
    - Requires passcode confirmation
    - Compares with stored passcode from localStorage

**Form Structure**:
- **Student Information**: Matric Number, Name, Department, Level, Semester, Year of Admission
- **Courses Section**: Dynamic list of courses with Course Code, Unit, Score, Auto-calculated Grade
- **Actions**: Add Course, Remove Course, Submit Result

**Display Sections**:
1. **Analytics Dashboard**: Shows total students, average CGPA, highest CGPA
2. **Upload/Update Form**: Form for creating or updating student results
3. **Student Records Table**: Lists all students with matric number, name, CGPA, delete action
4. **System Audit Logs**: Shows recent administrative actions with timestamps

---

#### `client/src/utils/authFetch.js` — Authentication HTTP Client

**Purpose**: Wrapper around `fetch` API that automatically includes authentication headers and handles errors consistently.

**Key Features**:

1. **Automatic Authentication** (Lines 2-9)
   - Retrieves `admin_passcode` from localStorage
   - Adds `Authorization: Passcode <passcode>` header if passcode exists
   - Merges with custom headers from options

2. **Timeout Support** (Lines 11-13, 36-44)
   - Uses `AbortController` for request cancellation
   - Supports `opts.timeout` parameter (milliseconds)
   - Throws timeout error if request exceeds timeout

3. **Error Handling** (Lines 24-31)
   - Parses JSON response even on HTTP errors
   - Extracts error message from `json.error`, `json.message`, or response text
   - Creates Error object with `status` and `response` properties (mimics axios structure)
   - Ensures consistent error format across the application

4. **Response Parsing** (Lines 19-21)
   - Safely parses JSON response
   - Returns empty object if response is empty or invalid JSON

**Usage Example**:
```javascript
// Public request (no auth)
const data = await authFetch('/api/results/SEED001');

// Protected request (auto-includes auth)
const students = await authFetch('/api/students');

// With timeout
const result = await authFetch('/api/results/SEED001', { timeout: 3000 });
```

---

#### `client/src/ErrorBoundary.jsx` — React Error Boundary

**Purpose**: Catches JavaScript errors in child components and displays a fallback UI instead of crashing the entire app.

**How It Works**:
- **`getDerivedStateFromError()`**: Updates state when error occurs
- **`componentDidCatch()`**: Can be used for error logging/telemetry (currently commented out)
- **Render**: Shows error message with "Go back" and "Reload" buttons

**Usage**: Wraps components that might throw errors (typically used in main.jsx to wrap entire app)

---

### Backend Components

#### `server.js` — Express Server & API Routes

**Purpose**: Main server file that sets up Express application, defines API routes, handles authentication, and manages database operations.

**Configuration** (Lines 1-23):
- Loads environment variables via `dotenv`
- Sets up CORS with configurable origin
- Configures JSON body parser (100kb limit)
- Serves static files from `client/dist` (for production builds)
- Connects to MongoDB using Mongoose

**Helper Functions**:

1. **`sendResponse(res, options)`** (Lines 35-37)
   - Standardized API response format
   - Always returns `{ success, data, error }` structure
   - Sets HTTP status code
   - Ensures consistent API responses across all endpoints

2. **`validateResultPayload(body)`** (Lines 39-45)
   - Validates POST /api/results request body
   - Checks required fields: matricNumber, semester, courses array
   - Returns array of error messages (empty if valid)

3. **`authenticateToken(req, res, next)`** (Lines 48-60)
   - **Authentication Middleware**: Protects admin routes
   - Extracts passcode from `Authorization: Passcode <passcode>` header
   - Compares with `ADMIN_PASSCODE` from environment
   - Sets `req.user = { role: 'admin' }` on success
   - Returns 401 error if authentication fails

**API Routes**:

1. **`POST /api/login`** (Lines 65-70)
   - **Public Endpoint**: Validates admin passcode
   - Request: `{ passcode: string }`
   - Response: `{ success: boolean, data: { authenticated: true }, error: null }`
   - Returns 401 if passcode is invalid

2. **`GET /api/results/:matricNumber`** (Lines 73-96)
   - **Public Endpoint**: Fetches student record by matric number
   - **Data Normalization**: Converts course data to consistent format
     - Handles both `courseCode`/`code` property names
     - Handles both `unit`/`units` property names
   - Returns 404 if student not found
   - Returns normalized student object with academicHistory array

3. **`GET /api/students`** (Lines 99-113)
   - **Protected Endpoint**: Requires authentication
   - Returns list of all students with basic info
   - **Data Formatting**: Combines `surname` and `othernames` into `name` field
   - Fields returned: matricNumber, name, department, cgpa

4. **`POST /api/results`** (Lines 116-197)
   - **Protected Endpoint**: Creates or updates student semester results
   - **Request Validation**: Calls `validateResultPayload()`
   - **Grade Calculation**: Uses `computeSemesterStats()` from `utils/grades.js`
   - **Business Logic**:
     - If student doesn't exist: Creates new student record
     - If student exists: Updates or adds semester to academicHistory
     - **CGPA Recalculation**: Recomputes cumulative GPA from all semesters
     - Formula: `CGPA = Total Points / Total Units` across all semesters
   - **Name Parsing**: Splits `name` field into `surname` and `othernames` if provided
   - **Logging**: Creates SystemLog entry for NEW_STUDENT or UPDATE_STUDENT actions
   - Returns created/updated student object

5. **`DELETE /api/results/:id`** (Lines 200-212)
   - **Protected Endpoint**: Deletes student by MongoDB `_id`
   - Validates ObjectId format
   - Creates SystemLog entry for DELETE_STUDENT action
   - Returns 404 if student not found

6. **`GET /api/logs`** (Lines 215-222)
   - **Protected Endpoint**: Returns system audit logs
   - Returns last 20 logs, sorted by timestamp (newest first)
   - Fields: action, details, timestamp

7. **`DELETE /api/logs`** (Lines 225-233)
   - **Protected Endpoint**: Clears all system logs
   - Creates a "SYSTEM_RESET" log entry after clearing

8. **`GET /*` (Fallback Route)** (Lines 238-240)
   - Serves React app for client-side routing
   - Only matches if no API route matched
   - Sends `index.html` from `client/dist`

**CGPA Calculation Logic** (Lines 176-183):
```javascript
// Iterates through all semesters in academicHistory
totalUnits = sum of all semesterUnits
totalPoints = sum of all semesterPoints
CGPA = totalPoints / totalUnits (rounded to 2 decimal places)
```

---

#### `models/Student.js` — Student Data Model

**Purpose**: Mongoose schema definition for Student documents in MongoDB.

**Schema Structure**:
```javascript
{
  matricNumber: String (required, unique),  // Primary identifier
  surname: String,
  othernames: String,
  department: String,
  level: String,                            // e.g., "100", "200", "300"
  yearOfAdmission: Number,
  cgpa: Number,                             // Cumulative GPA
  academicHistory: [                        // Array of semester records
    {
      semester: String,                     // e.g., "First", "Second", "2023-1"
      semesterUnits: Number,                 // Total units for semester
      semesterPoints: Number,                // Total points for semester
      semesterGPA: Number,                  // GPA for this semester
      courses: [                            // Array of course records
        {
          code: String,                     // Course code (e.g., "CSC301")
          unit: Number,                     // Credit units
          score: Number,                    // Numeric score (0-100)
          grade: String                     // Letter grade (A, B, C, D, F)
        }
      ]
    }
  ],
  timestamps: true                          // Auto-adds createdAt, updatedAt
}
```

**Key Features**:
- `matricNumber` is unique (enforced by MongoDB index)
- `academicHistory` is an array, allowing multiple semesters per student
- Each semester contains its own GPA and course list
- Timestamps automatically track creation and modification dates

---

#### `models/SystemLog.js` — Audit Log Model

**Purpose**: Tracks all administrative actions for audit purposes.

**Schema Structure**:
```javascript
{
  action: String (required),    // e.g., "NEW_STUDENT", "UPDATE_STUDENT", "DELETE_STUDENT"
  details: String,              // Additional information (e.g., matric number)
  timestamp: Date,              // Auto-set to current date/time
  timestamps: true              // Also adds createdAt, updatedAt
}
```

**Usage**: Created automatically by server when:
- New student is created
- Student record is updated
- Student is deleted
- Logs are cleared

---

#### `utils/grades.js` — Grade Calculation Utilities

**Purpose**: Centralized logic for converting scores to grades and calculating GPA.

**Functions**:

1. **`scoreToGrade(score)`** (Lines 1-7)
   - Converts numeric score (0-100) to letter grade
   - Returns: 'A' (70+), 'B' (60-69), 'C' (50-59), 'D' (45-49), 'F' (<45)

2. **`gradePointFromGrade(grade)`** (Lines 8-16)
   - Converts letter grade to grade points
   - Returns: A=5, B=4, C=3, D=2, F=0

3. **`computeSemesterStats(courses)`** (Lines 23-42)
   - **Main Function**: Calculates semester-level statistics
   - **Input**: Array of course objects `[{ courseCode, unit, score, grade? }]`
   - **Process**:
     1. For each course: extracts unit and score
     2. Determines grade (uses provided grade or calculates from score)
     3. Calculates grade point from grade
     4. Accumulates: `semesterUnits += unit`, `semesterPoints += unit * gradePoint`
   - **Output**: 
     ```javascript
     {
       semesterUnits: Number,        // Total credit units
       semesterPoints: Number,        // Total grade points
       semesterGPA: Number,          // Points / Units (rounded)
       processedCourses: Array        // Normalized course objects
     }
     ```
   - **GPA Formula**: `semesterGPA = semesterPoints / semesterUnits`
   - Handles edge cases: empty arrays, missing values, zero units

**Why Centralized?**: 
- Used by both server (POST /api/results) and potentially client (real-time preview)
- Ensures consistent grade calculation across the application
- Easily testable (see `tests/grades.test.js`)

---

#### `seed.js` — Database Seeding Script

**Purpose**: Populates database with sample data for development and testing.

**Functionality**:
1. Connects to MongoDB using `MONGO_URI` from environment
2. Deletes existing seed data (matric numbers starting with "SEED" or "U")
3. Creates sample student "SEED001" with:
   - Name: Jane Doe
   - Department: Computer Science
   - Level: 300
   - One semester (2023-1) with 5 courses
   - Pre-calculated CGPA: 3.0

**Usage**:
```bash
cd UniversityRecordsSystem
npm run seed
```

**Sample Data Structure**: Demonstrates the expected format for student records, including nested academicHistory and courses arrays.

---

### Configuration Files

#### `client/vite.config.js` — Vite Configuration

**Purpose**: Configures Vite build tool and development server.

**Key Settings**:
- **React Plugin**: Enables JSX transformation
- **Proxy Configuration**: Routes `/api/*` requests to `http://localhost:5000`
  - Allows frontend to make API calls without CORS issues in development
  - Only active in development mode

---

## API Endpoints

### Public Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/api/results/:matricNumber` | Get student record | - | `{ success: true, data: Student }` |
| POST | `/api/login` | Authenticate admin | `{ passcode: string }` | `{ success: boolean, data: { authenticated: true } }` |

### Protected Endpoints (Require Authorization Header)

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/api/students` | List all students | - | `{ success: true, data: Student[] }` |
| POST | `/api/results` | Create/update result | `{ matricNumber, name, department, level, semester, courses[] }` | `{ success: true, data: Student }` |
| DELETE | `/api/results/:id` | Delete student | - | `{ success: true, data: Student }` |
| GET | `/api/logs` | Get audit logs | - | `{ success: true, data: Log[] }` |
| DELETE | `/api/logs` | Clear all logs | - | `{ message: 'Cleared' }` |

**Authorization**: All protected endpoints require header:
```
Authorization: Passcode <admin_passcode>
```

---

## Data Models

### Student Document Structure

```javascript
{
  _id: ObjectId,                    // MongoDB auto-generated
  matricNumber: "SEED001",          // Unique identifier
  surname: "Doe",
  othernames: "Jane",
  department: "Computer Science",
  level: "300",
  yearOfAdmission: 2021,
  cgpa: 3.0,                       // Calculated from all semesters
  academicHistory: [
    {
      semester: "2023-1",          // Semester identifier
      semesterUnits: 15,           // Total units this semester
      semesterPoints: 45,          // Total points this semester
      semesterGPA: 3.0,            // Points / Units
      courses: [
        {
          code: "CSC301",
          unit: 3,
          score: 72,
          grade: "A"
        }
        // ... more courses
      ]
    }
    // ... more semesters
  ],
  createdAt: Date,
  updatedAt: Date
}
```

### SystemLog Document Structure

```javascript
{
  _id: ObjectId,
  action: "NEW_STUDENT",           // Action type
  details: "Created SEED001",      // Additional info
  timestamp: Date,                 // When action occurred
  createdAt: Date,
  updatedAt: Date
}
```

---

## Key Features & Workflows

### 1. Student Search Workflow

**User Journey**:
1. User enters matric number in search field
2. Clicks "Check Result" or presses Enter
3. Frontend calls `GET /api/results/:matricNumber`
4. Server queries MongoDB for student
5. Server normalizes course data format
6. Response displayed in formatted card with:
   - Student information (name, matric, department)
   - Current CGPA (prominently displayed)
   - Semester-by-semester breakdown with courses table
   - Print button for transcript

**Error Handling**: Shows "Student not found" message if matric number doesn't exist

---

### 2. Admin Result Upload Workflow

**User Journey**:
1. Admin logs in with passcode
2. Fills out form:
   - Student information (matric, name, department, level, semester)
   - Adds courses (course code, unit, score)
   - Grade is auto-calculated and displayed
3. Clicks "Submit Result"
4. Frontend sends `POST /api/results` with form data
5. Server validates payload
6. Server calculates semester stats using `computeSemesterStats()`
7. Server checks if student exists:
   - **New Student**: Creates new document with first semester
   - **Existing Student**: 
     - If semester exists: Replaces it
     - If new semester: Adds to academicHistory array
8. Server recalculates CGPA from all semesters
9. Server creates SystemLog entry
10. Response updates UI, refreshes student list and logs

**Real-time Features**:
- Grade updates automatically as score is entered
- Score validation (max 100, numeric only)
- Dynamic course addition/removal

---

### 3. Session Management

**How It Works**:
1. On login: Stores passcode and expiry timestamp (current time + 9 minutes)
2. Activity monitoring: Resets expiry on any click or keypress
3. Periodic check: Every 60 seconds, validates if session expired
4. Auto-logout: If expired, clears localStorage and returns to student portal

**Session Timeout**: 9 minutes of inactivity (configurable via `SESSION_TIMEOUT` constant)

---

### 4. CGPA Calculation

**Formula**:
```
CGPA = (Sum of all semesterPoints) / (Sum of all semesterUnits)
```

**Process**:
1. When semester is uploaded/updated, server calculates:
   - `semesterPoints = sum(unit × gradePoint)` for all courses
   - `semesterGPA = semesterPoints / semesterUnits`
2. When student record is updated, server recalculates CGPA:
   - Iterates through all semesters in `academicHistory`
   - Sums all `semesterPoints` and `semesterUnits`
   - Divides to get cumulative GPA
   - Rounds to 2 decimal places

**Example**:
- Semester 1: 15 units, 60 points → GPA 4.0
- Semester 2: 12 units, 48 points → GPA 4.0
- CGPA = (60 + 48) / (15 + 12) = 108 / 27 = 4.0

---

## Installation & Setup

### Prerequisites
- Node.js (v14 or higher)
- MongoDB (running locally or remote instance)
- npm or yarn

### Step-by-Step Setup

1. **Clone/Navigate to Project**
   ```bash
   cd UniversityRecordsSystem
   ```

2. **Install Server Dependencies**
   ```bash
   npm install
   ```

3. **Configure Environment Variables**
   - Create `.env` file in root directory (or copy from `.env.example` if exists)
   - Set required variables:
     ```
     PORT=5000
     MONGO_URI=mongodb://127.0.0.1:27017/uni_records_v2
     ADMIN_PASSCODE=admin123
     CLIENT_ORIGIN=http://localhost:5173
     ```

4. **Start MongoDB**
   - Ensure MongoDB is running on your system
   - Default connection: `mongodb://127.0.0.1:27017`

5. **Seed Database (Optional)**
   ```bash
   npm run seed
   ```
   This creates sample student "SEED001" for testing

6. **Start Server**
   ```bash
   npm start
   ```
   Server runs on http://localhost:5000

7. **Install Client Dependencies** (in new terminal)
   ```bash
   cd client
   npm install
   ```

8. **Start Client Development Server**
   ```bash
   npm run dev
   ```
   Client runs on http://localhost:5173

9. **Access Application**
   - Open browser to http://localhost:5173
   - Student Portal: Search for "SEED001" to test
   - Admin Dashboard: Click "Admin Dashboard", login with passcode from `.env`

---

## Development Guide

### Adding New Features

#### Adding a New API Endpoint

1. **Define Route in `server.js`**:
   ```javascript
   app.get('/api/new-endpoint', authenticateToken, async (req, res) => {
     try {
       // Your logic here
       return sendResponse(res, { success: true, data: result });
     } catch (err) {
       return sendResponse(res, { success: false, error: err.message, status: 500 });
     }
   });
   ```

2. **Call from Frontend**:
   ```javascript
   const data = await authFetch('/api/new-endpoint');
   ```

#### Adding a New Form Field

1. **Update `formData` state** in `Admin.jsx`:
   ```javascript
   const [formData, setFormData] = useState({
     // ... existing fields
     newField: ''
   });
   ```

2. **Add Input Element**:
   ```javascript
   <input 
     name="newField" 
     value={formData.newField} 
     onChange={handleChange} 
   />
   ```

3. **Update Server Schema** (if needed):
   - Modify `models/Student.js` to include new field
   - Update POST /api/results handler to process new field

### Code Style Guidelines

- **Naming Conventions**:
  - Components: PascalCase (e.g., `Admin.jsx`)
  - Functions: camelCase (e.g., `handleSubmit`)
  - Constants: UPPER_SNAKE_CASE (e.g., `SESSION_TIMEOUT`)
  - Files: Match component/function name

- **Error Handling**:
  - Always use try-catch for async operations
  - Display user-friendly error messages
  - Log errors to console for debugging

- **State Management**:
  - Use React hooks (useState, useEffect)
  - Keep state as local as possible
  - Lift state up only when necessary

### Debugging Tips

1. **Check Browser Console**: React errors and API call logs
2. **Check Server Logs**: Database connection, API requests, errors
3. **Network Tab**: Inspect API requests/responses
4. **MongoDB Compass**: Visual database inspection
5. **React DevTools**: Component state inspection

### Common Issues & Solutions

**Issue**: "Cannot connect to server"
- **Solution**: Ensure server is running on port 5000, check MongoDB connection

**Issue**: "Student not found" when searching
- **Solution**: Run `npm run seed` to create sample data, or check matric number spelling

**Issue**: "Invalid passcode" on admin login
- **Solution**: Check `.env` file has correct `ADMIN_PASSCODE`, restart server after changing .env

**Issue**: CORS errors
- **Solution**: Check `CLIENT_ORIGIN` in `.env` matches your client URL

---

## Testing

### Running Tests

**Unit Tests** (Grade Calculations):
```bash
npm test
# or
node tests/grades.test.js
```

**Expected Output**: `grades.test.js: OK`

### Test Coverage

Currently, only grade calculation logic is tested. The test verifies:
- Correct calculation of semester units
- Correct calculation of semester points
- Correct GPA computation

**Test Case**:
- 2 courses: CSC401 (3 units, score 75 → A), CSC402 (3 units, score 65 → B)
- Expected: 6 units, 27 points, 4.5 GPA

### Adding More Tests

To add tests for other components:

1. **Create test file**: `tests/component.test.js`
2. **Import dependencies**: Component/function to test
3. **Write test cases**: Use assert or testing framework
4. **Run tests**: `node tests/component.test.js`

**Example**:
```javascript
const assert = require('assert');
const { scoreToGrade } = require('../utils/grades');

assert.strictEqual(scoreToGrade(75), 'A');
assert.strictEqual(scoreToGrade(65), 'B');
console.log('scoreToGrade test: OK');
```

---

## Security Considerations

### Current Implementation (Development Only)

⚠️ **This application is designed for development/educational use only. Not production-ready.**

**Security Features**:
- Passcode-based authentication (single shared secret)
- Protected API routes require authorization header
- Input validation on result submission
- CORS configuration to restrict origins

**Security Limitations**:
- No password hashing (passcode stored in plain text)
- No rate limiting
- No SQL injection protection (using MongoDB, but still should validate inputs)
- No XSS protection beyond basic sanitization
- Session stored in localStorage (vulnerable to XSS)
- No HTTPS enforcement

### Production Recommendations

If deploying to production, consider:
1. **User Authentication**: Replace passcode with proper user accounts (JWT tokens, password hashing)
2. **Rate Limiting**: Prevent API abuse
3. **Input Validation**: Use libraries like Joi or Zod for schema validation
4. **HTTPS**: Enforce secure connections
5. **Environment Variables**: Never commit `.env` files
6. **Database Security**: Use MongoDB authentication, restrict network access
7. **Error Handling**: Don't expose internal errors to clients
8. **Logging**: Implement proper logging system (Winston, Morgan)
9. **Session Management**: Use httpOnly cookies instead of localStorage

---

## Performance Considerations

### Current Optimizations

1. **Static File Serving**: React build served directly by Express
2. **Database Indexing**: `matricNumber` has unique index for fast lookups
3. **Response Formatting**: Minimal data transfer
4. **Client-Side Caching**: localStorage for session management

### Potential Improvements

1. **Pagination**: For student lists (currently loads all students)
2. **Database Indexing**: Add indexes on frequently queried fields
3. **Caching**: Cache student records for frequently accessed matric numbers
4. **Lazy Loading**: Load semester details on demand
5. **Code Splitting**: Split React bundle for faster initial load

---

## Troubleshooting

### Server Won't Start

**Error**: "Port 5000 already in use"
- **Solution**: Change `PORT` in `.env` or kill process using port 5000

**Error**: "MongoDB connection failed"
- **Solution**: Ensure MongoDB is running, check `MONGO_URI` in `.env`

### Client Won't Connect to Server

**Error**: "Network request failed"
- **Solution**: 
  - Verify server is running
  - Check `vite.config.js` proxy configuration
  - Verify `CLIENT_ORIGIN` matches client URL

### Database Issues

**Error**: "Student not found" but student exists
- **Solution**: Check matric number spelling (case-sensitive), verify database connection

**Error**: "Duplicate key error"
- **Solution**: Matric number already exists, use update instead of create

---

## Contributing

### Code Structure

- **Frontend**: React components in `client/src/`
- **Backend**: Express routes in `server.js`
- **Models**: Mongoose schemas in `models/`
- **Utilities**: Shared functions in `utils/`

### Best Practices

1. **Follow existing patterns**: Match code style of existing components
2. **Test changes**: Run tests before committing
3. **Update documentation**: Keep README current with changes
4. **Error handling**: Always include try-catch for async operations
5. **Code comments**: Add comments for complex logic

---

## License & Credits

This project is developed for educational purposes. Feel free to use and modify as needed.

---

## Support & Contact

For issues or questions:
1. Check this README for common solutions
2. Review code comments in relevant files
3. Check server/client console logs for errors

---

**Last Updated**: See git history for latest changes

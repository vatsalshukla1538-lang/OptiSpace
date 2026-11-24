import React, { useState, useEffect } from 'react';
import api, { unwrap, API_BASE } from './api';

export default function Manage({ user }) {
  const isAdmin = user?.role === 'ADMIN' || user?.is_staff;
  const [activeTab, setActiveTab] = useState('rooms'); // 'rooms' | 'teachers' | 'courses' | 'groups'
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState(null);

  // Data lists
  const [rooms, setRooms] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [courses, setCourses] = useState([]);
  const [groups, setGroups] = useState([]);

  // Form states
  const [roomForm, setRoomForm] = useState({ room_number: '', capacity: 60, room_type: 'LECTURE' });
  const [teacherForm, setTeacherForm] = useState({ name: '', department: 'Information Technology' });
  const [courseForm, setCourseForm] = useState({
    code: '',
    name: '',
    credit_hours: 3,
    enrolled_students: 60,
    requires_lab: false,
    teacher: '',
    group: '',
  });
  const [groupForm, setGroupForm] = useState({ code: '', name: '' });

  // CSV Upload Modal
  const [showCsvModal, setShowCsvModal] = useState(false);
  const [csvFile, setCsvFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [rRes, tRes, cRes, gRes] = await Promise.all([
        api.get('/rooms/'),
        api.get('/teachers/'),
        api.get('/courses/'),
        api.get('/groups/'),
      ]);
      setRooms(unwrap(rRes.data));
      setTeachers(unwrap(tRes.data));
      setCourses(unwrap(cRes.data));
      setGroups(unwrap(gRes.data));
    } catch (err) {
      setAlert({ type: 'error', message: 'Failed to load data: ' + err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Form Submissions
  const handleAddRoom = async (e) => {
    e.preventDefault();
    if (!isAdmin) return;
    try {
      await api.post('/rooms/', roomForm);
      setAlert({ type: 'success', message: `Room ${roomForm.room_number} added!` });
      setRoomForm({ room_number: '', capacity: 60, room_type: 'LECTURE' });
      loadData();
    } catch (err) {
      setAlert({ type: 'error', message: err.response?.data?.error || err.response?.data?.room_number?.[0] || 'Error adding room.' });
    }
  };

  const handleAddTeacher = async (e) => {
    e.preventDefault();
    if (!isAdmin) return;
    try {
      await api.post('/teachers/', teacherForm);
      setAlert({ type: 'success', message: `Teacher ${teacherForm.name} added!` });
      setTeacherForm({ name: '', department: 'Information Technology' });
      loadData();
    } catch (err) {
      setAlert({ type: 'error', message: err.response?.data?.error || 'Error adding teacher.' });
    }
  };

  const handleAddCourse = async (e) => {
    e.preventDefault();
    if (!isAdmin) return;
    try {
      const payload = {
        ...courseForm,
        teacher: courseForm.teacher || null,
        group: courseForm.group || null,
      };
      await api.post('/courses/', payload);
      setAlert({ type: 'success', message: `Subject ${courseForm.name} added!` });
      setCourseForm({
        code: '',
        name: '',
        credit_hours: 3,
        enrolled_students: 60,
        requires_lab: false,
        teacher: '',
        group: '',
      });
      loadData();
    } catch (err) {
      setAlert({ type: 'error', message: err.response?.data?.error || err.response?.data?.code?.[0] || 'Error adding subject.' });
    }
  };

  const handleAddGroup = async (e) => {
    e.preventDefault();
    if (!isAdmin) return;
    try {
      await api.post('/groups/', groupForm);
      setAlert({ type: 'success', message: `Batch ${groupForm.code} added!` });
      setGroupForm({ code: '', name: '' });
      loadData();
    } catch (err) {
      setAlert({ type: 'error', message: err.response?.data?.error || 'Error adding batch.' });
    }
  };

  // Deletions
  const handleDelete = async (endpoint, id, name) => {
    if (!isAdmin || !window.confirm(`Delete ${name}?`)) return;
    try {
      await api.delete(`/${endpoint}/${id}/`);
      setAlert({ type: 'success', message: `Deleted ${name}.` });
      loadData();
    } catch {
      setAlert({ type: 'error', message: 'Failed to delete.' });
    }
  };

  // CSV Upload & Download Template
  const handleCsvUpload = async (e) => {
    e.preventDefault();
    if (!csvFile || !isAdmin) return;
    setUploading(true);
    setAlert(null);

    const formData = new FormData();
    formData.append('file', csvFile);

    try {
      const res = await api.post(`/import/${activeTab}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setAlert({ type: 'success', message: res.data?.message || 'CSV imported successfully!' });
      setShowCsvModal(false);
      setCsvFile(null);
      loadData();
    } catch (err) {
      setAlert({ type: 'error', message: err.response?.data?.error || 'CSV import failed.' });
    } finally {
      setUploading(false);
    }
  };

  const downloadCsvTemplate = () => {
    const url = `${API_BASE}/import/template/${activeTab}/`;
    window.open(url, '_blank');
  };

  return (
    <div className="tab-container">
      {/* Sub-navigation tabs */}
      <div className="subnav-bar">
        <button className={activeTab === 'rooms' ? 'subnav-active' : ''} onClick={() => setActiveTab('rooms')}>
          Classrooms & Labs ({rooms.length})
        </button>
        <button className={activeTab === 'teachers' ? 'subnav-active' : ''} onClick={() => setActiveTab('teachers')}>
          Faculty / Teachers ({teachers.length})
        </button>
        <button className={activeTab === 'courses' ? 'subnav-active' : ''} onClick={() => setActiveTab('courses')}>
          Subjects & Courses ({courses.length})
        </button>
        <button className={activeTab === 'groups' ? 'subnav-active' : ''} onClick={() => setActiveTab('groups')}>
          Student Batches ({groups.length})
        </button>
      </div>

      {/* Alert Banner */}
      {alert && (
        <div className={`alert-banner alert-${alert.type}`}>
          <span>{alert.message}</span>
          <button onClick={() => setAlert(null)}>✕</button>
        </div>
      )}

      {/* Action Header */}
      {loading && <div className="loading-state">Loading campus data...</div>}
      <div className="manage-header">
        <h2>{activeTab.toUpperCase()} MANAGEMENT</h2>
        {isAdmin && (
          <button className="btn btn-export" onClick={() => setShowCsvModal(true)}>
            📁 Upload {activeTab.toUpperCase()} CSV
          </button>
        )}
      </div>

      {/* ROOMS TAB */}
      {activeTab === 'rooms' && (
        <div className={`manage-layout ${isAdmin ? 'has-form' : 'table-only'}`}>
          {isAdmin && (
            <div className="form-card">
              <h3>Add New Classroom / Lab</h3>
              <form onSubmit={handleAddRoom}>
                <div className="form-group">
                  <label>Room Number / Name:</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. SH-5, 116, DS Lab"
                    value={roomForm.room_number}
                    onChange={(e) => setRoomForm({ ...roomForm, room_number: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Seating Capacity:</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={roomForm.capacity}
                    onChange={(e) => setRoomForm({ ...roomForm, capacity: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="form-group">
                  <label>Room Type:</label>
                  <select
                    value={roomForm.room_type}
                    onChange={(e) => setRoomForm({ ...roomForm, room_type: e.target.value })}
                  >
                    <option value="LECTURE">Lecture Hall (Theory)</option>
                    <option value="LAB">Computer / Practical Laboratory</option>
                  </select>
                </div>
                <button type="submit" className="btn btn-primary">Add Room</button>
              </form>
            </div>
          )}

          <div className="table-card">
            <h3>Registered Rooms ({rooms.length})</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Room</th>
                  <th>Capacity</th>
                  <th>Type</th>
                  <th>Status</th>
                  {isAdmin && <th>Action</th>}
                </tr>
              </thead>
              <tbody>
                {rooms.map((r) => (
                  <tr key={r.id}>
                    <td><strong>{r.room_number}</strong></td>
                    <td>{r.capacity} seats</td>
                    <td><span className={`badge ${r.room_type === 'LAB' ? 'badge-lab' : 'badge-lecture'}`}>{r.room_type}</span></td>
                    <td>{r.is_available ? '✅ Active' : '❌ Inactive'}</td>
                    {isAdmin && (
                      <td>
                        <button className="btn-small-danger" onClick={() => handleDelete('rooms', r.id, r.room_number)}>Delete</button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TEACHERS TAB */}
      {activeTab === 'teachers' && (
        <div className={`manage-layout ${isAdmin ? 'has-form' : 'table-only'}`}>
          {isAdmin && (
            <div className="form-card">
              <h3>Add Faculty Member</h3>
              <form onSubmit={handleAddTeacher}>
                <div className="form-group">
                  <label>Faculty Name:</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Dr. Akhilesh Tiwari"
                    value={teacherForm.name}
                    onChange={(e) => setTeacherForm({ ...teacherForm, name: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Department:</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Information Technology"
                    value={teacherForm.department}
                    onChange={(e) => setTeacherForm({ ...teacherForm, department: e.target.value })}
                  />
                </div>
                <button type="submit" className="btn btn-primary">Add Faculty</button>
              </form>
            </div>
          )}

          <div className="table-card">
            <h3>Registered Faculty ({teachers.length})</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Department</th>
                  {isAdmin && <th>Action</th>}
                </tr>
              </thead>
              <tbody>
                {teachers.map((t) => (
                  <tr key={t.id}>
                    <td><strong>{t.name}</strong></td>
                    <td>{t.department}</td>
                    {isAdmin && (
                      <td>
                        <button className="btn-small-danger" onClick={() => handleDelete('teachers', t.id, t.name)}>Delete</button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* COURSES / SUBJECTS TAB */}
      {activeTab === 'courses' && (
        <div className={`manage-layout ${isAdmin ? 'has-form' : 'table-only'}`}>
          {isAdmin && (
            <div className="form-card">
              <h3>Add Course / Subject</h3>
              <form onSubmit={handleAddCourse}>
                <div className="form-group">
                  <label>Course Code:</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 16261101"
                    value={courseForm.code}
                    onChange={(e) => setCourseForm({ ...courseForm, code: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Course Name:</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Programming in C"
                    value={courseForm.name}
                    onChange={(e) => setCourseForm({ ...courseForm, name: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Credit Hours (Weekly Sessions):</label>
                  <input
                    type="number"
                    min="1"
                    max="6"
                    required
                    value={courseForm.credit_hours}
                    onChange={(e) => setCourseForm({ ...courseForm, credit_hours: parseInt(e.target.value) || 1 })}
                  />
                </div>
                <div className="form-group">
                  <label>Enrolled Students:</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={courseForm.enrolled_students}
                    onChange={(e) => setCourseForm({ ...courseForm, enrolled_students: parseInt(e.target.value) || 1 })}
                  />
                </div>
                <div className="form-group">
                  <label>Assigned Faculty:</label>
                  <select
                    value={courseForm.teacher}
                    onChange={(e) => setCourseForm({ ...courseForm, teacher: e.target.value })}
                  >
                    <option value="">-- Select Teacher --</option>
                    {teachers.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Student Batch:</label>
                  <select
                    value={courseForm.group}
                    onChange={(e) => setCourseForm({ ...courseForm, group: e.target.value })}
                  >
                    <option value="">-- Select Batch --</option>
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>{g.code} ({g.name})</option>
                    ))}
                  </select>
                </div>
                <div className="form-group-checkbox">
                  <label>
                    <input
                      type="checkbox"
                      checked={courseForm.requires_lab}
                      onChange={(e) => setCourseForm({ ...courseForm, requires_lab: e.target.checked })}
                    />
                    Requires Computer Laboratory (Practical)
                  </label>
                </div>
                <button type="submit" className="btn btn-primary">Add Course</button>
              </form>
            </div>
          )}

          <div className="table-card">
            <h3>Registered Courses & Subjects ({courses.length})</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Course Title</th>
                  <th>Sessions/Wk</th>
                  <th>Faculty</th>
                  <th>Batch</th>
                  <th>Type</th>
                  {isAdmin && <th>Action</th>}
                </tr>
              </thead>
              <tbody>
                {courses.map((c) => (
                  <tr key={c.id}>
                    <td><code>{c.code}</code></td>
                    <td><strong>{c.name}</strong></td>
                    <td>{c.credit_hours} sessions</td>
                    <td>{c.teacher_name || 'None'}</td>
                    <td>{c.group_name || 'All'}</td>
                    <td><span className={`badge ${c.requires_lab ? 'badge-lab' : 'badge-lecture'}`}>{c.requires_lab ? 'LAB' : 'THEORY'}</span></td>
                    {isAdmin && (
                      <td>
                        <button className="btn-small-danger" onClick={() => handleDelete('courses', c.id, c.name)}>Delete</button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* STUDENT BATCHES TAB */}
      {activeTab === 'groups' && (
        <div className={`manage-layout ${isAdmin ? 'has-form' : 'table-only'}`}>
          {isAdmin && (
            <div className="form-card">
              <h3>Add Student Section / Batch</h3>
              <form onSubmit={handleAddGroup}>
                <div className="form-group">
                  <label>Batch Code:</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. IT-I-A, IT-I-A1"
                    value={groupForm.code}
                    onChange={(e) => setGroupForm({ ...groupForm, code: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Batch Name / Description:</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. IT Semester 1 Section A"
                    value={groupForm.name}
                    onChange={(e) => setGroupForm({ ...groupForm, name: e.target.value })}
                  />
                </div>
                <button type="submit" className="btn btn-primary">Add Batch</button>
              </form>
            </div>
          )}

          <div className="table-card">
            <h3>Registered Student Batches ({groups.length})</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Batch Code</th>
                  <th>Description</th>
                  {isAdmin && <th>Action</th>}
                </tr>
              </thead>
              <tbody>
                {groups.map((g) => (
                  <tr key={g.id}>
                    <td><strong>{g.code}</strong></td>
                    <td>{g.name}</td>
                    {isAdmin && (
                      <td>
                        <button className="btn-small-danger" onClick={() => handleDelete('groups', g.id, g.code)}>Delete</button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CSV UPLOAD MODAL */}
      {showCsvModal && (
        <div className="modal-overlay" onClick={() => setShowCsvModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Upload CSV for {activeTab.toUpperCase()}</h3>
              <button className="close-btn" onClick={() => setShowCsvModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p>Upload a CSV file containing your list of {activeTab}.</p>
              <div className="template-link">
                <button className="btn-link" onClick={downloadCsvTemplate}>
                  📥 Download Sample CSV Template
                </button>
              </div>

              <form onSubmit={handleCsvUpload}>
                <div className="form-group">
                  <label>Select CSV File:</label>
                  <input
                    type="file"
                    accept=".csv"
                    required
                    onChange={(e) => setCsvFile(e.target.files[0])}
                  />
                </div>

                <div className="modal-actions">
                  <button type="submit" className="btn btn-primary" disabled={uploading}>
                    {uploading ? 'Uploading...' : 'Upload & Process'}
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowCsvModal(false)}>
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

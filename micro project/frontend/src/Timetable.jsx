import React, { useState, useEffect } from 'react';
import api, { unwrap, API_BASE } from './api';

const DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI'];
const DAY_LABELS = { MON: 'Monday', TUE: 'Tuesday', WED: 'Wednesday', THU: 'Thursday', FRI: 'Friday' };
const TIME_SLOTS = [
  '10:00-11:00',
  '11:00-12:00',
  '01:00-02:00',
  '02:00-03:00',
  '03:00-04:00',
  '04:00-05:00',
  '05:00-06:00',
];

const slotMatches = (sSlot, gridSlot) => {
  if (!sSlot) return false;
  if (sSlot === gridSlot) return true;
  const alias = {
    '13:00-14:00': '01:00-02:00',
    '14:00-15:00': '02:00-03:00',
    '15:00-16:00': '03:00-04:00',
    '16:00-17:00': '04:00-05:00',
    '17:00-18:00': '05:00-06:00',
    '01:00-02:00': '13:00-14:00',
    '02:00-03:00': '14:00-15:00',
    '03:00-04:00': '15:00-16:00',
    '04:00-05:00': '16:00-17:00',
    '05:00-06:00': '17:00-18:00',
  };
  return alias[sSlot] === gridSlot;
};

export default function Timetable({ user }) {
  const isAdmin = user?.role === 'ADMIN' || user?.is_staff;
  const userBatch = user?.batch || '';
  const [schedules, setSchedules] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [alert, setAlert] = useState(null); // { type: 'success' | 'error', message: '' }

  // Filters: viewers default to their enrolled batch
  const [selectedSem, setSelectedSem] = useState('ALL');
  const [selectedBatch, setSelectedBatch] = useState(() => (!isAdmin && userBatch ? userBatch : 'ALL'));
  const [selectedType, setSelectedType] = useState('ALL'); // 'ALL' | 'LAB' | 'THEORY'
  const [search, setSearch] = useState('');

  // Keep viewer batch in sync
  useEffect(() => {
    if (!isAdmin && userBatch) {
      setSelectedBatch(userBatch);
    }
  }, [userBatch, isAdmin]);

  // Drag and Drop state
  const [draggedItem, setDraggedItem] = useState(null);
  const [dragOverCell, setDragOverCell] = useState(null);

  // Edit Modal State
  const [activeSession, setActiveSession] = useState(null);
  const [editRoom, setEditRoom] = useState('');
  const [editDay, setEditDay] = useState('');
  const [editSlot, setEditSlot] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [schedRes, roomRes, groupRes] = await Promise.all([
        api.get('/schedules/'),
        api.get('/rooms/'),
        api.get('/groups/'),
      ]);
      setSchedules(unwrap(schedRes.data));
      setRooms(unwrap(roomRes.data));
      setGroups(unwrap(groupRes.data));
    } catch (err) {
      setAlert({ type: 'error', message: 'Failed to load timetable: ' + (err.response?.data?.error || err.message) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleGenerate = async () => {
    if (!isAdmin) return;
    setGenerating(true);
    setAlert(null);
    try {
      const res = await api.post('/schedule/generate/');
      setAlert({
        type: 'success',
        message: `Timetable generated successfully! ${res.data.total_scheduled_sessions} sessions scheduled with 0 conflicts.`,
      });
      loadData();
    } catch (err) {
      setAlert({
        type: 'error',
        message: err.response?.data?.error || 'Generation failed. Existing timetable was preserved.',
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleClear = async () => {
    if (!isAdmin || !window.confirm('Are you sure you want to clear the entire schedule?')) return;
    try {
      await api.post('/schedule/clear/');
      setAlert({ type: 'success', message: 'Timetable cleared.' });
      loadData();
    } catch (err) {
      setAlert({ type: 'error', message: err.response?.data?.error || 'Failed to clear timetable.' });
    }
  };

  const downloadFile = (endpoint, filename) => {
    const params = new URLSearchParams();
    if (selectedSem !== 'ALL') params.append('semester', selectedSem);
    const activeBatch = (!isAdmin && userBatch) ? userBatch : selectedBatch;
    if (activeBatch !== 'ALL') params.append('batch', activeBatch);
    if (selectedType !== 'ALL') params.append('type', selectedType);
    const url = `${API_BASE}${endpoint}?${params.toString()}`;
    const token = localStorage.getItem('access');

    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (!res.ok) throw new Error('Download failed');
        return res.blob();
      })
      .then((blob) => {
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
      })
      .catch((err) => setAlert({ type: 'error', message: 'Export failed: ' + err.message }));
  };

  // Drag and Drop handlers
  const handleDragStart = (e, session) => {
    if (!isAdmin) return;
    setDraggedItem(session);
    e.dataTransfer.setData('text/plain', session.id);
  };

  const handleDragOver = (e, day, slot) => {
    if (!isAdmin || !draggedItem) return;
    e.preventDefault();
    setDragOverCell(`${day}-${slot}`);
  };

  const handleDrop = async (e, targetDay, targetSlot) => {
    e.preventDefault();
    setDragOverCell(null);
    if (!isAdmin || !draggedItem) return;

    if (draggedItem.day === targetDay && draggedItem.time_slot === targetSlot) {
      setDraggedItem(null);
      return;
    }

    setAlert(null);
    try {
      const roomId = (typeof draggedItem.room === 'object' ? draggedItem.room?.id : draggedItem.room) || draggedItem.room_id;
      const courseName = (typeof draggedItem.course === 'object' ? draggedItem.course?.name : draggedItem.course_name) || 'Class';
      // 1. Validate with backend
      const valRes = await api.post('/schedule/validate/', {
        schedule_id: draggedItem.id,
        room_id: roomId,
        day: targetDay,
        time_slot: targetSlot,
      });

      if (!valRes.data.valid) {
        const errorMsg = valRes.data.conflicts?.[0]?.message || valRes.data.message || 'Slot causes a schedule collision.';
        setAlert({ type: 'error', message: `❌ Conflict Detected: ${errorMsg} Class was not moved.` });
        setDraggedItem(null);
        return;
      }

      // 2. Perform move
      await api.patch(`/schedules/${draggedItem.id}/`, {
        day: targetDay,
        time_slot: targetSlot,
      });

      setAlert({ type: 'success', message: `✅ Moved "${courseName}" to ${DAY_LABELS[targetDay]} ${targetSlot}.` });
      loadData();
    } catch (err) {
      setAlert({
        type: 'error',
        message: '❌ Conflict: ' + (err.response?.data?.error || err.response?.data?.message || 'Move rejected.'),
      });
    } finally {
      setDraggedItem(null);
    }
  };

  // Open Edit Modal
  const openEdit = (session) => {
    setActiveSession(session);
    const roomId = (typeof session.room === 'object' ? session.room?.id : session.room) || session.room_id || '';
    setEditRoom(roomId);
    setEditDay(session.day);
    setEditSlot(session.time_slot);
  };

  const handleSaveEdit = async () => {
    if (!activeSession) return;
    try {
      // Validate
      const val = await api.post('/schedule/validate/', {
        schedule_id: activeSession.id,
        room_id: editRoom || null,
        day: editDay,
        time_slot: editSlot,
      });
      if (!val.data.valid) {
        setAlert({ type: 'error', message: '❌ Conflict: ' + (val.data.message || 'Cannot place in this slot.') });
        return;
      }
      await api.patch(`/schedules/${activeSession.id}/`, {
        room: editRoom || null,
        day: editDay,
        time_slot: editSlot,
      });
      setAlert({ type: 'success', message: 'Session updated successfully.' });
      setActiveSession(null);
      loadData();
    } catch (err) {
      setAlert({ type: 'error', message: err.response?.data?.error || 'Save failed.' });
    }
  };

  const handleDeleteSession = async (id) => {
    if (!window.confirm('Delete this scheduled class?')) return;
    try {
      await api.delete(`/schedules/${id}/`);
      setAlert({ type: 'success', message: 'Session deleted.' });
      setActiveSession(null);
      loadData();
    } catch {
      setAlert({ type: 'error', message: 'Delete failed.' });
    }
  };

  // Filtered schedules
  const filteredSchedules = schedules.filter((s) => {
    const course = typeof s.course === 'object' ? s.course : {};
    const group = (course?.group?.code || s.group_code || '').trim();
    const name = (course?.name || s.course_name || '').toLowerCase();
    const code = (course?.code || s.course_code || '').toLowerCase();
    const teacher = (s.teacher?.name || s.teacher_name || '').toLowerCase();
    const room = (s.room?.room_number || s.room_number || '').toLowerCase();
    const isLab = course?.requires_lab ?? s.course_requires_lab ?? false;

    // Type filter
    if (selectedType === 'LAB' && !isLab) return false;
    if (selectedType === 'THEORY' && isLab) return false;

    // Section / Batch filter
    if (selectedBatch === 'SEC-A') {
      const isSecA = group.includes('-A') || group.endsWith('A') || code.includes('-a');
      const isSecB = group.includes('-B') || group.endsWith('B') || code.includes('-b');
      if (!isSecA || (isSecB && !isSecA)) return false;
    } else if (selectedBatch === 'SEC-B') {
      const isSecB = group.includes('-B') || group.endsWith('B') || code.includes('-b');
      const isSecA = group.includes('-A') || group.endsWith('A') || code.includes('-a');
      if (!isSecB || (isSecA && !isSecB)) return false;
    } else if (selectedBatch === 'Batch-A1' || selectedBatch === 'A1') {
      const isSecB = group.includes('-B') || group.endsWith('B') || code.includes('-b');
      if (isSecB) return false;
      if (isLab) {
        const isA1 = group.includes('A1') || code.includes('a1') || code.includes('16261110-a');
        if (!isA1) return false;
      }
    } else if (selectedBatch === 'Batch-A2' || selectedBatch === 'A2') {
      const isSecB = group.includes('-B') || group.endsWith('B') || code.includes('-b');
      if (isSecB) return false;
      if (isLab) {
        const isA2 = group.includes('A2') || code.includes('a2') || code.includes('16261110-a');
        if (!isA2) return false;
      }
    } else if (selectedBatch === 'Batch-B1' || selectedBatch === 'B1') {
      const isSecA = group.includes('-A') || group.endsWith('A') || code.includes('-a');
      if (isSecA) return false;
      if (isLab) {
        const isB1 = group.includes('B1') || code.includes('b1') || code.includes('16261110-b');
        if (!isB1) return false;
      }
    } else if (selectedBatch === 'Batch-B2' || selectedBatch === 'B2') {
      const isSecA = group.includes('-A') || group.endsWith('A') || code.includes('-a');
      if (isSecA) return false;
      if (isLab) {
        const isB2 = group.includes('B2') || code.includes('b2') || code.includes('16261110-b');
        if (!isB2) return false;
      }
    }

    if (selectedSem !== 'ALL' && !group.startsWith(`IT-${selectedSem}`) && !group.startsWith('Batch-')) {
      return false;
    }
    if (search) {
      const q = search.toLowerCase();
      if (!name.includes(q) && !code.includes(q) && !teacher.includes(q) && !room.includes(q) && !group.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  const labCount = filteredSchedules.filter((s) => (typeof s.course === 'object' ? s.course?.requires_lab : s.course_requires_lab)).length;
  const theoryCount = filteredSchedules.length - labCount;

  return (
    <div className="tab-container">
      {/* Action / Toolbar Header */}
      <div className="toolbar-card">
        <div className="filter-group">
          <label>Semester:
            <select value={selectedSem} onChange={(e) => setSelectedSem(e.target.value)}>
              <option value="ALL">All Semesters</option>
              <option value="I">Semester I</option>
              <option value="III">Semester III</option>
              <option value="V">Semester V</option>
              <option value="VII">Semester VII</option>
            </select>
          </label>

          {isAdmin ? (
            <label>Batch / Section:
              <select value={selectedBatch} onChange={(e) => setSelectedBatch(e.target.value)}>
                <option value="ALL">Both (Section A & B)</option>
                <option value="SEC-A">Section A (Complete)</option>
                <option value="SEC-B">Section B (Complete)</option>
                <option value="Batch-A1">Batch A1 (Sec A Theory + A1 Labs)</option>
                <option value="Batch-A2">Batch A2 (Sec A Theory + A2 Labs)</option>
                <option value="Batch-B1">Batch B1 (Sec B Theory + B1 Labs)</option>
                <option value="Batch-B2">Batch B2 (Sec B Theory + B2 Labs)</option>
              </select>
            </label>
          ) : (
            <div className="viewer-batch-pill" title="Timetable locked to your registered student batch">
              🎓 Your Batch: <strong>{userBatch ? userBatch.replace('Batch-', 'Batch ').replace('SEC-', 'Section ') : 'All Classes'}</strong>
            </div>
          )}

          <label>Class Type:
            <select value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>
              <option value="ALL">All Classes (Theory + Labs)</option>
              <option value="LAB">🔬 Practical Labs Only</option>
              <option value="THEORY">📖 Theory Lectures Only</option>
            </select>
          </label>

          <input
            type="text"
            className="search-input"
            placeholder="Search subject, lab, faculty, room..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="button-group">
          {isAdmin && (
            <>
              <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
                {generating ? '⏳ Generating...' : '⚡ Generate Timetable'}
              </button>
              <button className="btn btn-secondary" onClick={handleClear}>Clear</button>
            </>
          )}
          <button className="btn btn-export" onClick={() => downloadFile('/schedule/export.xlsx', 'MITS_Timetable.xlsx')}>
            📊 Export Excel
          </button>
          <button className="btn btn-export" onClick={() => downloadFile('/schedule/export.pdf', 'MITS_Timetable.pdf')}>
            📄 Export PDF
          </button>
        </div>
      </div>

      {/* Timetable Status / Legend Bar */}
      <div className="timetable-status-bar">
        <span>
          Showing <strong>{filteredSchedules.length}</strong> Sessions
          {!isAdmin && userBatch ? ` for ${userBatch.replace('Batch-', 'Batch ').replace('SEC-', 'Section ')}` : ''}
          {' '}(<strong style={{ color: '#0284c7' }}>{labCount} Practical Labs</strong>,
          {' '}<strong style={{ color: '#16a34a' }}>{theoryCount} Theory Lectures</strong>)
        </span>
        <div className="legend-pills">
          <span className="pill pill-lecture">📖 Theory (Merged Section)</span>
          <span className="pill pill-lab">🔬 Practical Labs</span>
        </div>
      </div>

      {/* Alert Banner */}
      {alert && (
        <div className={`alert-banner alert-${alert.type}`}>
          <span>{alert.message}</span>
          <button onClick={() => setAlert(null)}>✕</button>
        </div>
      )}

      {/* Timetable Weekly Grid */}
      {loading ? (
        <div className="loading-state">Loading timetable data...</div>
      ) : (
        <div className="calendar-wrapper">
          <div className="calendar-grid">
            {/* Header row: Time Slots across the columns */}
            <div className="grid-header-corner">Day \ Time</div>
            {TIME_SLOTS.map((slot) => (
              <div key={slot} className="grid-header-slot">
                <strong>{slot}</strong>
              </div>
            ))}

            {/* Days down the rows */}
            {DAYS.map((day) => (
              <React.Fragment key={day}>
                <div className="grid-day-label">
                  <strong>{DAY_LABELS[day]}</strong>
                  <small>{day}</small>
                </div>
                {TIME_SLOTS.map((slot) => {
                  const cellKey = `${day}-${slot}`;
                  const isHovered = dragOverCell === cellKey;
                  const cellSessions = filteredSchedules.filter((s) => s.day === day && slotMatches(s.time_slot, slot));

                  return (
                    <div
                      key={cellKey}
                      className={`grid-cell ${isHovered ? 'drag-over' : ''}`}
                      onDragOver={(e) => handleDragOver(e, day, slot)}
                      onDrop={(e) => handleDrop(e, day, slot)}
                    >
                      {cellSessions.map((s) => {
                        const course = typeof s.course === 'object' ? s.course : {};
                        const code = course?.code || s.course_code || '';
                        const name = course?.name || s.course_name || '';
                        const isLab = course?.requires_lab ?? s.course_requires_lab ?? false;
                        const roomNum = s.room?.room_number || s.room_number || 'Room TBD';
                        const teacherName = s.teacher?.name || s.teacher_name || 'Faculty TBD';
                        const rawBatch = course?.group?.code || s.group_code || '';

                        let batchDisplay = '';
                        if (isLab) {
                          if (rawBatch.includes('A1') || code.includes('A1')) batchDisplay = 'Batch: A1';
                          else if (rawBatch.includes('A2') || code.includes('A2')) batchDisplay = 'Batch: A2';
                          else if (rawBatch.includes('B1') || code.includes('B1')) batchDisplay = 'Batch: B1';
                          else if (rawBatch.includes('B2') || code.includes('B2')) batchDisplay = 'Batch: B2';
                          else if (rawBatch.includes('-A') || rawBatch.endsWith('A') || code.includes('-A')) batchDisplay = 'Section: A';
                          else if (rawBatch.includes('-B') || rawBatch.endsWith('B') || code.includes('-B')) batchDisplay = 'Section: B';
                        } else {
                          // Theory: merged whole section
                          if (rawBatch.includes('-A') || rawBatch.endsWith('A') || code.includes('-A')) batchDisplay = 'Section: A';
                          else if (rawBatch.includes('-B') || rawBatch.endsWith('B') || code.includes('-B')) batchDisplay = 'Section: B';
                        }

                        const isMentorMeeting = code.toUpperCase().startsWith('MENTOR') || name.toLowerCase().includes('mentor mentee');
                        if (isMentorMeeting) {
                          return (
                            <div
                              key={s.id}
                              className="session-card session-mentor"
                              draggable={isAdmin}
                              onDragStart={(e) => handleDragStart(e, s)}
                              onClick={() => openEdit(s)}
                              title={isAdmin ? 'Mentor Mentee Meeting (Drag to change slot, or click to edit)' : 'Mentor Mentee Meeting'}
                            >
                              <div className="card-mentor-title">Mentor Mentee Meeting</div>
                            </div>
                          );
                        }

                        return (
                          <div
                            key={s.id}
                            className={`session-card ${isLab ? 'session-lab' : 'session-lecture'}`}
                            draggable={isAdmin}
                            onDragStart={(e) => handleDragStart(e, s)}
                            onClick={() => openEdit(s)}
                            title={isAdmin ? 'Drag to change slot, or click to edit' : 'Click to view details'}
                          >
                            <div className="card-top">
                              <span className="card-code">{code}</span>
                              <span className={`card-badge ${isLab ? 'badge-lab' : 'badge-theory'}`}>
                                {isLab ? '🔬 LAB' : '📖 THEORY'}
                              </span>
                            </div>
                            <div className="card-name">{name}</div>
                            <div className="card-details">
                              {roomNum ? (
                                <span>{isLab ? '🔬' : '📍'} {roomNum}</span>
                              ) : (
                                <span style={{ color: '#64748b', fontStyle: 'italic' }}>👥 No Room</span>
                              )}
                              <span>👤 {teacherName}</span>
                            </div>
                            {batchDisplay && (
                              <div className="card-batch">{batchDisplay}</div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  );
                })}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* Edit / Detail Modal */}
      {activeSession && (
        <div className="modal-overlay" onClick={() => setActiveSession(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Class Details: {(typeof activeSession.course === 'object' ? activeSession.course?.name : activeSession.course_name) || 'Class'}</h3>
              <button className="close-btn" onClick={() => setActiveSession(null)}>✕</button>
            </div>
            <div className="modal-body">
              <p><strong>Course Code:</strong> {(typeof activeSession.course === 'object' ? activeSession.course?.code : activeSession.course_code) || 'N/A'}</p>
              <p><strong>Faculty:</strong> {(typeof activeSession.teacher === 'object' ? activeSession.teacher?.name : activeSession.teacher_name) || 'Faculty TBD'}</p>
              <p><strong>Student Batch:</strong> {(typeof activeSession.course === 'object' ? activeSession.course?.group?.code : activeSession.group_code) || 'All'}</p>
              <p><strong>Required Type:</strong> {((typeof activeSession.course === 'object' ? activeSession.course?.requires_lab : activeSession.course_requires_lab)) ? 'Laboratory' : 'Lecture Hall'}</p>

              {isAdmin ? (
                <>
                  <hr />
                  <h4>Manual Edit (Admin)</h4>
                  <div className="form-group">
                    <label>Room:</label>
                    <select value={editRoom} onChange={(e) => setEditRoom(e.target.value)}>
                      <option value="">-- No Room (Meeting) --</option>
                      {rooms.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.room_number} ({r.capacity} seats - {r.room_type})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label>Day:</label>
                    <select value={editDay} onChange={(e) => setEditDay(e.target.value)}>
                      {DAYS.map((d) => (
                        <option key={d} value={d}>{DAY_LABELS[d]}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label>Time Slot:</label>
                    <select value={editSlot} onChange={(e) => setEditSlot(e.target.value)}>
                      {TIME_SLOTS.map((ts) => (
                        <option key={ts} value={ts}>{ts}</option>
                      ))}
                    </select>
                  </div>

                  <div className="modal-actions">
                    <button className="btn btn-primary" onClick={handleSaveEdit}>Save Changes</button>
                    <button className="btn btn-danger" onClick={() => handleDeleteSession(activeSession.id)}>Delete Class</button>
                    <button className="btn btn-secondary" onClick={() => setActiveSession(null)}>Cancel</button>
                  </div>
                </>
              ) : (
                <div className="modal-actions">
                  <button className="btn btn-secondary" onClick={() => setActiveSession(null)}>Close</button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

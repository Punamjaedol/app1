// Initialize icons
lucide.createIcons();

// API_BASE_URL is defined in auth.js

// --- STATE MANAGEMENT ---
let currentUser = JSON.parse(localStorage.getItem('currentUser')) || null;

let appState = {
    places: [], // { id, name, address, timestamp }
    schedules: {}, // { 'YYYY-MM-DD': [{ id, title, time, placeId }] }
};

// --- DATA FETCHING (FASTAPI) ---
async function fetchTimeline() {
    if (!currentUser) return;
    try {
        const response = await fetch(`${API_BASE_URL}/timeline?couple_id=${currentUser.couple_id}`);
        if (response.ok) {
            appState.places = await response.json();
            renderTimeline();
        }
    } catch (error) {
        console.error("Timeline fetch failed:", error);
    }
}

async function fetchSchedulesForDate(dateStr) {
    if (!currentUser) return;
    try {
        const response = await fetch(`${API_BASE_URL}/schedule/${dateStr}?couple_id=${currentUser.couple_id}`);
        if (response.ok) {
            appState.schedules[dateStr] = await response.json();
            renderCalendar();
            renderSchedules();
        }
    } catch (error) {
        console.error("Schedule fetch failed:", error);
    }
}

async function fetchMonthSchedules(year, month) {
    if (!currentUser) return;
    const yearMonth = `${year}-${String(month + 1).padStart(2, '0')}`;
    try {
        const response = await fetch(`${API_BASE_URL}/schedule/month/${yearMonth}?couple_id=${currentUser.couple_id}`);
        if (response.ok) {
            const data = await response.json();
            // Merge into appState.schedules
            Object.assign(appState.schedules, data);
        }
    } catch (error) {
        console.error("Month schedule fetch failed:", error);
    }
}

// --- GPS POLLING LOGIC ---
let watchId = null;

function startGpsTracking() {
    if (!currentUser) return;
    const statusText = document.getElementById('gps-status-text');

    if ("geolocation" in navigator) {
        watchId = navigator.geolocation.watchPosition(
            async (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                statusText.textContent = `📍 ${lat.toFixed(5)}, ${lng.toFixed(5)}`;

                initMapWithLocation(lat, lng);

                try {
                    const res = await fetch(`${API_BASE_URL}/location?couple_id=${currentUser.couple_id}`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ lat, lng })
                    });
                    const data = await res.json();
                    if (data.place_tagged) {
                        fetchTimeline();
                    }
                } catch (err) {
                    console.error("Failed to send GPS", err);
                    statusText.textContent = "Server offline. Waiting...";
                }
            },
            (error) => {
                console.error(error);
                statusText.textContent = "GPS Access Denied.";
            },
            { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
        );
    } else {
        statusText.textContent = "Geolocation not supported.";
    }
}

async function deletePlace(placeId) {
    if (!currentUser) return;
    if (!confirm("Are you sure you want to delete this memory?")) return;
    try {
        const res = await fetch(`${API_BASE_URL}/places/${placeId}?couple_id=${currentUser.couple_id}`, { method: "DELETE" });
        if (res.ok) {
            fetchTimeline();
        }
    } catch (e) {
        console.error("Failed to delete place", e);
    }
}

// --- NAVIGATION ---
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    document.querySelectorAll('.nav-item').forEach(v => v.classList.remove('active'));

    document.getElementById(`view-${viewName}`).classList.remove('hidden');
    document.getElementById(`nav-${viewName}`).classList.add('active');

    if (viewName === 'calendar') {
        renderCalendar();
    } else if (viewName === 'map') {
        fetchTimeline();
    }
}

// --- MAP & TAGGING VIEW ---
function renderTimeline() {
    const container = document.getElementById('timeline-list');
    if (appState.places.length === 0) {
        container.innerHTML = '<p class="text-muted text-sm mt-2">No places automatically tagged yet. Stay in one place for 10 seconds to generate a record!</p>';
        return;
    }

    container.innerHTML = appState.places.map(p => {
        const date = new Date(p.timestamp);
        const timeString = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const dateString = date.toLocaleDateString([], { month: 'short', day: 'numeric' });

        return `
            <div class="timeline-item">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div class="timeline-title">${p.name}</div>
                    <button class="icon-btn" onclick="deletePlace('${p.id}')" style="width: 24px; height: 24px; color: var(--text-muted);"><i data-lucide="trash-2" style="width: 14px; height: 14px;"></i></button>
                </div>
                <div class="timeline-meta">
                    <i data-lucide="clock"></i> ${dateString} at ${timeString}
                </div>
                <div class="timeline-meta mt-1">
                    <i data-lucide="map-pin"></i> ${p.address}
                </div>
            </div>
        `;
    }).join('');

    lucide.createIcons();
}

// --- CALENDAR VIEW ---
let currentDate = new Date();
let selectedDateStr = null;

async function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    await fetchMonthSchedules(year, month);

    document.getElementById('calendar-month-year').textContent =
        new Date(year, month).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();

    const grid = document.getElementById('calendar-grid');
    let html = '';

    for (let i = 0; i < firstDay; i++) {
        html += '<div class="calendar-day empty"></div>';
    }

    for (let i = 1; i <= daysInMonth; i++) {
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
        const isToday = today.getFullYear() === year && today.getMonth() === month && today.getDate() === i;
        const isSelected = selectedDateStr === dateStr;
        const hasEvent = appState.schedules[dateStr] && appState.schedules[dateStr].length > 0;

        let classes = 'calendar-day';
        if (isToday) classes += ' today';
        if (isSelected) classes += ' active';
        if (hasEvent) classes += ' has-event';

        html += `<div class="${classes}" onclick="selectDate('${dateStr}')">${i}</div>`;
    }

    grid.innerHTML = html;

    if (!selectedDateStr && today.getFullYear() === year && today.getMonth() === month) {
        selectDate(`${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`, false);
    } else if (selectedDateStr) {
        renderSchedules();
    }
}

function changeMonth(delta) {
    currentDate.setMonth(currentDate.getMonth() + delta);
    renderCalendar();
}

function selectDate(dateStr, showModal = false) { // Default to false
    selectedDateStr = dateStr;
    const [y, m, d] = dateStr.split('-');

    // Update Inline Title
    const inlineTitle = document.getElementById('selected-date-title');
    if (inlineTitle) inlineTitle.textContent = `${y}. ${m}. ${d}`;

    // Update Modal Title
    const modalTitle = document.getElementById('modal-date-title');
    if (modalTitle) modalTitle.textContent = `${y}. ${m}. ${d}`;

    fetchSchedulesForDate(dateStr);
    if (showModal) openModal();
}

function renderSchedules() {
    if (!selectedDateStr) return;

    const inlineList = document.getElementById('schedule-list');
    const daySchedules = appState.schedules[selectedDateStr] || [];

    const emptyHtml = '<p class="empty-state" style="color: var(--text-muted); font-size: 14px; text-align: center; padding: 20px 0;">No schedules for this day.</p>';

    if (daySchedules.length === 0) {
        if (inlineList) inlineList.innerHTML = emptyHtml;
    } else {
        const listHtml = daySchedules.map(s => {
            let placeHtml = '';
            if (s.placeId) {
                const place = appState.places.find(p => p.id === s.placeId);
                const placeName = place ? place.name : "Saved Place";
                placeHtml = `<div style="font-size: 11px; color: var(--primary-color); display: flex; align-items: center; gap: 4px; margin-top: 2px;"><i data-lucide="map-pin" style="width:10px; height:10px;"></i> ${placeName}</div>`;
            }

            return `
                <div class="modal-schedule-item">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; font-size: 15px;">${s.title}</div>
                        <div style="font-size: 12px; color: var(--text-muted);">${s.time || 'All day'}</div>
                        ${placeHtml}
                    </div>
                    <div class="schedule-actions">
                        <div class="action-icon edit" onclick="editSchedule('${s.id}')">
                            <i data-lucide="edit-2" style="width: 14px; height: 14px;"></i>
                        </div>
                        <div class="action-icon delete" onclick="deleteSchedule('${s.id}')">
                            <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        if (inlineList) inlineList.innerHTML = listHtml;
    }

    lucide.createIcons();
}

// --- MODAL & SCHEDULE CRUD ---
function openModal() {
    document.getElementById('modal-overlay').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
    pendingLinkedPlaceId = null;
    resetForm();
}

function showAddForm(openModalFlag = false) {
    resetForm();
    if (openModalFlag) openModal();
}

function resetForm() {
    document.getElementById('edit-schedule-id').value = '';
    document.getElementById('schedule-title').value = '';
    document.getElementById('schedule-time').value = '';
    document.getElementById('linked-place').textContent = 'None linked';
    pendingLinkedPlaceId = null;
}

function editSchedule(scheduleId) {
    const s = appState.schedules[selectedDateStr].find(item => item.id === scheduleId);
    if (!s) return;

    document.getElementById('edit-schedule-id').value = s.id;
    document.getElementById('schedule-title').value = s.title;
    document.getElementById('schedule-time').value = s.time || '';

    if (s.placeId) {
        const place = appState.places.find(p => p.id === s.placeId);
        document.getElementById('linked-place').textContent = place ? place.name : 'Linked Place';
        pendingLinkedPlaceId = s.placeId;
    } else {
        document.getElementById('linked-place').textContent = 'None linked';
        pendingLinkedPlaceId = null;
    }

    openModal();
}

async function saveSchedule() {
    if (!currentUser) return;
    const scheduleId = document.getElementById('edit-schedule-id').value;
    const title = document.getElementById('schedule-title').value;
    const time = document.getElementById('schedule-time').value;

    if (!title) {
        alert('Please enter a schedule title.');
        return;
    }

    const payload = {
        date: selectedDateStr,
        title,
        time,
        placeId: pendingLinkedPlaceId
    };

    try {
        let res;
        if (scheduleId) {
            // Update
            res = await fetch(`${API_BASE_URL}/schedule/${scheduleId}?couple_id=${currentUser.couple_id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
        } else {
            // Create
            res = await fetch(`${API_BASE_URL}/schedule?couple_id=${currentUser.couple_id}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
        }

        if (res.ok) {
            fetchSchedulesForDate(selectedDateStr);
            closeModal();
        }
    } catch (e) {
        console.error("Failed to save schedule", e);
    }
}

async function deleteSchedule(scheduleId) {
    if (!currentUser || !confirm("Are you sure you want to delete this schedule?")) return;

    try {
        const res = await fetch(`${API_BASE_URL}/schedule/${scheduleId}?couple_id=${currentUser.couple_id}`, {
            method: "DELETE"
        });
        if (res.ok) {
            fetchSchedulesForDate(selectedDateStr);
        }
    } catch (e) {
        console.error("Failed to delete schedule", e);
    }
}

// --- INIT ---
function initApp() {
    console.log("Initializing App...");
    if (currentUser) {
        fetchTimeline();

        if (typeof kakao !== 'undefined' && kakao.maps) {
            console.log("Loading Kakao Maps...");
            kakao.maps.load(() => {
                console.log("Kakao Maps Loaded.");
                startGpsTracking();
            });
        } else {
            console.error("Kakao Maps SDK not loaded. Check your API key and domain settings.");
            const mapContainer = document.getElementById('kakao-map');
            if (mapContainer) {
                mapContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">카카오 지도 SDK를 로드할 수 없습니다.<br>API 키와 도메인 설정을 확인해주세요.</div>';
            }
        }

        // Update avatars for the couple
        const avatar1 = document.getElementById('avatar-1');
        const avatar2 = document.getElementById('avatar-2');

        if (avatar1 && avatar2) {
            // Show both partners. If current user is user1, show user1 and user2. 
            // Simplified logic: user1 is always 'S', user2 is always 'J' (as per user's colors preference)
            avatar1.src = `https://ui-avatars.com/api/?name=user1&background=ff6b6b&color=fff&rounded=true`;
            avatar1.title = "user1";
            avatar2.src = `https://ui-avatars.com/api/?name=user2&background=4ecdc4&color=fff&rounded=true`;
            avatar2.title = "user2";
        }

        fetchCoupleInfo();
    } else {
        console.warn("No current user found.");
    }

    // Final icon check to ensure Lucide renders everything
    if (window.lucide) {
        lucide.createIcons();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

// --- ANNIVERSARY LOGIC ---
async function fetchCoupleInfo() {
    if (!currentUser) return;
    try {
        const res = await fetch(`${API_BASE_URL}/couple/info?couple_id=${currentUser.couple_id}`);
        if (res.ok) {
            const data = await res.json();
            if (data.start_date) {
                updateAnniversaryDisplay(data.start_date);
            }
        }
    } catch (err) {
        console.error("Failed to fetch couple info", err);
    }
}

function updateAnniversaryDisplay(startDateStr) {
    const dateText = document.getElementById('anniversary-date-text');
    const dDayText = document.getElementById('d-day-count');
    const calendarStartDateInput = document.getElementById('anniversary-start-date');

    if (dateText && dDayText) {
        // Format: YYYY.MM.DD
        const formattedDate = startDateStr.replace(/-/g, '.');
        dateText.textContent = `${formattedDate} ~`;

        // Calculate D-day
        const start = new Date(startDateStr);
        start.setHours(0, 0, 0, 0);
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const diffTime = today.getTime() - start.getTime();
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24)) + 1; // Start date is Day 1

        dDayText.textContent = `D+${diffDays}`;
    }

    if (calendarStartDateInput) {
        calendarStartDateInput.value = startDateStr;
    }
}

function toggleDateEdit() {
    const controls = document.getElementById('date-edit-controls');
    controls.classList.toggle('hidden');
}

async function saveStartDate() {
    const newDate = document.getElementById('new-start-date').value;
    if (!newDate) {
        alert("날짜를 선택해 주세요.");
        return;
    }

    try {
        const res = await fetch(`${API_BASE_URL}/couple/info?couple_id=${currentUser.couple_id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start_date: newDate })
        });

        if (res.ok) {
            updateAnniversaryDisplay(newDate);
            toggleDateEdit();
        }
    } catch (err) {
        console.error("Failed to save start date", err);
    }
}

let kakaoMap = null;
let kakaoMarker = null;

function initMapWithLocation(lat, lng) {
    const container = document.getElementById('kakao-map');
    const options = {
        center: new kakao.maps.LatLng(lat, lng),
        level: 3
    };

    if (!kakaoMap) {
        kakaoMap = new kakao.maps.Map(container, options);
        kakaoMarker = new kakao.maps.Marker({
            position: new kakao.maps.LatLng(lat, lng),
            map: kakaoMap
        });
    } else {
        const newPos = new kakao.maps.LatLng(lat, lng);
        kakaoMap.setCenter(newPos);
        kakaoMarker.setPosition(newPos);
    }
}

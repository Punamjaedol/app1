// Initialize icons
lucide.createIcons();

// const API_BASE_URL = 'http://127.0.0.1:8000/api';
const API_BASE_URL = 'http://localhost:8080';

// --- STATE MANAGEMENT ---
let appState = {
    places: [], // { id, name, address, timestamp }
    schedules: {}, // { 'YYYY-MM-DD': [{ id, title, time, placeId }] }
};

// --- DATA FETCHING (FASTAPI) ---
async function fetchTimeline() {
    try {
        const response = await fetch(`${API_BASE_URL}/timeline`);
        if (response.ok) {
            appState.places = await response.json();
            renderTimeline();
        }
    } catch (error) {
        console.error("Timeline fetch failed:", error);
    }
}

async function fetchSchedulesForDate(dateStr) {
    try {
        const response = await fetch(`${API_BASE_URL}/schedule/${dateStr}`);
        if (response.ok) {
            appState.schedules[dateStr] = await response.json();
            renderCalendar();
            renderSchedules();
        }
    } catch (error) {
        console.error("Schedule fetch failed:", error);
    }
}

// --- GPS POLLING LOGIC ---
let watchId = null;

function startGpsTracking() {
    const statusText = document.getElementById('gps-status-text');

    if ("geolocation" in navigator) {
        watchId = navigator.geolocation.watchPosition(
            async (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                statusText.textContent = `Tracking (${lat.toFixed(3)}, ${lng.toFixed(3)})...`;

                initMapWithLocation(lat, lng);

                try {
                    const res = await fetch(`${API_BASE_URL}/location`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ lat, lng })
                    });
                    const data = await res.json();

                    console.log("GPS Update:", data.message);

                    if (data.place_tagged) {
                        // Backend auto-tagged a place!
                        fetchTimeline(); // Refresh timeline
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
            { enableHighAccuracy: true, maximumAge: 0, timeout: 10000 }
        );
    } else {
        statusText.textContent = "Geolocation not supported.";
    }
}

async function deletePlace(placeId) {
    if (!confirm("Are you sure you want to delete this memory?")) return;
    try {
        const res = await fetch(`${API_BASE_URL}/places/${placeId}`, { method: "DELETE" });
        if (res.ok) {
            fetchTimeline();
        } else {
            alert("Failed to delete place.");
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

    // Empty cells
    for (let i = 0; i < firstDay; i++) {
        html += '<div class="calendar-day empty"></div>';
    }

    // Days (Only re-rendering structure)
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
        selectDate(`${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`);
    } else if (selectedDateStr) {
        renderSchedules();
    }
}

function changeMonth(delta) {
    currentDate.setMonth(currentDate.getMonth() + delta);
    renderCalendar();
}

function selectDate(dateStr) {
    selectedDateStr = dateStr;
    fetchSchedulesForDate(dateStr); // Fetch from API whenever we change daily view
}

function renderSchedules() {
    if (!selectedDateStr) return;

    const dateObj = new Date(selectedDateStr);
    document.getElementById('selected-date-title').textContent =
        dateObj.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

    const list = document.getElementById('schedule-list');
    const daySchedules = appState.schedules[selectedDateStr] || [];

    if (daySchedules.length === 0) {
        list.innerHTML = '<p class="empty-state" style="color: var(--text-muted); font-size: 14px; text-align: center; padding: 20px 0;">No schedules for this day.</p>';
        return;
    }

    list.innerHTML = daySchedules.map(s => {
        let placeHtml = '';
        if (s.placeId) {
            // Find in current state memory, fallback to just ID if not loaded
            const place = appState.places.find(p => p.id === s.placeId);
            const placeName = place ? place.name : "Saved Place";
            placeHtml = `<div style="font-size: 12px; color: var(--primary-color); display: flex; align-items: center; gap: 4px; margin-top: 4px;"><i data-lucide="map-pin"></i> ${placeName}</div>`;
        }

        return `
            <div style="background: rgba(255,255,255,0.8); border: 1px solid rgba(0,0,0,0.05); padding: 12px; border-radius: 12px; margin-bottom: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.02);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="font-weight: 600;">${s.title}</div>
                    <div style="font-size: 13px; color: var(--text-muted); background: rgba(0,0,0,0.05); padding: 2px 8px; border-radius: 10px;">${s.time || 'All day'}</div>
                </div>
                ${placeHtml}
            </div>
        `;
    }).join('');

    lucide.createIcons();
}

async function fetchMonthSchedules(year, month) {
    const yearMonth = `${year}-${String(month + 1).padStart(2, '0')}`;
    try {
        const res = await fetch(`${API_BASE_URL}/schedule/month/${yearMonth}`);
        const data = await res.json();
        // appState.schedules에 병합
        Object.assign(appState.schedules, data);
    } catch (err) {
        console.error("Failed to fetch month schedules", err);
    }
}

// --- MODAL & SCHEDULE ADDING ---
function openAddScheduleModal() {
    if (!selectedDateStr) {
        alert("Please select a date first.");
        return;
    }
    document.getElementById('schedule-title').value = '';
    document.getElementById('schedule-time').value = '';
    document.getElementById('modal-overlay').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
}

let pendingLinkedPlaceId = null;

function linkPlace() {
    if (appState.places.length === 0) {
        alert("You haven't generated any automated GPS memories yet!");
        return;
    }
    const recentPlace = appState.places[0];
    pendingLinkedPlaceId = recentPlace.id;
    document.getElementById('linked-place').textContent = recentPlace.name;
    document.getElementById('linked-place').style.color = 'var(--primary-color)';
}

async function saveSchedule() {
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
        const res = await fetch(`${API_BASE_URL}/schedule`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            // refresh data for today
            fetchSchedulesForDate(selectedDateStr);
            closeModal();
            pendingLinkedPlaceId = null;
            document.getElementById('linked-place').textContent = 'No place linked';
            document.getElementById('linked-place').style.color = 'var(--text-muted)';
        }
    } catch (e) {
        console.error("Failed to save schedule", e);
        alert("Server error saving schedule.");
    }
}

async function generateAnniversaries() {
    const startDate = document.getElementById('anniversary-start-date').value;
    if (!startDate) {
        alert("Please select a date first.");
        return;
    }

    try {
        const res = await fetch(`${API_BASE_URL}/anniversary`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ start_date: startDate })
        });

        if (res.ok) {
            const data = await res.json();
            alert(`Success! ${data.message}`);
            // Refresh current calendar view
            if (selectedDateStr) {
                fetchSchedulesForDate(selectedDateStr);
            } else {
                renderCalendar();
            }
        } else {
            alert("Failed to generate anniversaries.");
        }
    } catch (e) {
        console.error("Failed to call anniversary API", e);
        alert("Server error.");
    }
}

// --- INIT ---
document.addEventListener('DOMContentLoaded', () => {
    fetchTimeline();

    // We start automated background tracking right away
    kakao.maps.load(() => {
        startGpsTracking();
    });
});

let kakaoMap = null;
let kakaoMarker = null;

function initMapWithLocation(lat, lng) {
    const container = document.getElementById('kakao-map');
    const options = {
        center: new kakao.maps.LatLng(lat, lng),
        level: 3  // 줌 레벨 (숫자 낮을수록 확대)
    };

    if (!kakaoMap) {
        // 첫 로드: 지도 생성
        kakaoMap = new kakao.maps.Map(container, options);

        kakaoMarker = new kakao.maps.Marker({
            position: new kakao.maps.LatLng(lat, lng),
            map: kakaoMap
        });
    } else {
        // 위치 업데이트: 지도 중심 및 마커 이동
        const newPos = new kakao.maps.LatLng(lat, lng);
        kakaoMap.setCenter(newPos);
        kakaoMarker.setPosition(newPos);
    }
}

// 기존 GPS 감지 코드에 연결
navigator.geolocation.watchPosition(
    (position) => {
        const { latitude, longitude } = position.coords;

        document.getElementById('gps-status-text').textContent =
            `📍 ${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;

        initMapWithLocation(latitude, longitude);
    },
    (error) => {
        document.getElementById('gps-status-text').textContent =
            '위치를 가져올 수 없습니다: ' + error.message;
    },
    { enableHighAccuracy: true, maximumAge: 5000 }
);
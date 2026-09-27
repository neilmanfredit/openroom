const roomNameEl = document.getElementById('room-name');
const clockEl = document.getElementById('clock');
const listEl = document.getElementById('meeting-list');
const offlineEl = document.getElementById('offline-indicator');

function tickClock() {
  clockEl.textContent = new Date().toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function renderMeetings(meetings) {
  listEl.innerHTML = '';
  if (!meetings.length) {
    const li = document.createElement('li');
    li.textContent = 'No meetings today';
    listEl.appendChild(li);
    return;
  }
  for (const meeting of meetings) {
    const li = document.createElement('li');
    const label = document.createElement('span');
    label.textContent = meeting.subject;
    li.appendChild(label);
    if (meeting.join_url_available) {
      const button = document.createElement('button');
      button.className = 'join-button';
      button.type = 'button';
      button.textContent = 'Join';
      button.addEventListener('click', () => joinMeeting(meeting.id));
      li.appendChild(button);
    }
    listEl.appendChild(li);
  }
  const first = listEl.querySelector('.join-button');
  if (first) first.focus();
}

async function refreshMeetings() {
  try {
    const resp = await fetch('/api/today');
    if (!resp.ok) throw new Error('bad response');
    const data = await resp.json();
    offlineEl.hidden = true;
    roomNameEl.textContent = data.room_name;
    renderMeetings(data.meetings);
  } catch (err) {
    offlineEl.hidden = false;
  }
}

async function joinMeeting(id) {
  await fetch(`/api/join/${encodeURIComponent(id)}`, { method: 'POST' });
}

// USB numeric keypad / presenter remote support: arrow keys move focus
// between Join buttons, Enter/Space activate the focused one (handled
// natively by <button>).
function handleArrowNav(event) {
  const buttons = Array.from(document.querySelectorAll('.join-button'));
  if (!buttons.length) return;
  const currentIndex = buttons.indexOf(document.activeElement);
  if (event.key === 'ArrowDown' || event.key === 'ArrowRight') {
    event.preventDefault();
    buttons[(currentIndex + 1 + buttons.length) % buttons.length].focus();
  } else if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') {
    event.preventDefault();
    buttons[(currentIndex - 1 + buttons.length) % buttons.length].focus();
  }
}

document.addEventListener('keydown', handleArrowNav);

tickClock();
setInterval(tickClock, 1000);
refreshMeetings();
setInterval(refreshMeetings, 60000);

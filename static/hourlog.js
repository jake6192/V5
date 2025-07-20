
// hourlog.js — Fully backend-integrated version with ALL original UI functionality preserved
// Locked in architect mode

function showToast(msg) {
  const toast = document.createElement("div");
  toast.textContent = msg;
  toast.style.position = "fixed";
  toast.style.bottom = "20px";
  toast.style.left = "50%";
  toast.style.transform = "translateX(-50%)";
  toast.style.background = "#28a745";
  toast.style.color = "#fff";
  toast.style.padding = "0.75rem 1.5rem";
  toast.style.borderRadius = "5px";
  toast.style.fontWeight = "bold";
  toast.style.zIndex = "9999";
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2000);
}

document.addEventListener("DOMContentLoaded", () => {
  const PIN_CODE = "1234";
  let allShifts = [];
  let currentSort = { column: null, ascending: true };
  let isPinModalOpen = false;

  // Elements
  const staffSelect = document.getElementById("staffSelect");
  const dateInput = document.getElementById("date");
  const startTimeInput = document.getElementById("startTime");
  const endTimeInput = document.getElementById("endTime");
  const venueSelect = document.getElementById("venueSelect");
  const notesInput = document.getElementById("notes");
  const logShiftBtn = document.getElementById("logShift");

  const tableBody = document.querySelector("#logTable tbody");
  const totalHoursEl = document.getElementById("totalHours");
  const rangeStart = document.getElementById("rangeStart");
  const rangeEnd = document.getElementById("rangeEnd");
  const quickButtons = document.querySelectorAll(".quick-buttons button");

  const filterStaff = document.getElementById("filterStaff");
  const filterVenue = document.getElementById("filterVenue");

  const cumulativeStaff = document.getElementById("cumulativeStaff");
  const startRange = document.getElementById("startRange");
  const endRange = document.getElementById("endRange");
  const calculateBtn = document.getElementById("calculateHours");
  const cumulativeResult = document.getElementById("cumulativeResult");

  const triggerPinBtn = document.getElementById("triggerPin");
  const pinModal = document.getElementById("pinModal");
  const pinInput = document.getElementById("pinInput");
  const submitPin = document.getElementById("submitPin");
  const pinError = document.getElementById("pinError");
  const dataSection = document.getElementById("dataSection");

  const darkToggle = document.getElementById("darkModeToggle");
  const clearLogsBtn = document.getElementById("clearLogs");
  const printBtn = document.getElementById("printTable");
  const exportCSVBtn = document.getElementById("exportCSV");

  // === Live filtering hooks ===
  filterStaff.addEventListener("change", renderTable);
  filterVenue.addEventListener("change", renderTable);
  rangeStart.addEventListener("input", renderTable);
  rangeEnd.addEventListener("input", renderTable);
  
  // Dark mode state
  if (localStorage.getItem("darkMode") === "true") {
    document.documentElement.classList.add("dark");
    darkToggle.checked = true;
  }
  darkToggle.addEventListener("change", () => {
    document.documentElement.classList.toggle("dark", darkToggle.checked);
    localStorage.setItem("darkMode", darkToggle.checked);
  });
  
  // Loading overlay
  function showOverlay() {
    document.getElementById("loadingOverlay").style.display = "flex";
  }
  function hideOverlay() {
    document.getElementById("loadingOverlay").style.display = "none";
  }

  // === Backend replacement ===
  async function loadShifts() {
    showOverlay();
    const res = await fetch("/api/shifts");
    let data = await res.json();
    if (!Array.isArray(data)) {
      console.error("Invalid shift data:", data);
      data = [];  // Prevent UI crash
    }
    allShifts = data;
    renderTable();
    updateFilterOptions();
    hideOverlay();
  }

  async function saveShifts() {
    await loadShifts();  // Re-fetch after post/delete
    renderTable();
    updateFilterOptions();
  }

  async function deleteShift(id) {
    if(confirm("Are you sure you would like to delete this shift?\n\nThis action cannot be undone.")) {
      showOverlay();
      await fetch(`/api/shifts/${id}`, { method: "DELETE" });
      saveShifts();
      hideOverlay();
    }
  }
  window.deleteShift = deleteShift;

  // === Modified postShift ===
  async function postShift(payload) {
    await fetch("/api/shifts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    await loadShifts();   // refresh
    hideOverlay();
    showToast("✅ Shift logged successfully");
  }

  async function lookupCumulative(staff, start, end) {
    const res = await fetch(`/api/shifts/cumulative?staff=${staff}&start=${start}&end=${end}`);
    return await res.json();
  }

  // UI Functions
  function calculateHours(start, end) {
    const [sh, sm] = start.split(":").map(Number);
    const [eh, em] = end.split(":").map(Number);
    return ((eh * 60 + em - sh * 60 - sm) / 60).toFixed(2);
  }

  function formatDate(isoDate) {
    const [yyyy, mm, dd] = isoDate.split("-");
    return `${dd}-${mm}-${yyyy}`;
  }

  function isWithinDateRange(dateStr) {
    if (!rangeStart.value && !rangeEnd.value) return true;
    const target = new Date(dateStr);
    const start = rangeStart.value ? new Date(rangeStart.value) : null;
    const end = rangeEnd.value ? new Date(rangeEnd.value) : null;
    if (start && target < start) return false;
    if (end && target > end) return false;
    return true;
  }

  function renderTable() {
    const staffVal = filterStaff.value;
	  const venueVal = filterVenue.value;
    const filtered = allShifts.filter(s =>
      (staffVal === "All" || s.staff === staffVal) && (venueVal === "All" || s.venue === venueVal) &&
      isWithinDateRange(s.date)
    );

    if (currentSort.column) {
      filtered.sort((a, b) => {
        let valA = a[currentSort.column];
        let valB = b[currentSort.column];
        if (currentSort.column === "hours") {
          valA = parseFloat(valA);
          valB = parseFloat(valB);
        }
        if (valA < valB) return currentSort.ascending ? -1 : 1;
        if (valA > valB) return currentSort.ascending ? 1 : -1;
        return 0;
      });
    }

    tableBody.innerHTML = "";
    let total = 0;
    filtered.forEach(s => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${s.staff}</td>
        <td>${formatDate(s.date)}</td>
        <td>${s.start}</td>
        <td>${s.end}</td>
        <td>${s.venue}</td>
        <td>${s.hours.toFixed(2)}</td>
        <td>${s.notes || ""}</td>
        <td><button onclick="deleteShift(${s.id})">🗑</button></td>`;
      total += parseFloat(s.hours);
      tableBody.appendChild(tr);
    });
    totalHoursEl.textContent = "Total Hours: " + (total||0).toFixed(2);
  }

  function updateFilterOptions() {
    const uniqueStaff = [...new Set(allShifts.map(s => s.staff))];
    const uniqueVenues = [...new Set(allShifts.map(s => s.venue))];
    [filterStaff, cumulativeStaff].forEach(select => {
      const current = select.value;
      select.innerHTML = `<option value="All">All</option>`;
      uniqueStaff.forEach(name => {
        const opt = document.createElement("option");
        opt.value = opt.textContent = name;
        select.appendChild(opt);
      });
      if (current) select.value = current;
    });
    filterVenue.innerHTML = `<option value="All">All</option>`;
	  uniqueVenues.forEach(v => {
      const opt = document.createElement("option");
      opt.value = opt.textContent = v;
      filterVenue.appendChild(opt);
	  });
  }

  logShiftBtn.addEventListener("click", () => {
    const staff = staffSelect.value;
    const date = dateInput.value;
    const start = startTimeInput.value;
    const end = endTimeInput.value;
    const venue = venueSelect.value;
    const notes = notesInput.value;
    if (!staff || !date || !start || !end || !venue) {
      alert("Please fill in all required fields.");
      return;
    }
    if(staff == "null") {
      alert("Select a staff member.");
      return;
    }
    if(venue == "null") {
      alert("Select a venue.");
      return;
    }
    const hours = calculateHours(start, end);
    if (hours <= 0) {
      alert("End time must be after start time.");
      return;
    }
    showOverlay();
    postShift({ staff, date, start, end, venue, notes, hours });
  });

  calculateBtn.addEventListener("click", async () => {
    showOverlay();
    const staff = cumulativeStaff.value;
    const start = startRange.value;
    const end = endRange.value;
    if (!staff || !start || !end) {
      alert("Please select staff and date range.");
      return;
    }
    const data = await lookupCumulative(staff, start, end);
    cumulativeResult.textContent = `${staff} worked ${parseFloat(data.total || 0).toFixed(2)} hours from ${start} to ${end}.`;
    hideOverlay();
  });

  document.querySelectorAll(".sortable").forEach(th => {
    const colMap = {
      sortStaff: "staff",
      sortVenue: "venue",
      sortHours: "hours"
    };
    const col = colMap[th.id];
    if (!col) return;
    th.addEventListener("click", () => {
      if (currentSort.column === col) {
        currentSort.ascending = !currentSort.ascending;
      } else {
        currentSort.column = col;
        currentSort.ascending = true;
      }
      renderTable();
    });
  });

  triggerPinBtn.addEventListener("click", () => {
    pinModal.style.display = "flex";
    setTimeout(() => {
      isPinModalOpen = true;
      pinInput.focus();
    }, 0);
  });

  submitPin.addEventListener("click", () => {
    if (pinInput.value === PIN_CODE) {
      pinModal.style.display = "none";
      isPinModalOpen = false;
      dataSection.style.display = "block";
      triggerPinBtn.style.display = "none";
      loadShifts();
    } else {
      pinError.textContent = "Incorrect PIN.";
      pinModal.querySelector(".modal-content").classList.add("shake");
      setTimeout(() => pinModal.querySelector(".modal-content").classList.remove("shake"), 500);
    }
  });

  pinInput.addEventListener("keydown", e => {
    if (e.key === "Enter") submitPin.click();
  });

  window.addEventListener("click", e => {
    if (isPinModalOpen && !pinModal.querySelector(".modal-content").contains(e.target)) {
      pinModal.style.display = "none";
      pinInput.value = "";
      pinError.innerText = "";
      isPinModalOpen = false;
    }
  });

  clearLogsBtn.addEventListener("click", async() => {
    if(confirm("This will delete all logs from the database.\n\nThis action is irreversible, are you sure you want to do this?")) {
      showOverlay();
      await fetch("/api/shifts", { method: "DELETE" });
      await loadShifts();
      hideOverlay();
      showToast("🗑️ All logs deleted");
    }
  });
  printBtn.addEventListener("click", () => window.print());

  exportCSVBtn.addEventListener("click", () => {
    const rows = [["Staff", "Date", "Start", "End", "Venue", "Hours", "Notes"]];
    allShifts.forEach(s => {
      rows.push([s.staff, s.date, s.start, s.end, s.venue, s.hours, s.notes || ""]);
    });
    const csv = rows.map(r => r.map(v => `"${v}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "KingsLangley_Staff_Hours.csv";
    a.click();
    URL.revokeObjectURL(url);
  });

  quickButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const today = new Date();
      const toDate = d => d.toISOString().slice(0, 10);
      const past = new Date(today);
      let start = "", end = toDate(today);
      switch (btn.dataset.range) {
        case "today": start = end; break;
        case "24h": past.setDate(today.getDate() - 1); start = toDate(past); break;
        case "7d": past.setDate(today.getDate() - 7); start = toDate(past); break;
        case "1m": past.setMonth(today.getMonth() - 1); start = toDate(past); break;
        case "1y": past.setFullYear(today.getFullYear() - 1); start = toDate(past); break;
        case "all": start = end = ""; break;
      }
      rangeStart.value = start;
      rangeEnd.value = end;
      renderTable();
    });
  });

  // Calendar/Time Picker init
  const calendarGrid = document.getElementById("calendarGrid");
  const calendarMonth = document.getElementById("calendarMonth");
  let selectedDate = new Date();

  function renderCalendar(date) {
    calendarGrid.innerHTML = "";
    const year = date.getFullYear();
    const month = date.getMonth();
    calendarMonth.textContent = date.toLocaleDateString('default', { month: 'long', year: 'numeric' });
    const start = new Date(year, month, 1);
    const end = new Date(year, month + 1, 0);
    const offset = start.getDay();

    for (let i = 0; i < offset; i++) calendarGrid.appendChild(document.createElement("div"));
    for (let d = 1; d <= end.getDate(); d++) {
      const day = document.createElement("div");
      day.textContent = d;
      const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      day.dataset.date = dateStr;
      if (dateStr === new Date().toISOString().slice(0, 10)) day.classList.add("today");
      if (dateStr === dateInput.value) day.classList.add("selected");
      day.addEventListener("click", () => {
        dateInput.value = dateStr
        renderCalendar(new Date(dateStr));
      });
      calendarGrid.appendChild(day);
    }
  }

  document.getElementById("prevMonth").onclick = () => {
    selectedDate.setMonth(selectedDate.getMonth() - 1);
    renderCalendar(selectedDate);
  };
  document.getElementById("nextMonth").onclick = () => {
    selectedDate.setMonth(selectedDate.getMonth() + 1);
    renderCalendar(selectedDate);
  };

  function roundToPrevious15(date = new Date()) {
    const minutes = date.getMinutes();
    const rounded = minutes - (minutes % 15);
    date.setMinutes(rounded, 0, 0);
    return date;
  }

  function formatTime(d) {
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  }

  function updateTimeDisplays() {
    document.getElementById("startTimeDisplay").textContent = formatTime(startTime);
    document.getElementById("endTimeDisplay").textContent = formatTime(endTime);
    document.getElementById("startTime").value = formatTime(startTime);
    document.getElementById("endTime").value = formatTime(endTime);
  }

  let endTime = roundToPrevious15(new Date());
  let startTime = new Date(endTime.getTime() - 5 * 60 * 60 * 1000);

  document.querySelectorAll(".time-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const isStart = btn.dataset.type === "start";
      const direction = btn.dataset.op === "up" ? 1 : -1;
      const delta = direction * 15 * 60 * 1000;
      if (isStart) startTime = new Date(startTime.getTime() + delta);
      else endTime = new Date(endTime.getTime() + delta);
      updateTimeDisplays();
    });
  });

  document.querySelectorAll(".time-editable").forEach(wrapper => {
    const type = wrapper.dataset.type;
    const display = wrapper.querySelector("span");
    const input = wrapper.querySelector("input");
    display.addEventListener("click", () => {
      input.value = display.textContent;
      display.style.display = "none";
      input.style.display = "inline-block";
      input.focus();
    });
    input.addEventListener("blur", applyTimeInput);
    input.addEventListener("keydown", e => {
      if (e.key === "Enter") applyTimeInput.call(input);
    });
    function applyTimeInput() {
      const [hh, mm] = this.value.split(":").map(Number);
      const t = new Date();
      t.setHours(hh, mm, 0, 0);
      if (type === "start") startTime = t;
      else endTime = t;
      updateTimeDisplays();
      this.style.display = "none";
      display.style.display = "inline-block";
    }
  });
  
  const todayStr = new Date().toISOString().slice(0, 10);
  dateInput.value = todayStr;
  renderCalendar(new Date());
  updateTimeDisplays();
});

// Elements
	const staffSelect = document.getElementById("staffSelect");
	const dateInput = document.getElementById("date");
	const startTimeInput = document.getElementById("startTime");
	const endTimeInput = document.getElementById("endTime");
	//const venueSelect = document.getElementById("venue");
	const notesInput = document.getElementById("notes");
	const logShiftBtn = document.getElementById("logShift");
	const tableBody = document.querySelector("#logTable tbody");
	const totalHoursEl = document.getElementById("totalHours");
	const rangeStart = document.getElementById("rangeStart");
	const rangeEnd = document.getElementById("rangeEnd");
	const quickButtons = document.querySelectorAll(".quick-buttons button");

	const filterStaff = document.getElementById("filterStaff");
	//const filterVenue = document.getElementById("filterVenue");

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
	const printBtn = document.getElementById("printTable");
	const exportCSVBtn = document.getElementById("exportCSV");

	// State
	let shifts = JSON.parse(localStorage.getItem("shifts") || "[]");
	let backupTimer = null;
	let currentSort = { column: null, ascending: true };
	let isPinModalOpen = false;
	const PIN_CODE = "1234";

	// Setup theme
	if (localStorage.getItem("darkMode") === "true") {
	  document.documentElement.classList.add("dark");
	  darkToggle.checked = true;
	}
	darkToggle.addEventListener("change", () => {
	  document.documentElement.classList.toggle("dark", darkToggle.checked);
	  localStorage.setItem("darkMode", darkToggle.checked);
	});

	function calculateHours(start, end) {
	  const [sh, sm] = start.split(":").map(Number);
	  const [eh, em] = end.split(":").map(Number);
	  return ((eh * 60 + em - sh * 60 - sm) / 60).toFixed(2);
	}

	function saveShifts() {
	  localStorage.setItem("shifts", JSON.stringify(shifts));
	  triggerBackupDebounced();
	  renderTable();
	  updateFilterOptions();
	}

	function deleteShift(index) {
	  shifts.splice(index, 1);
	  saveShifts();
	}

	function triggerBackupDebounced() {
	  clearTimeout(backupTimer);
	  backupTimer = setTimeout(triggerBackupDownload, 20000);
	}

	function triggerBackupDownload() {/* CURRENTLY DISABLED  - REMOVE COMMENTS TO ENEBLE AUTO BACKUPS
	  const blob = new Blob([JSON.stringify(shifts, null, 2)], { type: "application/json" });
	  const url = URL.createObjectURL(blob);
	  const a = document.createElement("a");
	  a.href = url;
	  a.download = "staff_hours_backup.json";
	  a.click();
	  URL.revokeObjectURL(url);
	*/}
	
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
	  //const venueVal = filterVenue.value;

	  let filtered = shifts.filter(s =>
		//(staffVal === "All" || s.staff === staffVal) && (venueVal === "All" || s.venue === venueVal) &&
		(staffVal === "All" || s.staff === staffVal) &&
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
	  filtered.forEach((s, i) => {
		const tr = document.createElement("tr");
		tr.innerHTML = `
		  <td>${s.staff}</td>
		  <td>${formatDate(s.date)}</td>
		  <td>${s.start}</td>
		  <td>${s.end}</td>
		  <!-- <td>${s.venue}</td> -->
		  <td>${s.hours}</td>
		  <td>${s.notes || ""}</td>
		  <td><button onclick="deleteShift(${shifts.indexOf(s)})">🗑</button></td>
		`;
		total += parseFloat(s.hours);
		tableBody.appendChild(tr);
	  });
	  totalHoursEl.textContent = "Total Hours: " + total.toFixed(2);
	}

	function updateFilterOptions() {
	  const uniqueStaff = [...new Set(shifts.map(s => s.staff))];
	  //const uniqueVenues = [...new Set(shifts.map(s => s.venue))];

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

	  /*filterVenue.innerHTML = `<option value="All">All</option>`;
	  uniqueVenues.forEach(v => {
		const opt = document.createElement("option");
		opt.value = opt.textContent = v;
		filterVenue.appendChild(opt);
	  });*/
	}

	logShiftBtn.addEventListener("click", () => {
	  const staff = staffSelect.value;
	  const date = dateInput.value;
	  const start = startTimeInput.value;
	  const end = endTimeInput.value;
	  //const venue = venueSelect.value;
	  const notes = notesInput.value;

	  //if (!staff || !date || !start || !end || !venue) {
	  if (!staff || !date || !start || !end) {
		alert("Please fill in all required fields.");
		return;
	  }

	  const hours = calculateHours(start, end);
	  if (hours <= 0) {
		alert("End time must be after start time.");
		return;
	  }

	  //shifts.push({ staff, date, start, end, venue, notes, hours });
	  shifts.push({ staff, date, start, end, notes, hours });
	  saveShifts();

    // Reset to defaults
    endTime = roundToPrevious15(new Date());
    startTime = new Date(endTime.getTime() - 5 * 60 * 60 * 1000);
    updateTimeDisplays();

    const todayStr = new Date().toISOString().slice(0, 10);
    dateInput.value = todayStr;
    renderCalendar(new Date());

    // Clear other fields
    staffSelect.selectedIndex = 0;
	  //venueSelect.selectedIndex = 0;
    notesInput.value = "";

    // Show toast
    showToast("✅ Shift logged successfully");
	});

	document.querySelectorAll(".sortable").forEach(th => {
	  th.addEventListener("click", () => {
		const colMap = {
		  sortStaff: "staff",
		  //sortVenue: "venue",
		  sortHours: "hours"
		};
		const col = colMap[th.id];
		if (currentSort.column === col) {
		  currentSort.ascending = !currentSort.ascending;
		} else {
		  currentSort.column = col;
		  currentSort.ascending = true;
		}
		renderTable();
	  });
	});

	filterStaff.addEventListener("change", renderTable);
	//filterVenue.addEventListener("change", renderTable);

	calculateBtn.addEventListener("click", () => {
	  const staff = cumulativeStaff.value;
	  const start = startRange.value;
	  const end = endRange.value;
	  if (!staff || !start || !end) {
		alert("Please select staff and date range.");
		return;
	  }

	  const total = shifts
		.filter(s => s.staff === staff && s.date >= start && s.date <= end)
		.reduce((sum, s) => sum + parseFloat(s.hours), 0);

	  cumulativeResult.textContent = `${staff} worked ${total.toFixed(2)} hours from ${start} to ${end}.`;
	});

	// PIN Unlock
	triggerPinBtn.addEventListener("click", () => {
	  pinModal.style.display = "flex";
	  setTimeout(() => {
		isPinModalOpen = true;
		pinInput.focus();
	  }, 0); // next tick
	});

	submitPin.addEventListener("click", () => {
	  if (pinInput.value === PIN_CODE) {
		pinModal.style.display = "none";
		isPinModalOpen = false;
		dataSection.style.display = "block";
		triggerPinBtn.style.display = "none";
		renderTable();
		updateFilterOptions();
	  } else {
		pinError.textContent = "Incorrect PIN.";
		pinModal.querySelector(".modal-content").classList.add("shake");
		setTimeout(() => {
		  pinModal.querySelector(".modal-content").classList.remove("shake");
		}, 500);
	  }
	});
	
	pinInput.addEventListener("keydown", e => {
	  if(e.key === "Enter") submitPin.click();
	});

	// Print/export
	printBtn.addEventListener("click", () => {
	  window.print();
	});

	exportCSVBtn.addEventListener("click", () => {
	  const staffVal = filterStaff.value;
	  //const venueVal = filterVenue.value;

	  let filtered = shifts.filter(s => 
		//(staffVal === "All" || s.staff === staffVal) && (venueVal === "All" || s.venue === venueVal)
		(staffVal === "All" || s.staff === staffVal)
	  );

	  const rows = [
		//["Staff", "Date", "Start", "End", "Venue", "Hours", "Notes"],
		["Staff", "Date", "Start", "End", "Hours", "Notes"],
		//...filtered.map(s => [s.staff, s.date, s.start, s.end, s.venue, s.hours, s.notes || ""])
		...filtered.map(s => [s.staff, s.date, s.start, s.end, s.hours, s.notes || ""])
	  ];

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
		const range = btn.dataset.range;
		let start = "", end = "";

		if (range === "all") {
		  rangeStart.value = "";
		  rangeEnd.value = "";
		} else {
		  const toISOStringDate = d => d.toISOString().slice(0, 10);
		  end = toISOStringDate(today);
		  let past = new Date(today);

		  if (range === "today") {
			start = toISOStringDate(today);
		  } else if (range === "24h") {
			past.setDate(today.getDate() - 1);
			start = toISOStringDate(past);
		  } else if (range === "7d") {
			past.setDate(today.getDate() - 7);
			start = toISOStringDate(past);
		  } else if (range === "1m") {
			past.setMonth(today.getMonth() - 1);
			start = toISOStringDate(past);
		  } else if (range === "1y") {
			past.setFullYear(today.getFullYear() - 1);
			start = toISOStringDate(past);
		  }

		  rangeStart.value = start;
		  rangeEnd.value = end;
		}

		renderTable();
	  });
	});

	rangeStart.addEventListener("change", renderTable);
	rangeEnd.addEventListener("change", renderTable);
	
	// Close modal when clicking outside
	window.addEventListener("click", (e) => {
	  if (
		isPinModalOpen &&
		!pinModal.querySelector(".modal-content").contains(e.target)
	  ) {
		pinModal.style.display = "none";
		document.getElementById('pinInput').value = '';
		document.getElementById('pinError').innerText = '';
		isPinModalOpen = false;
	  }
	});
	
	// ===== Date/Time Picker Logic =====
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

	  for (let i = 0; i < offset; i++) {
		calendarGrid.appendChild(document.createElement("div"));
	  }

	  for (let d = 1; d <= end.getDate(); d++) {
		const day = document.createElement("div");
		day.textContent = d;
		const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
		day.dataset.date = dateStr;

		if (dateStr === new Date().toISOString().slice(0, 10)) {
		  day.classList.add("today");
		}
		if (dateStr === dateInput.value) {
		  day.classList.add("selected");
		}

		day.addEventListener("click", () => {
		  dateInput.value = dateStr;
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
  
  function showToast(message) {
    const toast = document.createElement("div");
    toast.textContent = message;
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
    toast.style.boxShadow = "0 4px 10px rgba(0,0,0,0.2)";
    toast.style.transition = "opacity 0.5s ease";
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 500);
    }, 2000);
  }

	// Time increment handlers
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
  let startTime = new Date(endTime.getTime() - 5 * 60 * 60 * 1000); // -5h default

  document.querySelectorAll(".time-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const isStart = btn.dataset.type === "start";
      const direction = btn.dataset.op === "up" ? 1 : -1;
      const delta = direction * 15 * 60 * 1000;

      if (isStart) {
        startTime = new Date(startTime.getTime() + delta);
      } else {
        endTime = new Date(endTime.getTime() + delta);
      }

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
      if (e.key === "Enter") {
        applyTimeInput.call(input);
      }
    });

    function applyTimeInput() {
      const [hh, mm] = this.value.split(":").map(Number);
      const targetTime = new Date();
      targetTime.setHours(hh);
      targetTime.setMinutes(mm);
      targetTime.setSeconds(0);
      targetTime.setMilliseconds(0);

      if (type === "start") startTime = targetTime;
      else endTime = targetTime;

      updateTimeDisplays();
      this.style.display = "none";
      display.style.display = "inline-block";
    }
  });

	// Init on load
  document.addEventListener("DOMContentLoaded", () => {
    const dateInput = document.getElementById("date");
    const startTimeInput = document.getElementById("startTime");
    const endTimeInput = document.getElementById("endTime");

    if (dateInput && startTimeInput && endTimeInput) {
      const todayStr = new Date().toISOString().slice(0, 10);
      dateInput.value = todayStr;

      renderCalendar(new Date());
      updateTimeDisplays();
    } else {
      console.warn("Required time/date input(s) missing in DOM.");
    }
  });

	// Initialize
	updateFilterOptions();
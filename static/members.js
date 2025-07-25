// static/members.js

$(document).ready(function () {
	let currentTierId = null,
	    currentMember = null,
	    modalStack = [],
	    showUnlimited = !0;

	// helper: show/hide any <li> whose .reset-period text is "Unlimited"
	function applyUnlimitedFilter(){
		$('li').has('.reset-period:contains("Unlimited")').each(function(){
			$(this).toggle(!showUnlimited);
		});
	}
	// toggle listener for both checkboxes
	$('#toggleUnlimitedMember,#toggleUnlimitedTier').on('change',function(){
		showUnlimited=$(this).is(':checked');
		$('#toggleUnlimitedMember,#toggleUnlimitedTier').prop('checked',showUnlimited);
		applyUnlimitedFilter();
	});

	// ========== MODAL HANDLERS ==========
	function openModal(id) {
		$(`#${id}`).show();
		modalStack.push(id);
		if(id==='perksModal'||id==='tierPerksModal'){
			$('#toggleUnlimitedMember,#toggleUnlimitedTier').prop('checked',showUnlimited);
			applyUnlimitedFilter();
		}
	}

	function closeTopModal() {
		const id = modalStack.pop();
		if(id) $(`#${id}`).hide();
	}

	$('.close').on('click', function () {
		closeTopModal();
	});

	window.onclick = function (event) {
		if($(event.target).hasClass('modal')) closeTopModal();
	};

	// ========== MEMBERS ==========
	let allMembers = [];

	function loadMembers() {
		$.get('/api/members', function (members) {
			allMembers = members; // Keep a copy for searching
			renderMemberTable(members);
		});
	}

	function renderMemberTable(members) {
		const tbody = $('#membersTable tbody').empty();
		members.forEach(m => {
			const row = `<tr>
				<td>${m.member_id}</td>
				<td>${m.location}</td>
				<td><span class="tier-badge" style="background-color:${m.color || '#888'}">${m.tier_name}</span></td>
				<td>${m.name}</td>
				<td>
					<button class="viewPerksBtn" data-id="${m.member_id}">Claim Perks</button>
					<button class="btn-edit editMemberBtn" data-id="${encodeURI(JSON.stringify(m))}">Edit</button>
					<button class="btn-delete deleteMemberBtn" data-id="${m.member_id}">Delete</button>
				</td>
			</tr>`;
			tbody.append(row);
		});
	}

	// Filter table as you type
	$('#memberSearch').on('input', function () {
		const term = $(this).val().toLowerCase();
		if (!term) {
			renderMemberTable(allMembers);
			return;
		}
		const filtered = allMembers.filter(m =>
			(m.member_id + '').toLowerCase().includes(term) ||
			(m.name || '').toLowerCase().includes(term) ||
			(m.location || '').toLowerCase().includes(term) ||
			(m.tier_name || '').toLowerCase().includes(term)
		);
		renderMemberTable(filtered);
	});

	$('#addMemberBtn').click(() => {
		$('#memberModalTitle').text('Add Member');
		$('#memberModal input').val('');
		// DEFAULT TIER & LOCATION - Currently set to 'Casual Golfer' & 'Kings Langley' //
		loadTiersIntoSelect('new', '#tierField', null, ()=>{
			$('#locationField option[value="Kings Langley"]').prop('selected', true);
			$('#tierField option[value="2"]').prop('selected', true);
			openModal('memberModal');
		});
	});

	$(document).on('click', '.editMemberBtn', function () {
		const data = JSON.parse(decodeURI($(this).attr('data-id')));
		$('#memberModalTitle').text('Edit Member');
		$('#memberIdInput').val(data.id);
		$('#memberIdField').val(data.member_id);
		$('#locationField').val(data.location);
		$('#nameField').val(data.name);
		$('#signUpDateField').val(data.sign_up_date);
		$('#dobField').val(data.date_of_birth);
		loadTiersIntoSelect('edit', '#tierField', data.tier_id);
		openModal('memberModal');
	});

	$('#saveMemberBtn').click(() => {
		const member_id = $('#memberIdField').val();
		const name = $('#nameField').val();
		const location = $('#locationField').val();
		const tier_id = $('#tierField').val();
		const sign_up_date = $('#signUpDateField').val();
		const date_of_birth = $('#dobField').val();

		// 1. Check member_id is numeric
		if(!/^\d+$/.test(member_id) || parseInt(member_id) === 0) {
			alert("Member ID must be a number greater than 0.");
			return;
		}
		// 2. Check required fields
		if(!member_id || !name || !tier_id || !sign_up_date) {
			alert("Please fill in all fields except Date of Birth.");
			return;
		}

		const member = {
		id: $('#memberIdInput').val(),
			member_id: member_id,
			name: name,
			location: location,
			tier_id: tier_id,
			sign_up_date: sign_up_date,
			date_of_birth: date_of_birth
		};
		$.ajax({
			url: '/api/members',
			type: 'POST',
			data: JSON.stringify(member),
			contentType: 'application/json',
			success: () => {
				closeTopModal();
				loadMembers();
			},
			error: function (xhr) {
				// 1. Unique member ID error
				if(xhr.status === 409 || (xhr.responseText && xhr.responseText.includes('UNIQUE constraint failed')))
					alert("Member ID must be unique.");
				else alert("Failed to save member. Please try again.");
			}
		});
	});

	$(document).on('click', '.deleteMemberBtn', function () {
		const id = $(this).data('id');
		if(confirm('Delete this member?'))
			$.ajax({ url: `/api/members/${id}`, type: 'DELETE' }).done(loadMembers);
	});

	// ========== TIERS ==========
	let allTiers = [];

	$('#manageTiersBtn').click(() => {
		loadTiers();
		openModal('tiersModal');
	});

	function loadTiers() {
		$.get('/api/tiers', tiers => {
			allTiers = tiers;
			const ul = $('#tiersList').empty();
			tiers.forEach(t => {
				ul.append(`<li>
					<span class="tier-badge" style="background-color:${t.color}">${t.name}</span>
					<span class="tier-actions">
						<button class="manageTierPerksBtn" data-id="${t.id}">Manage Perks</button>
						<button class="btn-edit editTierBtn" data-id='${JSON.stringify(t)}'>Edit Tier</button>
						<button class="btn-delete deleteTierBtn" data-id="${t.id}">Delete Tier</button>
					</span>
				</li>`);
			});
			loadMembers();
		});
	}

	$('#createTierBtn').click(() => {
		$('#tierModalTitle').text('Create Tier');
		$('#tierIdInput').val('');
		$('#tierNameField').val('');
		$('#tierColorField').val('#000000');
		openModal('tierModal');
	});

	$(document).on('click', '.editTierBtn', function () {
		const t = JSON.parse($(this).attr('data-id'));
		$('#tierModalTitle').text('Edit Tier');
		$('#tierIdInput').val(t.id);
		$('#tierNameField').val(t.name);
		$('#tierColorField').val(t.color);
		openModal('tierModal');
	});

	$('#saveTierBtn').click(() => {
		const tier = {
			id: $('#tierIdInput').val(),
			name: $('#tierNameField').val(),
			color: $('#tierColorField').val()
		};
		$.ajax({
			url: '/api/tiers',
			type: 'POST',
			data: JSON.stringify(tier),
			contentType: 'application/json',
			success: () => {
				closeTopModal();
				loadTiers();
			},
			error: function (xhr) {
				// If unique constraint or duplicate error
				if(xhr.status === 409 || (xhr.responseText && xhr.responseText.includes('UNIQUE constraint failed')))
					alert("Tier name must be unique.");
				else alert("Failed to save tier. Please try again.");
			}
		});
	});

	$(document).on('click', '.deleteTierBtn', function () {
		const id = $(this).data('id');
		if(confirm('Delete this tier?'))
			$.ajax({ url: `/api/tiers/${id}`, type: 'DELETE' }).done(loadTiers);
	});

	// ========== TIER PERKS ==========
	$(document).on('click', '.manageTierPerksBtn', function () {
		currentTierId = $(this).data('id');
		loadTierPerks(currentTierId);
		const tier = allTiers.find(t => t.id == currentTierId);
		$('#tierPerksModal .tierName').text(tier ? `${tier.name}` : '');
		openModal('tierPerksModal');
	});

	function loadTierPerks(tierId) {
		$.get(`/api/perks`, allPerks => {
			$.get(`/api/tier_perks/${tierId}`, assigned => {
				const assignedIds = assigned.map(p => p.id);
				const available = allPerks.filter(p => !assignedIds.includes(p.id));

				$('#assignedPerksList').empty();
				assigned.forEach(p => {
					$('#assignedPerksList').append(`<li>
					<span>${p.name}</span><small class="reset-period">&nbsp;(${p.reset_period})</small>
					<button class="btn-delete unassignPerkBtn" data-id="${p.id}">Unassign Perk</button>
					</li>`);
				});

				$('#availablePerksList').empty();
				available.forEach(p => {
					$('#availablePerksList').append(`<li>
						<span>${p.name}</span><small class="reset-period">&nbsp;(${p.reset_period})</small>
						<button class="btn-edit assignPerkBtn" data-id="${p.id}">Assign Perk</button>
						<button class="btn-edit editPerkBtn" data-id='${JSON.stringify(p)}'>Edit Perk</button>
						<button class="btn-delete deletePerkBtn" data-id="${p.id}">Delete Perk</button>
					</li>`);
				});
				applyUnlimitedFilter();
			});
		});
	}

	$(document).on('click', '.assignPerkBtn', function () {
		const perkId = $(this).data('id');
		$.ajax({
			url: '/api/tier_perks',
			type: 'POST',
			data: JSON.stringify({ tier_id: currentTierId, perk_id: perkId }),
			contentType: 'application/json',
			success: () => {
				loadTierPerks(currentTierId);
				loadMembers();
			}
		});
	});

	$(document).on('click', '.unassignPerkBtn', function () {
		const perkId = $(this).data('id');
		$.ajax({
			url: '/api/tier_perks',
			type: 'DELETE',
			data: JSON.stringify({ tier_id: currentTierId, perk_id: perkId }),
			contentType: 'application/json',
			success: () => {
				loadTierPerks(currentTierId);
				loadMembers();
			}
		});
	});

	// ========== PERK CRUD ==========
	$('#createPerkBtn').click(() => {
		$('#perkModalTitle').text('Create Perk');
		$('#perkIdInput').val('');
		$('#perkNameField').val('');
		$('#perkResetField').val('Weekly');
		openModal('perkModal');
	});

	$(document).on('click', '.editPerkBtn', function () {
		const p = JSON.parse($(this).attr('data-id'));
		$('#perkModalTitle').text('Edit Perk');
		$('#perkIdInput').val(p.id);
		$('#perkNameField').val(p.name);
		$('#perkResetField').val(p.reset_period);
		openModal('perkModal');
	});

	$('#savePerkBtn').click(() => {
		const perk = {
			id: $('#perkIdInput').val(),
			name: $('#perkNameField').val(),
			reset_period: $('#perkResetField').val()
		};
		$.ajax({
			url: '/api/perks',
			type: 'POST',
			data: JSON.stringify(perk),
			contentType: 'application/json',
			success: () => {
				closeTopModal();
				loadTierPerks(currentTierId);
				loadMembers();
			}
		});
	});

	$(document).on('click', '.deletePerkBtn', function () {
		const perkId = $(this).data('id');
		if(confirm('Delete this perk?')) {
			$.ajax({ url: `/api/perks/${perkId}`, type: 'DELETE' }).done(() => {
				loadTierPerks(currentTierId);
				loadMembers();
			});
		}
	});

	// ========== MEMBER PERKS ==========
	// rendering perk items inside #perksList
	$(document).on('click', '.viewPerksBtn', function () {
		memberId = $(this).data('id');
		const member = allMembers.find(m => m.member_id == memberId);
    currentMember = member;
    refreshPerksModal(memberId, member.name);
  	openModal('perksModal');
	});
  
  function refreshPerksModal(memberId, memberName) {
		$('#perksModal .memberName').text(memberName);
    $("#loadingOverlay").fadeIn(200);
    fetch(`/api/member_perks/${memberId}`)
    .then(r => r.json())
    .then(perks => {
			const ul = $('#perksList').empty();
			perks.forEach(p => {
				const claimed = p.last_claimed !== null && p.last_claimed !== undefined;
				const isUnlimited = p.reset_period === 'Unlimited';
        const hideUnlimited = $('#toggleUnlimitedMember').is(':checked');
				let html = `<li${isUnlimited && hideUnlimited?' style="display: none;"':''} class="perk-item">`;
				html += `<div><strong>${p.name}</strong> <small class="reset-period">(${p.reset_period})</small></div>`;
				if(!isUnlimited) {
					html += `<div class="perk-meta">`;
					if(claimed) {
						html += `<div class="perk-dates">
							<div><i>Claimed On:&nbsp;&nbsp;${new Date(p.last_claimed).toLocaleDateString('en-GB', { day: 'numeric', month: 'numeric', year: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric' })||null}</i></div>
							<div><i>Resets On:&nbsp;&nbsp;${new Date(p.next_reset_date||p.last_claimed.split(', ')[0].split('-').map((e,i)=>i==0?+e+1:e).join('-')).toLocaleDateString('en-GB', { day: 'numeric', month: 'numeric', year: 'numeric' })||null}</i></div> ${/* DO NOT (DELETE)/(CHANGE THE FUNCTIONALITY OF) THIS LINE */''}
						</div>`;
						html += `<button class="resetPerkBtn" data-id="${p.id}">Reset Perk</button>`;
						html += `<span class="badge-claimed">Claimed</span>`;
            html += `<button class="advancePerkBtn" data-id="${p.id}">⏭ Pre-Claim Next Period</button>`
					} else html += `<button class="claimPerkBtn" data-id="${p.id}">Claim</button>`;
					html += `</div>`;
				}
				html += `</li>`;
				ul.append(html);
			});

      ul[0].querySelectorAll(".claimPerkBtn").forEach(btn =>
        btn.onclick = () => claimPerk(btn.dataset.id));
      ul[0].querySelectorAll(".resetPerkBtn").forEach(btn =>
        btn.onclick = () => resetPerk(btn.dataset.id));
      ul[0].querySelectorAll(".advancePerkBtn").forEach(btn =>
        btn.onclick = () => advancePerk(memberId, btn.dataset.id));
      $("#loadingOverlay").fadeOut(200);
    });
  }
  
  function claimPerk(perkId) {
		if(confirm('Claim this perk?')) {
			$.ajax({
				url: '/api/member_perks/claim',
				type: 'POST',
				data: JSON.stringify({ member_id: currentMember.member_id, perk_id: perkId }),
				contentType: 'application/json',
				success: () => { refreshPerksModal(currentMember.member_id, currentMember.name); }
			});
		}
	}
  
  function resetPerk(perkId) {
		if(confirm('Reset this perk?')) {
			$.ajax({
				url: '/api/member_perks/reset',
				type: 'POST',
				data: JSON.stringify({ member_id: currentMember.member_id, perk_id: perkId }),
				contentType: 'application/json',
				success: () => { refreshPerksModal(currentMember.member_id, currentMember.name); }
			});
		}
  }
  
  function advancePerk(memberId, perkId) {
    if (!confirm("Are you sure you want to claim an additional future period of this perk?")) return;
    $("#loadingOverlay").fadeIn(200);
    fetch('/api/member_perks/advance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ member_id: memberId, perk_id: perkId })
    })
    .then(r => r.json())
    .then(res => {
        if (res.error) alert("Error: " + res.error);
    })
    .catch(err => alert("Advance failed"))
    .finally(()=>{ refreshPerksModal(memberId, $(".memberName").text()); $("#loadingOverlay").fadeOut(200); });
  }

	function formatDMY(dateString) {
		if(!dateString || dateString === '-' || dateString === 'null') return '-';
		const d_t=dateString.split` `, [y, m, d] = d_t[0].split('-');
		return `${d}-${m}-${y} `+(d_t[1]||'');
	}

	// ========== HELPERS ==========
	function loadTiersIntoSelect(type, selector, selectedId = null, callback) {
		$.get('/api/tiers', tiers => {
			const sel = $(selector).empty();
			tiers.forEach(t => { sel.append(`<option value="${t.id}" ${t.id == selectedId ? 'selected' : ''}>${t.name}</option>`); });
			if(callback) callback(tiers);
		});
	}
  
  $(document).ajaxStart(function () {
    $("#loadingOverlay").fadeIn(200);
  });

  $(document).ajaxStop(function () {
    $("#loadingOverlay").fadeOut(200);
  });
  
  // ========== AUTO-SYNC UI POLLING ==========
  // Poll every 60s for backend changes, refreshes only if modals are closed (so we don't interrupt edits)
  setInterval(function() {
    // Don't refresh while editing
    if ($('.modal:visible').length === 0) {
      loadMembers();
      loadTiers();
    }
  }, 60000); // every 60s, change to 30000 for 30s, etc


	// Initial load
	loadMembers();
});

// static/app.js

$(document).ready(function () {
  let currentTierId = null;
  let currentMemberId = null;

  // ========== MODAL HANDLERS ==========
  function openModal(id) {
    $(`#${id}`).show();
  }

  function closeModals() {
    $('.modal').hide();
  }

  $('.close').on('click', closeModals);

  window.onclick = function (event) {
    if ($(event.target).hasClass('modal')) closeModals();
  };

  // ========== MEMBERS ==========
  function loadMembers() {
    $.get('/api/members', function (members) {
      const tbody = $('#membersTable tbody').empty();
      members.forEach(m => {
        const row = `<tr>
          <td>${m.member_id}</td>
          <td>${m.name}</td>
          <td>${m.tier_name || '—'}</td>
          <td>
            <button class="editMemberBtn" data-id='${JSON.stringify(m)}'>Edit</button>
            <button class="deleteMemberBtn" data-id="${m.member_id}">Delete</button>
            <button class="viewPerksBtn" data-id="${m.member_id}">View Perks</button>
          </td>
        </tr>`;
        tbody.append(row);
      });
    });
  }

  $('#addMemberBtn').click(() => {
    $('#memberModalTitle').text('Add Member');
    $('#memberModal input, #memberModal select').val('');
    loadTiersIntoSelect('#tierField');
    openModal('memberModal');
  });

  $(document).on('click', '.editMemberBtn', function () {
    const data = JSON.parse($(this).attr('data-id'));
    $('#memberModalTitle').text('Edit Member');
    $('#memberIdInput').val(data.id);
    $('#memberIdField').val(data.member_id);
    $('#nameField').val(data.name);
    $('#signUpDateField').val(data.sign_up_date);
    $('#dobField').val(data.date_of_birth);
    loadTiersIntoSelect('#tierField', data.tier_id);
    openModal('memberModal');
  });

  $('#saveMemberBtn').click(() => {
    const member = {
      id: $('#memberIdInput').val(),
      member_id: $('#memberIdField').val(),
      name: $('#nameField').val(),
      tier_id: $('#tierField').val(),
      sign_up_date: $('#signUpDateField').val(),
      date_of_birth: $('#dobField').val()
    };
	$.ajax({
	  url: '/api/members',
	  type: 'POST',
	  data: JSON.stringify(member),
	  contentType: 'application/json',
	  success: () => {
		closeModals();
		loadMembers();
	  }
	});
  });

  $(document).on('click', '.deleteMemberBtn', function () {
    const id = $(this).data('id');
    if (confirm('Delete this member?')) {
      $.ajax({ url: `/api/members/${id}`, type: 'DELETE' }).done(loadMembers);
    }
  });

  // ========== TIERS ==========
  $('#manageTiersBtn').click(() => {
    loadTiers();
    openModal('tiersModal');
  });

  function loadTiers() {
    $.get('/api/tiers', tiers => {
      const ul = $('#tiersList').empty();
      tiers.forEach(t => {
        ul.append(`<li>
          <b>${t.name}</b> (${t.color})
          <button class="editTierBtn" data-id='${JSON.stringify(t)}'>Edit</button>
          <button class="deleteTierBtn" data-id="${t.id}">Delete</button>
          <button class="manageTierPerksBtn" data-id="${t.id}">Manage Perks</button>
        </li>`);
      });
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
		closeModals();
		loadTiers();
		loadTiersIntoSelect('#tierField');
	  }
	});
  });

  $(document).on('click', '.deleteTierBtn', function () {
    const id = $(this).data('id');
    if (confirm('Delete this tier?')) {
      $.ajax({ url: `/api/tiers/${id}`, type: 'DELETE' }).done(() => {
        loadTiers();
        loadTiersIntoSelect('#tierField');
      });
    }
  });

  // ========== TIER PERKS ==========
  $(document).on('click', '.manageTierPerksBtn', function () {
    currentTierId = $(this).data('id');
    loadTierPerks(currentTierId);
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
            ${p.name} (${p.reset_period})
            <button class="unassignPerkBtn" data-id="${p.id}">Unassign</button>
          </li>`);
        });

        $('#availablePerksList').empty();
        available.forEach(p => {
          $('#availablePerksList').append(`<li>
            ${p.name} (${p.reset_period})
            <button class="assignPerkBtn" data-id="${p.id}">Assign</button>
            <button class="editPerkBtn" data-id='${JSON.stringify(p)}'>Edit</button>
            <button class="deletePerkBtn" data-id="${p.id}">Delete</button>
          </li>`);
        });
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
	  }
	});
  });

  $(document).on('click', '.unassignPerkBtn', function () {
    const perkId = $(this).data('id');
    $.ajax({
      url: '/api/tier_perks',
      type: 'DELETE',
      data: JSON.stringify({ tier_id: currentTierId, perk_id: perkId }),
      contentType: 'application/json'
    }).done(() => loadTierPerks(currentTierId));
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
		closeModals();
        loadTierPerks(currentTierId);
	  }
	});
  });

  $(document).on('click', '.deletePerkBtn', function () {
    const perkId = $(this).data('id');
    if (confirm('Delete this perk?')) {
      $.ajax({ url: `/api/perks/${perkId}`, type: 'DELETE' }).done(() => {
        loadTierPerks(currentTierId);
      });
    }
  });

  // ========== MEMBER PERKS ==========
  $(document).on('click', '.viewPerksBtn', function () {
    currentMemberId = $(this).data('id');
    $.get(`/api/member_perks/${currentMemberId}`, perks => {
      const ul = $('#perksList').empty();
      perks.forEach(p => {
        let html = `<li>
          ${p.name} (${p.reset_period}) `;
        if (p.reset_period === 'Unlimited') {
          html += '</li>';
        } else if (p.perk_claimed) {
          html += `
            <span>Last: ${p.last_claimed || '-'}, Reset: ${p.next_reset_date || '-'}</span>
            <button class="resetPerkBtn" data-id="${p.id}">Reset Perk</button>
            <button disabled>Claimed</button>
          </li>`;
        } else {
          html += `<button class="claimPerkBtn" data-id="${p.id}">Claim</button></li>`;
        }
        ul.append(html);
      });
      openModal('perksModal');
    });
  });

  $(document).on('click', '.claimPerkBtn', function () {
    const perkId = $(this).data('id');
    if (confirm('Claim this perk?')) {
	  $.ajax({
		url: '/api/member_perks/claim',
		type: 'POST',
		data: JSON.stringify({ member_id: currentMemberId, perk_id: perkId }),
		contentType: 'application/json',
		success: () => { $(`.viewPerksBtn[data-id="${currentMemberId}"]`).click(); }
	  });
    }
  });

  $(document).on('click', '.resetPerkBtn', function () {
    const perkId = $(this).data('id');
    if (confirm('Reset this perk?')) {
	  $.ajax({
		url: '/api/member_perks/reset',
		type: 'POST',
		data: JSON.stringify({ member_id: currentMemberId, perk_id: perkId }),
		contentType: 'application/json',
		success: () => { $(`.viewPerksBtn[data-id="${currentMemberId}"]`).click(); }
      });
    }
  });

  // ========== HELPERS ==========
  function loadTiersIntoSelect(selector, selectedId = null) {
    $.get('/api/tiers', tiers => {
      const sel = $(selector).empty();
      tiers.forEach(t => {
        sel.append(`<option value="${t.id}" ${t.id == selectedId ? 'selected' : ''}>${t.name}</option>`);
      });
    });
  }

  // Initial load
  loadMembers();
});

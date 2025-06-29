// static/app.js

$(document).ready(function () {
  let currentTierId = null;
  let currentMemberId = null;
  let modalStack = [];

  // ========== MODAL HANDLERS ==========
  function openModal(id) {
    $(`#${id}`).show();
    modalStack.push(id);
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
  function loadMembers() {
    $.get('/api/members', function (members) {
      const tbody = $('#membersTable tbody').empty();
      members.forEach(m => {
        const row = `<tr>
          <td>${m.member_id}</td>
          <td><span class="tier-badge" style="background-color:${m.color || '#888'}">${m.tier_name}</span></td>
          <td>${m.name}</td>
          <td>
            <button class="viewPerksBtn" data-id="${m.member_id}">Claim Perks</button>
            <button class="btn-edit editMemberBtn" data-id='${JSON.stringify(m)}'>Edit</button>
            <button class="btn-delete deleteMemberBtn" data-id="${m.member_id}">Delete</button>
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
    const member_id = $('#memberIdField').val();
    const name = $('#nameField').val();
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
        if(xhr.status === 409 || (xhr.responseText && xhr.responseText.includes('UNIQUE constraint failed'))) {
          alert("Member ID must be unique.");
        } else {
          alert("Failed to save member. Please try again.");
        }
      }
    });
  });

  $(document).on('click', '.deleteMemberBtn', function () {
    const id = $(this).data('id');
    if(confirm('Delete this member?')) {
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
    if(confirm('Delete this tier?')) {
      $.ajax({ url: `/api/tiers/${id}`, type: 'DELETE' }).done(loadTiers);
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
            <span>${p.name}</span><small>&nbsp;(${p.reset_period})</small>
            <button class="btn-delete unassignPerkBtn" data-id="${p.id}">Unassign Perk</button>
          </li>`);
        });

        $('#availablePerksList').empty();
        available.forEach(p => {
          $('#availablePerksList').append(`<li>
            <span>${p.name}</span><small>&nbsp;(${p.reset_period})</small>
            <button class="btn-edit assignPerkBtn" data-id="${p.id}">Assign Perk</button>
            <button class="btn-edit editPerkBtn" data-id='${JSON.stringify(p)}'>Edit Perk</button>
            <button class="btn-delete deletePerkBtn" data-id="${p.id}">Delete Perk</button>
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
    currentMemberId = $(this).data('id');
    $.get(`/api/member_perks/${currentMemberId}`, perks => {
      const ul = $('#perksList').empty();
      perks.forEach(p => {
        const claimed = p.last_claimed !== null && p.last_claimed !== undefined;
        const isUnlimited = p.reset_period === 'Unlimited';
        let html = `<li class="perk-item">`;
        html += `<div><strong>${p.name}</strong> <span class="reset-period">(${p.reset_period})</span></div>`;

        if(!isUnlimited) {
          html += `<div class="perk-meta">`;
          if(claimed) {
            html += `<div class="perk-dates">
                        <div>Claimed On: ${formatDMY(p.last_claimed)}</div>
                        <div>Resets On: ${formatDMY(p.next_reset_date)}</div>
                     </div>`;
            html += `<button class="resetPerkBtn" data-id="${p.id}">Reset Perk</button>`;
            html += `<span class="badge-claimed">Claimed</span>`;
          } else {
            html += `<button class="claimPerkBtn" data-id="${p.id}">Claim</button>`;
          }
          html += `</div>`;
        }

        html += `</li>`;
        ul.append(html);
      });
      openModal('perksModal');
    });
  });

  function formatDMY(dateString) {
    if(!dateString || dateString === '-' || dateString === 'null') return '-';
    const [y, m, d] = dateString.split('-');
    return `${d}-${m}-${y}`;
  }

  $(document).on('click', '.claimPerkBtn', function () {
    const perkId = $(this).data('id');
    if(confirm('Claim this perk?')) {
      $.ajax({
        url: '/api/member_perks/claim',
        type: 'POST',
        data: JSON.stringify({ member_id: currentMemberId, perk_id: perkId }),
        contentType: 'application/json',
        success: () => {
          $(`.viewPerksBtn[data-id="${currentMemberId}"]`).click();
        }
      });
    }
  });

  $(document).on('click', '.resetPerkBtn', function () {
    const perkId = $(this).data('id');
    if(confirm('Reset this perk?')) {
      $.ajax({
        url: '/api/member_perks/reset',
        type: 'POST',
        data: JSON.stringify({ member_id: currentMemberId, perk_id: perkId }),
        contentType: 'application/json',
        success: () => {
          $(`.viewPerksBtn[data-id="${currentMemberId}"]`).click();
        }
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

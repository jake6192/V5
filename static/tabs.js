document.addEventListener('DOMContentLoaded', () => {
  const tabList = document.getElementById('tabs-list');
  const newTabBtn = document.getElementById('new-tab-btn');
  const timerMap = {};

  newTabBtn.addEventListener('click', () => {
    document.getElementById('new-tab-modal').classList.remove('hidden');
  });

  document.getElementById('create-tab-confirm').addEventListener('click', async () => {
    const bay = document.getElementById('bay-input').value;
    const booking = document.getElementById('booking-start').value;
    if (!booking) {
      alert("Please enter a valid booking start time.");
      return;
    }
    const duration = document.getElementById('duration').value;
  if (!booking) {
    alert("Please enter a valid booking start time.");
    return;
  }
    await fetch('/api/tabs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bay_number: bay, booking_start: booking, duration_minutes: duration })
    });
    closeModal('new-tab-modal');
    loadTabs();
  });

  window.closeModal = id => document.getElementById(id).classList.add('hidden');

  async function loadTabs() {
    $('#tabs-list').html('');
    const res = await fetch('/api/tabs');
    const tabs = await res.json();
    const now = new Date();

    for (const tab of tabs) {
      // Archive timer if paid_at exists
      if (tab.paid && tab.paid_at) {
        const paidTime = new Date(tab.paid_at).getTime();
        const nowTime = Date.now();
        const msLeft = Math.max(0, (paidTime + 1 * 60000) - nowTime);
        console.log(msLeft-3600000);//Time zone BST DST UTC GMT todo timezone bugfix bug fix bug-fix
        if(msLeft-3600000 < 1)//Time zone BST DST UTC GMT todo timezone bugfix bug fix bug-fix
          await fetch(`/api/tabs/${tab.id}?force_paid=${tab.paid}`, { method: 'DELETE' }).then(loadTabs);
        else {
          clearTimeout(timerMap[tab.id]);
          timerMap[tab.id] = setTimeout(async() => {
            await fetch(`/api/tabs/${tab.id}?force_paid=${tab.paid}`, { method: 'DELETE' }).then(loadTabs);
          }, msLeft-3600000);//Time zone BST DST UTC GMT todo timezone bugfix bug fix bug-fix
        }
      }
    
      const card = document.createElement('div');
      card.className = 'tab-card';
      if (tab.paid) card.classList.add('paid');
      const start = new Date(tab.booking_start);
      const ageMin = (now - new Date(tab.created_at)) / 60000;
      if (!tab.paid && ageMin > 60) card.classList.add('highlight');

      card.innerHTML = `
        <div class="tab-header">
          ${tab.overdue && !tab.paid ? '<div class="overdue-banner">⚠️ OVERDUE TAB</div>' : ''}
          <h3>Bay ${tab.bay_number}: <span>${start.toLocaleTimeString()}<small> (${tab.duration_minutes} min)</small></span></h3>
        </div>
        <div class="tab-body" data-tab-id="${tab.id}">
          <ul class="tab-items"></ul>
        </div>
        <div class="tab-footer">
          <div>Total: £${(+tab.total).toFixed(2) || '0.00'}</div>
          <div>
            <button id="markPaid" onclick="markPaid(${tab.id})" ${tab.paid ? 'style="display: none;"' : ''}>Mark Paid</button>
            <button id="markUnPaid" onclick="undoPaid(${tab.id})" ${!tab.paid ? 'style="display: none;"' : ''}>Mark Un-Paid</button>
            <button onclick="deleteTab(${tab.id}, ${tab.paid})">Delete</button>
          </div>
        </div>`;

      const list = card.querySelector('.tab-items');
      list.innerHTML = '';

      const resItems = await fetch(`/api/tab_items/${tab.id}`);
      const items = await resItems.json();
      const addedItemIds = new Set();

      for (const item of items) {
        const line = document.createElement('li');
        line.className = 'tab-item-line';
        line.setAttribute('data-qty', item.quantity);
        line.setAttribute('data-price', item.price);
        line.innerHTML = `
          <span>${item.name}</span>
          <div>
            <button onclick="adjustQty(${tab.id}, ${item.item_id}, -1)">-</button>
            <span id="qty-display-${tab.id}-${item.item_id}">${item.quantity}</span>
            <button onclick="adjustQty(${tab.id}, ${item.item_id}, 1)">+</button>
          </div>
        `;
        list.appendChild(line);
        addedItemIds.add(item.item_id);
      }
      updateTabTotal(tab.id);
      tabList.appendChild(card);

      const body = card.querySelector('.tab-body');
      const addRow = document.createElement('div');
      addRow.className = 'add-new-row';
      addRow.innerText = 'Click to add new item';
      addRow.onclick = () => openAddItemModal(tab.id, addedItemIds);
      body.appendChild(addRow);
    }
  }

  window.adjustQty = async (tabId, itemId, delta) => {
    const display = document.getElementById(`qty-display-${tabId}-${itemId}`);
    if (!display) return;

    const current = parseInt(display.innerText) || 1;
    const newQty = Math.max(current + delta);
    display.innerText = newQty;

    try {
      if (newQty <= 0) {
        await fetch(`/api/tab_items/${tabId}/${itemId}`, { method: 'DELETE' });
        loadTabs();
        return;
      }
      const res = await fetch('/api/tab_item_qty', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tab_id: tabId, item_id: itemId, quantity: newQty })
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        showToast('Failed to update quantity', 'error');
      } else {
        // ✅ LIVE TOTAL UPDATE
        updateTabTotal(tabId);
        loadTabs();
      }
    } catch (err) {
      console.error('❌ Error adjusting qty:', err);
      showToast('Error updating quantity', 'error');
    }
  };

  window.openAddItemModal = async (tabId, existingItems) => {
    const res = await fetch('/api/stock');
    const items = await res.json();
    const modal = document.createElement('div');
    modal.className = 'modal';
    const content = document.createElement('div');
    content.className = 'modal-content';
    content.innerHTML = `<h3>Select Item to Add</h3>`;
    const container = document.createElement('div');
    container.style.maxHeight = '300px';
    container.style.overflowY = 'auto';

    for (const item of items) {
      const div = document.createElement('div');
      div.innerText = item.name;
      div.style.padding = '6px';
      div.style.borderBottom = '1px solid #ccc';
      if (existingItems.has(item.id)) {
        div.style.opacity = 0.4;
        div.style.pointerEvents = 'none';
      } else {
        div.style.cursor = 'pointer';
        div.onclick = async () => {
          await fetch(`/api/tabs/${tabId}/items`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_id: item.id, quantity: 1 })
          });
          document.body.removeChild(modal);
          loadTabs();
        };
      }
      container.appendChild(div);
    }

    const cancel = document.createElement('button');
    cancel.innerText = 'Cancel';
    cancel.onclick = () => document.body.removeChild(modal);
    content.appendChild(container);
    content.appendChild(cancel);
    modal.appendChild(content);
    document.body.appendChild(modal);
  };

  window.markPaid = async (tabId) => {
    await fetch(`/api/tabs/${tabId}/pay`, { method: 'POST' });
    $('#markPaid, #markUnPaid').toggle();
    loadTabs();
  };

  window.undoPaid = async (tabId) => {
    if (timerMap[tabId]) {
      clearTimeout(timerMap[tabId]);
      delete timerMap[tabId];
    }
    $('#markPaid, #markUnPaid').toggle();
    await fetch(`/api/tabs/${tabId}/undo`, { method: 'POST' });
    loadTabs();
  };

  function updateTabTotal(tabId) {
    let total = 0;
    // Find all tab items for this tab
    const itemElements = document.querySelectorAll(`.tab[data-id="${tabId}"] .tab-item-line`);
    itemElements.forEach(el => {
      const qtyEl = el.querySelector('[id^="qty-display-"]');
      const priceAttr = el.getAttribute('data-price');
      const price = parseFloat(priceAttr);
      const qty = parseInt(qtyEl?.innerText) || 0;

      total += price * qty;
    });
    // Update total display
    const totalDisplay = document.getElementById(`tab-total-${tabId}`);
    if (totalDisplay) {
      totalDisplay.innerText = `£${total.toFixed(2)}`;
    }
  }

  window.deleteTab = (tabId, paid) => {
    const modal = document.createElement('div');
    modal.className = 'modal';
    const box = document.createElement('div');
    box.className = 'modal-content';

    box.innerHTML = paid
      ? `<p>This tab is marked as paid. Are you sure you want to delete it?</p>`
      : `<p>This tab has not been marked as paid.<br>
          Do you want to delete it anyway (loss will be recorded), or mark it paid and delete?</p>`;

    const deleteBtn = document.createElement('button');
    deleteBtn.innerText = paid ? 'Delete' : 'Delete Anyway';
    deleteBtn.onclick = async () => {
      await fetch(`/api/tabs/${tabId}?force_paid=${paid}`, { method: 'DELETE' });
      document.body.removeChild(modal);
      loadTabs();
    };

    const markAndDeleteBtn = document.createElement('button');
    markAndDeleteBtn.innerText = 'Mark Paid + Delete';
    markAndDeleteBtn.onclick = async () => {
      await fetch(`/api/tabs/${tabId}/pay`, { method: 'POST' });
      await fetch(`/api/tabs/${tabId}?force_paid=true`, { method: 'DELETE' });
      document.body.removeChild(modal);
      loadTabs();
    };

    const cancelBtn = document.createElement('button');
    cancelBtn.innerText = 'Cancel';
    cancelBtn.onclick = () => document.body.removeChild(modal);

    if (!paid) box.appendChild(markAndDeleteBtn);
    box.appendChild(deleteBtn);
    box.appendChild(cancelBtn);
    modal.appendChild(box);
    document.body.appendChild(modal);
  };
  loadTabs();
});

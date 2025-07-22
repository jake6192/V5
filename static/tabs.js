document.addEventListener('DOMContentLoaded', () => {
  const tabList = document.getElementById('tabs-list');
  const newTabBtn = document.getElementById('new-tab-btn');

  newTabBtn.addEventListener('click', () => {
    document.getElementById('new-tab-modal').classList.remove('hidden');
  });

  document.getElementById('create-tab-confirm').addEventListener('click', async () => {
    const bay = document.getElementById('bay-input').value;
    const booking = document.getElementById('booking-start').value;
    const duration = document.getElementById('duration').value;
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
    tabList.innerHTML = '';
    const res = await fetch('/api/tabs');
    const tabs = await res.json();
    const now = new Date();

    for (const tab of tabs) {
      const card = document.createElement('div');
      card.className = 'tab-card';
      const start = new Date(tab.booking_start);
      const ageMin = (now - new Date(tab.created_at)) / 60000;
      if (!tab.paid && ageMin > 60) card.classList.add('highlight');

      card.innerHTML = `
        <div class="tab-header">
          <h3>Bay ${tab.bay_number}: <span>${start.toLocaleTimeString()}<small> (${tab.duration_minutes} min)</small></span></h3>
        </div>
        <div class="tab-body" data-tab-id="${tab.id}">
          <p>Loading items...</p>
        </div>
        <div class="tab-footer">
          <button onclick="markPaid(${tab.id})">Mark Paid</button>
          <button onclick="deleteTab(${tab.id})">Delete</button>
        </div>`;
      tabList.appendChild(card);

      const body = card.querySelector('.tab-body');
      const itemsRes = await fetch(`/api/stock`);
      const stockItems = await itemsRes.json();
      body.innerHTML = '';

      for (const item of stockItems) {
        const line = document.createElement('div');
        line.className = 'item-line';
        line.innerHTML = `
          <span>${item.name}</span>
          <input type="number" min="1" value="1" id="qty-${tab.id}-${item.id}">
          <button onclick="addItem(${tab.id}, ${item.id})">Add</button>`;
        body.appendChild(line);
      }
    }
  }

  window.addItem = async (tabId, itemId) => {
    const qty = document.getElementById(`qty-${tabId}-${itemId}`).value;
    await fetch(`/api/tabs/${tabId}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_id: itemId, quantity: parseInt(qty) })
    });
    loadTabs();
  }

  window.markPaid = async (tabId) => {
    await fetch(`/api/tabs/${tabId}/pay`, { method: 'POST' });
    loadTabs();
  }

  window.deleteTab = async (tabId) => {
    await fetch(`/api/tabs/${tabId}`, { method: 'DELETE' });
    loadTabs();
  }

  loadTabs();
});

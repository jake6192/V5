document.addEventListener('DOMContentLoaded', () => {
  const stockList = document.getElementById('stock-list');
  const searchInput = document.getElementById('search-input');
  const modal = document.getElementById('stock-modal');
  const addBtn = document.getElementById('add-stock-btn');
  const reportBtn = document.getElementById('view-reports-btn');
  const reportModal = document.getElementById('report-modal');
  let editingId = null;

  window.closeModal = id => document.getElementById(id).classList.add('hidden');

  addBtn.onclick = () => {
    editingId = null;
    clearModal();
    document.getElementById('modal-title').innerText = 'New Item';
    modal.classList.remove('hidden');
  };

  document.getElementById('save-stock-btn').onclick = async () => {
    const payload = getModalData();
    const url = editingId ? `/api/stock/${editingId}` : '/api/stock';
    const method = editingId ? 'PUT' : 'POST';

    await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    closeModal('stock-modal');
    loadStock();
  };

  reportBtn.onclick = async () => {
    const res = await fetch('/api/reports/profit');
    const data = await res.json();
    const container = document.getElementById('report-results');
    container.innerHTML = '<table><tr><th>Name</th><th>Qty</th><th>Revenue</th><th>Cost</th><th>Profit</th></tr>' +
      data.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>£${r[2]}</td><td>£${r[3]}</td><td>£${r[4]}</td></tr>`).join('') +
      '</table>';
    reportModal.classList.remove('hidden');
  };

  searchInput.oninput = () => {
    for (const card of stockList.children) {
      const txt = card.dataset.filter;
      card.style.display = txt.includes(searchInput.value.toLowerCase()) ? '' : 'none';
    }
  };

  function getModalData() {
    return {
      name: document.getElementById('stock-name').value,
      venue: document.getElementById('stock-venue').value,
      price: parseFloat(document.getElementById('stock-price').value),
      cost_price: parseFloat(document.getElementById('stock-cost').value),
      total_inventory: parseInt(document.getElementById('stock-qty').value),
      description: document.getElementById('stock-desc').value,
      image_url: document.getElementById('stock-img').value
    };
  }

  function clearModal() {
    for (const id of ['stock-name','stock-venue','stock-price','stock-cost','stock-qty','stock-desc','stock-img']) {
      document.getElementById(id).value = '';
    }
  }

  async function loadStock() {
    const res = await fetch('/api/stock');
    const items = await res.json();
    stockList.innerHTML = '';
    for (const item of items) {
      const card = document.createElement('div');
      card.className = 'stock-card';
      card.dataset.filter = `${item.name.toLowerCase()} ${item.venue.toLowerCase()}`;
      card.innerHTML = `
        <h4>${item.name}</h4>
        <p>£${item.price} @ ${item.venue}</p>
        <p><strong>${item.total_inventory}</strong> in stock</p>
        <button onclick="editItem(${item.id})">Edit</button>
        <button onclick="deleteItem(${item.id})">Delete</button>
      `;
      stockList.appendChild(card);
    }
  }

  window.editItem = async (id) => {
    editingId = id;
    const res = await fetch('/api/stock');
    const items = await res.json();
    const item = items.find(i => i.id === id);
    document.getElementById('modal-title').innerText = 'Edit Item';
    document.getElementById('stock-name').value = item.name;
    document.getElementById('stock-venue').value = item.venue;
    document.getElementById('stock-price').value = item.price;
    document.getElementById('stock-cost').value = item.cost_price;
    document.getElementById('stock-qty').value = item.total_inventory;
    document.getElementById('stock-desc').value = item.description;
    document.getElementById('stock-img').value = item.image_url;
    modal.classList.remove('hidden');
  };

  window.deleteItem = async (id) => {
    await fetch(`/api/stock/${id}`, { method: 'DELETE' });
    loadStock();
  };

  loadStock();
});

document.addEventListener('DOMContentLoaded', () => {
  const stockList = document.getElementById('stock-list');
  const searchInput = document.getElementById('search-input');
  const modal = document.getElementById('stock-modal');
  const addBtn = document.getElementById('add-stock-btn');
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

document.getElementById('openReportBtn').addEventListener('click', async () => {
  const modal = document.getElementById('reportModal');
  const container = document.getElementById('report-results');
  modal.style.display = 'flex';

  const res = await fetch('/api/reports/profit');
  const data = await res.json();

  let html = '<table><tr><th>Item</th><th>Qty Sold</th><th>Revenue</th><th>Cost</th><th>Profit</th></tr>';
  let totals = { qty: 0, rev: 0, cost: 0, profit: 0 };
  data.forEach(row => {
    const [name, qty, rev, cost, profit] = Object.values(row);
    totals.qty += qty;
    totals.rev += parseFloat(rev);
    totals.cost += parseFloat(cost);
    totals.profit += parseFloat(profit);
    html += `<tr>
      <td>${name}</td>
      <td>${qty}</td>
      <td>£${rev.toFixed(2)}</td>
      <td>£${cost.toFixed(2)}</td>
      <td class="${profit >= 0 ? 'positive' : 'negative'}">£${profit.toFixed(2)}</td>
    </tr>`;
  });
  html += `<tr style="font-weight:bold"><td>Total</td><td>${totals.qty}</td>
    <td>£${totals.rev.toFixed(2)}</td><td>£${totals.cost.toFixed(2)}</td>
    <td class="${totals.profit >= 0 ? 'positive' : 'negative'}">£${totals.profit.toFixed(2)}</td></tr>`;
  html += '</table>';
  container.innerHTML = html;
});

document.getElementById('closeReportModal').addEventListener('click', () => {
  document.getElementById('reportModal').style.display = 'none';
});

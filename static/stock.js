document.addEventListener('DOMContentLoaded', () => {
  const stockList = document.getElementById('stock-list');
  const searchInput = document.getElementById('search-input');
  const modal = document.getElementById('stock-modal');
  const addBtn = document.getElementById('add-stock-btn');
  let editingId = null;

  window.closeModal = id => document.getElementById(id).style.display = 'none';

  addBtn.onclick = () => {
    editingId = null;
    clearModal();
    document.getElementById('modal-title').innerText = 'New Item';
    modal.style.display = 'flex';
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
        <div class="stock-title">${item.name}</div>
        <img class="stock-img" src="${item.image_url || ''}" alt="${item.name}">
        <div class="stock-price">£${item.price} @ ${item.venue}</div>
        <div class="stock-qty"><strong>${item.total_inventory}</strong> in stock</div>
        <div class="stock-footer">
          <button class="btn-edit" onclick="editItem(${item.id})">Edit</button>
          <button class="btn-delete" onclick="deleteItem(${item.id})">Delete</button>
        </div>
      `;
      if (!item.image_url) {
        fetch(`/api/fetch_image?q=${encodeURIComponent(item.name)}`)
          .then(res => res.json())
          .then(data => card.querySelector('img').src = data.bestImageUrl)
          .catch(() => console.warn('No fallback image found'));
      }
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
    modal.style.display = 'flex';
  };

  window.deleteItem = async (id) => {
    await fetch(`/api/stock/${id}`, { method: 'DELETE' });
    loadStock();
  };

  document.getElementById('openSummary').addEventListener('click', async () => {
    openFinancialReport();
    $('#reportModal').css('display', 'flex');
    const res = await fetch('/api/reports/profit');
    const data = await res.json();

    let html = '<table><tr><th>Item</th><th>Qty Sold</th><th>Revenue</th><th>Cost</th><th>Profit</th></tr>';
    let totals = { qty: 0, rev: 0, cost: 0, profit: 0 };
    data.forEach(row => {
      const [name, qty, rev, cost, profit] = Object.values(row);
      totals.qty += +qty;
      totals.rev += +rev;
      totals.cost += +cost;
      totals.profit += +profit;
      html += `<tr>
        <td>${name}</td>
        <td>${+qty}</td>
        <td>£${(+rev).toFixed(2)}</td>
        <td>£${(+cost).toFixed(2)}</td>
        <td class="${+profit >= 0 ? 'positive' : 'negative'}">£${(+profit).toFixed(2)}</td>
      </tr>`;
    });
    html += `<tr style="font-weight:bold"><td>Total</td><td>${totals.qty}</td>
      <td>£${totals.rev.toFixed(2)}</td><td>£${totals.cost.toFixed(2)}</td>
      <td class="${totals.profit >= 0 ? 'positive' : 'negative'}">£${totals.profit.toFixed(2)}</td></tr>`;
    html += '</table>';
    $('#report-results').html(html);
  });
  
  function openFinancialReport() {
    fetch('/api/summary')
    .then(r => r.json())
    .then(data => {
      document.getElementById('summary-losses').textContent = data.total_losses.toFixed(2);
      document.getElementById('summary-net').textContent = data.net_revenue.toFixed(2);
      $('#financialModal').show();
    });
  }
  
  loadStock();
});

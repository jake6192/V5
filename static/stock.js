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
    const _method = editingId ? 'PUT' : 'POST';

    await fetch(url, {
      method: _method,
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
      image_url: document.getElementById('stock-img').value.trim(),
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
        fetch(`/api/fetch_image?q=${encodeURIComponent(item.name)}&id=${item.id}`)
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
  
  function applyDateFilter() {
    const today = new Date();
    const formatDate = d => d.toISOString().split('T')[0];
    let quickFilter = $('#quickFilter').val();
    if (quickFilter === 'all') {
        start = end = '';
    } else if (quickFilter === 'today') {
        start = end = today;
    } else if (quickFilter === 'yesterday') {
        today.setDate(today.getDate()-1);
        start = end = today;
    } else if (quickFilter === 'this_week') {
        const day = today.getDay();
        const diff = today.getDate() - day + (day === 0 ? -6 : 1); // Monday as start
        const monday = new Date(today.setDate(diff));
        start = monday;
        end = new Date();
    } else if (quickFilter === 'this_month') {
        const first = new Date(today.getFullYear(), today.getMonth(), 1);
        start = first;
        end = today;
    } else if (quickFilter === 'last_7_days') {
        const last7 = new Date();
        last7.setDate(today.getDate() - 6);
        start = last7;
        end = today;
    } else {
        start = document.getElementById('startDate').value;
        end = document.getElementById('endDate').value;
    }
    if(quickFilter != 'all') {
      start = formatDate(start);
      end = formatDate(end);
    }
    $('#startDate').val(start);
    $('#endDate').val(end);
    $('#applyDateFilter')[0].click();
  }
  document.getElementById('quickFilter').addEventListener("change", applyDateFilter);
  document.getElementById('applyDateFilter').addEventListener('click', () => {
    let start = $('#startDate').val(), end = $('#endDate').val();
    const range = (start && end) ? { start, end } : '';
    openSummaryModal(range);
  });

  let openSummaryModal = async (dateRange) => {
    openFinancialReport();
    $("#reportModal").css("display", 'flex');
    const res = await fetch('/api/reports/profit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dateRange })
    });
    const data = await res.json();

    let html = `<table><tr>
      <th>Item</th><th>Qty Sold</th><th>Qty Unpaid</th><th>Revenue</th><th>Cost</th>
      <th>Profit</th><th>Loss</th><th>Total P/L</th></tr>`;
    let totals = { sold: 0, lost: 0, rev: 0, cost: 0, profit: 0, loss: 0, net: 0 };
    data.forEach(row => {
      const [ name, sold_qty, qty_lost, revenue, cost, profit, loss, total_pl ] = [...row];
      totals.sold += +sold_qty;
      totals.lost += +qty_lost;
      totals.rev += +revenue;
      totals.cost += +cost;
      totals.profit += +profit;
      totals.loss += +loss;
      totals.net += +total_pl;
      html += `<tr>
        <td>${name}</td>
        <td>${sold_qty}</td>
        <td>${qty_lost}</td>
        <td>£${revenue}</td>
        <td>£${cost}</td>
        <td class='${+profit >= 0 ? 'positive' : 'negative'}'>£${profit}</td>
        <td class='${+loss >= 0 ? 'negative' : 'positive'}'>£${loss}</td>
        <td class='${+total_pl >= 0 ? 'positive' : 'negative'}'>£${total_pl}</td>`;
    });
    html += `<tr style='font-weight:bold'><td>Total</td>
      <td>${totals.sold}</td><td>${totals.lost}</td>
      <td>£${totals.rev.toFixed(2)}</td><td>£${totals.cost.toFixed(2)}</td>
      <td class='${totals.profit >= 0 ? 'positive' : 'negative'}'>£${totals.profit.toFixed(2)}</td>
      <td class='${totals.loss >= 0 ? 'negative' : 'positive'}'>£${totals.loss.toFixed(2)}</td>
      <td class='${totals.net >= 0 ? 'positive' : 'negative'}'>£${totals.net.toFixed(2)}</td>`;
    html += '</tr></table>';
    $('#report-results').html(html);
  };
  document.getElementById('openSummary').addEventListener('click', openSummaryModal);
  
  function openFinancialReport() {
    fetch('/api/summary')
    .then(r => r.json())
    .then(data => {
      document.getElementById('summary-losses').textContent = data.total_losses.toFixed(2);
      $('#financialModal').show();
    });
  }
  
  loadStock();
});
/* 订单列表页脚本：原生 JavaScript + fetch，不依赖前端框架 */
(() => {
  "use strict";

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const state = { page: 1, pageSize: 20, total: 0, products: [], selectedItems: new Map() };
  const $ = (id) => document.getElementById(id);

  function showMessage(text, type = "") {
    const box = $("message");
    if (!box) return;
    box.textContent = text || "";
    box.className = "message" + (type ? ` ${type}` : "");
    box.classList.toggle("hidden", !text);
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[ch]));
  }

  function formatDate(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return escapeHtml(value);
    return new Intl.DateTimeFormat("zh-CN", {
      timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hour12: false,
    }).format(date);
  }

  function formatMoney(value) {
    return value === null || value === undefined || value === "" ? "-" : `¥${value}`;
  }

  function statusBadge(status) {
    const safe = escapeHtml(status || "UNKNOWN");
    return `<span class="status ${safe}">${safe}</span>`;
  }

  function allowedStatuses(current) {
    const map = {
      PENDING: ["PENDING", "PAID", "CANCELLED"],
      PAID: ["PAID", "SHIPPED", "CANCELLED"],
      SHIPPED: ["SHIPPED", "COMPLETED"],
      COMPLETED: ["COMPLETED"],
      CANCELLED: ["CANCELLED"],
    };
    return map[current] || [current];
  }

  async function apiFetch(url, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");
    if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    if (!["GET", "HEAD", "OPTIONS"].includes(method)) headers.set("X-CSRF-Token", csrfToken);
    const response = await fetch(url, { ...options, headers });
    const text = await response.text();
    let payload = null;
    if (text) {
      try { payload = JSON.parse(text); } catch { payload = null; }
    }
    if (!response.ok) {
      const message = payload?.error?.message || `请求失败（HTTP ${response.status}）`;
      const error = new Error(message);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  async function loadProducts(query = "") {
    const select = $("product-select");
    if (!select) return;
    select.innerHTML = '<option value="">加载中...</option>';
    try {
      const params = new URLSearchParams({ page_size: "50" });
      if (query) params.set("q", query);
      const payload = await apiFetch(`/api/products?${params.toString()}`);
      state.products = payload.data || [];
      select.innerHTML = "";
      select.add(new Option("请选择商品", ""));
      if (!state.products.length) {
        select.add(new Option("没有匹配商品", ""));
        return;
      }
      for (const product of state.products) {
        const label = `${product.product_name} | ${product.sku} | 库存 ${product.stock} | ¥${product.unit_price}`;
        select.add(new Option(label, String(product.product_id)));
      }
    } catch (error) {
      select.innerHTML = '<option value="">商品加载失败</option>';
      showMessage(error.message, "error");
    }
  }

  function renderSelectedItems() {
    const list = $("selected-items");
    if (!list) return;
    list.innerHTML = "";
    if (!state.selectedItems.size) {
      const li = document.createElement("li");
      li.className = "muted";
      li.textContent = "尚未添加商品";
      list.appendChild(li);
      return;
    }
    for (const item of state.selectedItems.values()) {
      const li = document.createElement("li");
      const text = document.createElement("span");
      text.textContent = `${item.product_name} × ${item.quantity}`;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn danger small";
      button.dataset.removeProductId = String(item.product_id);
      button.textContent = "移除";
      li.append(text, button);
      list.appendChild(li);
    }
  }

  function addItem() {
    const select = $("product-select");
    const quantityInput = $("product-quantity");
    const productId = select?.value;
    const quantity = Number(quantityInput?.value);
    if (!productId) { showMessage("请先选择商品。", "warn"); return; }
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 1000) {
      showMessage("数量必须是 1~1000 的整数。", "warn"); return;
    }
    const product = state.products.find((p) => String(p.product_id) === String(productId));
    if (!product) { showMessage("商品信息已变化，请重新搜索。", "warn"); return; }
    const existing = state.selectedItems.get(String(productId));
    if (existing) existing.quantity += quantity;
    else state.selectedItems.set(String(productId), {
      product_id: Number(product.product_id), product_name: product.product_name, quantity,
    });
    renderSelectedItems();
    showMessage("", "");
  }

  async function createOrder() {
    const button = $("create-order-btn");
    const customerId = Number($("create-customer")?.value);
    const address = $("create-address")?.value.trim() || "";
    const items = Array.from(state.selectedItems.values()).map((item) => ({
      product_id: item.product_id, quantity: item.quantity,
    }));
    if (!Number.isInteger(customerId) || customerId < 1) {
      showMessage("请输入有效的客户 ID。", "warn"); return;
    }
    if (!items.length) { showMessage("请至少添加一条商品明细。", "warn"); return; }
    button.disabled = true;
    try {
      const payload = await apiFetch("/api/orders", {
        method: "POST",
        body: JSON.stringify({ customer_id: customerId, shipping_address: address || null, items }),
      });
      const orderId = payload?.data?.order?.order_id;
      showMessage(`订单创建成功：#${orderId}（库存已扣减，物流单已生成）`, "ok");
      state.selectedItems.clear();
      renderSelectedItems();
      await loadOrders(1);
    } catch (error) {
      showMessage(error.message, "error");
    } finally {
      button.disabled = false;
    }
  }

  async function loadOrders(page = 1) {
    state.page = page;
    state.pageSize = Number($("filter-page-size")?.value || 20);
    const params = new URLSearchParams({ page: String(state.page), page_size: String(state.pageSize) });
    const customerId = $("filter-customer")?.value.trim();
    const status = $("filter-status")?.value;
    const dateFrom = $("filter-date-from")?.value;
    const dateTo = $("filter-date-to")?.value;
    if (customerId) params.set("customer_id", customerId);
    if (status) params.set("status", status);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    const tbody = $("orders-body");
    tbody.innerHTML = '<tr><td colspan="8" class="muted">加载中...</td></tr>';
    try {
      const payload = await apiFetch(`/api/orders?${params.toString()}`);
      const rows = payload.data || [];
      const meta = payload.meta || {};
      state.total = Number(meta.total || 0);
      const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
      if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="muted">没有符合条件的订单</td></tr>';
      } else {
        tbody.innerHTML = rows.map((order) => {
          const statuses = allowedStatuses(order.status);
          const terminal = statuses.length <= 1;
          const options = statuses.map((status) => (
            `<option value="${escapeHtml(status)}" ${status === order.status ? "selected" : ""}>${escapeHtml(status)}</option>`
          )).join("");
          const shipment = order.tracking_no
            ? `${escapeHtml(order.tracking_no)}<div class="muted">${escapeHtml(order.shipment_status || "")}</div>`
            : '<span class="muted">无</span>';
          return `
            <tr>
              <td><a href="/orders/${Number(order.order_id)}">#${Number(order.order_id)}</a></td>
              <td>${escapeHtml(order.customer_name)}<div class="muted">客户 ${Number(order.customer_id)}</div></td>
              <td>${statusBadge(order.status)}</td>
              <td>${formatDate(order.created_at)}</td>
              <td>${formatMoney(order.total_amount)}</td>
              <td>${Number(order.item_lines)} 行 / ${Number(order.total_quantity)} 件</td>
              <td>${shipment}</td>
              <td><div class="actions">
                <select id="status-${Number(order.order_id)}" ${terminal ? "disabled" : ""}>${options}</select>
                <button class="btn small btn-update-status" type="button"
                        data-order-id="${Number(order.order_id)}" ${terminal ? "disabled" : ""}>更新</button>
              </div></td>
            </tr>`;
        }).join("");
      }
      $("order-count").textContent = `共 ${state.total} 条，第 ${state.page} / ${totalPages} 页`;
      $("page-info").textContent = `第 ${state.page} / ${totalPages} 页`;
      $("prev-page").disabled = state.page <= 1;
      $("next-page").disabled = state.page >= totalPages;
    } catch (error) {
      tbody.innerHTML = '<tr><td colspan="8" class="muted">加载失败</td></tr>';
      showMessage(error.message, "error");
    }
  }

  async function updateStatus(orderId) {
    const select = $(`status-${orderId}`);
    if (!select) return;
    const status = select.value;
    try {
      await apiFetch(`/api/orders/${orderId}/status`, {
        method: "PATCH", body: JSON.stringify({ status }),
      });
      showMessage(`订单 #${orderId} 状态已更新为 ${status}。`, "ok");
      await loadOrders(state.page);
    } catch (error) {
      showMessage(error.message, "error");
      await loadOrders(state.page);
    }
  }

  function bindEvents() {
    $("filter-form")?.addEventListener("submit", (event) => {
      event.preventDefault(); loadOrders(1);
    });
    $("filter-reset")?.addEventListener("click", () => {
      $("filter-form")?.reset(); loadOrders(1);
    });
    $("prev-page")?.addEventListener("click", () => { if (state.page > 1) loadOrders(state.page - 1); });
    $("next-page")?.addEventListener("click", () => { loadOrders(state.page + 1); });
    $("product-search-btn")?.addEventListener("click", () => {
      loadProducts($("product-search")?.value.trim() || "");
    });
    $("add-item-btn")?.addEventListener("click", addItem);
    $("create-order-btn")?.addEventListener("click", createOrder);
    $("selected-items")?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-remove-product-id]");
      if (!button) return;
      state.selectedItems.delete(button.dataset.removeProductId);
      renderSelectedItems();
    });
    $("orders-body")?.addEventListener("click", (event) => {
      const button = event.target.closest(".btn-update-status");
      if (!button) return;
      updateStatus(button.dataset.orderId);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindEvents(); renderSelectedItems(); loadProducts(""); loadOrders(1);
  });
})();
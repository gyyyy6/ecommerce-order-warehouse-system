/* 订单详情页脚本：多表 join 数据展示与删除明细 */
(() => {
  "use strict";

  const root = document.getElementById("order-detail");
  const orderId = root?.dataset.orderId;
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
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
      throw new Error(message);
    }
    return payload;
  }

  function card(label, value) {
    return `<div class="summary-card"><div class="label">${escapeHtml(label)}</div><div class="value">${value}</div></div>`;
  }

  function kv(label, value) {
    return `<div class="kv"><div class="k">${escapeHtml(label)}</div><div class="v">${value}</div></div>`;
  }

  async function loadDetail() {
    const loading = $("detail-loading");
    const content = $("detail-content");
    try {
      const payload = await apiFetch(`/api/orders/${orderId}`);
      const data = payload.data || {};
      const order = data.order || {};
      const items = data.items || [];
      const summary = data.summary || {};

      $("detail-summary").innerHTML = [
        card("订单号", `#${Number(order.order_id)}`),
        card("客户", `${escapeHtml(order.customer_name)}<div class="muted">ID ${Number(order.customer_id)}</div>`),
        card("订单状态", statusBadge(order.status)),
        card("下单时间", formatDate(order.created_at)),
        card("收货地址", escapeHtml(order.shipping_address || "-")),
        card("金额合计", formatMoney(summary.total_amount)),
        card("明细", `${Number(summary.item_lines || 0)} 行 / ${Number(summary.total_quantity || 0)} 件`),
        card("物流状态", order.shipment_status ? statusBadge(order.shipment_status) : '<span class="muted">无</span>'),
      ].join("");

      const canDelete = ["PENDING", "PAID"].includes(order.status) && items.length > 1;
      $("detail-items").innerHTML = items.length ? items.map((item) => `
        <tr>
          <td>${escapeHtml(item.product_name)}</td>
          <td>${escapeHtml(item.sku)}</td>
          <td>${escapeHtml(item.categories || "-")}</td>
          <td>${Number(item.quantity)}</td>
          <td>${formatMoney(item.unit_price)}</td>
          <td>${formatMoney(item.line_amount)}</td>
          <td>
            ${canDelete
              ? `<button class="btn danger small btn-delete-item" type="button" data-order-item-id="${Number(item.order_item_id)}">删除</button>`
              : '<span class="muted">-</span>'}
          </td>
        </tr>
      `).join("") : '<tr><td colspan="7" class="muted">暂无明细</td></tr>';

      $("detail-shipment").innerHTML = order.shipment_id
        ? [
            kv("承运商", escapeHtml(order.carrier || "-")),
            kv("运单号", escapeHtml(order.tracking_no || "-")),
            kv("物流状态", statusBadge(order.shipment_status)),
            kv("发货时间", formatDate(order.shipped_at)),
          ].join("")
        : '<div class="muted">该订单暂无物流单。</div>';

      loading.classList.add("hidden");
      content.classList.remove("hidden");
    } catch (error) {
      loading.textContent = "加载失败";
      showMessage(error.message, "error");
    }
  }

  async function deleteItem(itemId) {
    if (!window.confirm("确定删除这条订单明细？库存会回补。")) return;
    try {
      await apiFetch(`/api/order-items/${itemId}`, { method: "DELETE" });
      showMessage("订单明细已删除，库存已回补。", "ok");
      await loadDetail();
    } catch (error) {
      showMessage(error.message, "error");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("detail-items")?.addEventListener("click", (event) => {
      const button = event.target.closest(".btn-delete-item");
      if (!button) return;
      deleteItem(button.dataset.orderItemId);
    });
    loadDetail();
  });
})();
// IRON RIFF — фронтенд магазина. Всё общение с бэкендом через /api.
const API = "/api";
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (n) => "$" + Number(n).toLocaleString("en-US");

const state = { category: "", products: [], cart: loadCart(), categories: {} };

// ---------- запросы ----------
async function api(path, options = {}) {
  const res = await fetch(API + path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.error || (data.detail && data.detail.map?.((d) => `${d.loc.at(-1)}: ${d.msg}`).join("; ")) || `Ошибка ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

function toast(text, isError = false) {
  const t = $("#toast");
  t.textContent = text;
  t.className = "toast show" + (isError ? " err" : "");
  clearTimeout(t.timer);
  t.timer = setTimeout(() => (t.className = "toast"), 3500);
}

// ---------- картинки товаров (SVG) ----------
function picture(p) {
  const c = p.color;
  if (p.category === "amp") return `<svg viewBox="0 0 200 160"><rect x="10" y="20" width="180" height="130" rx="8" fill="#151515" stroke="${c}" stroke-width="5"/><rect x="22" y="32" width="156" height="28" fill="${c}"/>${[0,1,2,3,4,5].map(i=>`<circle cx="${40+i*24}" cy="46" r="6" fill="#111"/>`).join("")}<rect x="22" y="70" width="156" height="68" fill="url(#g)"/><defs><pattern id="g" width="6" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="#222"/><path d="M0 0L6 6" stroke="#444"/></pattern></defs></svg>`;
  if (p.category === "pedal") return `<svg viewBox="0 0 200 200"><rect x="50" y="20" width="100" height="160" rx="10" fill="${c}" stroke="#000" stroke-width="4"/><circle cx="75" cy="55" r="12" fill="#111"/><circle cx="125" cy="55" r="12" fill="#111"/><circle cx="100" cy="85" r="10" fill="#111"/><rect x="62" y="110" width="76" height="56" rx="6" fill="#222"/><circle cx="100" cy="138" r="14" fill="#bbb"/></svg>`;
  const bass = p.category === "bass", acoustic = p.category === "acoustic";
  const neckLen = bass ? 120 : 100;
  const body = acoustic
    ? `<path d="M100 120c-30 0-45 18-40 40 4 15-12 22-12 45 0 30 25 45 52 45s52-15 52-45c0-23-16-30-12-45 5-22-10-40-40-40z" fill="${c}" stroke="#000" stroke-width="3"/><circle cx="100" cy="180" r="14" fill="#111"/>`
    : `<path d="M88 125 L60 105 L70 145 C50 160 50 215 75 240 C95 255 120 252 135 235 C150 215 148 175 130 150 L150 110 L112 130 Z" fill="${c}" stroke="#000" stroke-width="3"/><rect x="85" y="165" width="30" height="10" fill="#111"/><rect x="85" y="195" width="30" height="10" fill="#111"/><circle cx="125" cy="222" r="5" fill="#ddd"/>`;
  return `<svg viewBox="0 0 200 270"><rect x="94" y="${130-neckLen}" width="12" height="${neckLen+20}" fill="#5a3a1c"/><path d="M90 ${130-neckLen} l-6 -22 h32 l-6 22z" fill="#222"/>${body}<line x1="97" y1="${110-neckLen}" x2="97" y2="230" stroke="#eee" stroke-width=".6"/><line x1="103" y1="${110-neckLen}" x2="103" y2="230" stroke="#eee" stroke-width=".6"/></svg>`;
}

// ---------- каталог ----------
async function loadCategories() {
  state.categories = await api("/categories");
  const all = { "": "Все", ...state.categories };
  $("#categories").innerHTML = Object.entries(all)
    .map(([code, name]) => `<button class="tab ${code === state.category ? "active" : ""}" data-cat="${code}">${esc(name)}</button>`).join("");
  $("#catSelect").innerHTML = Object.entries(state.categories).map(([c, n]) => `<option value="${c}">${esc(n)}</option>`).join("");
}

async function loadProducts() {
  const params = new URLSearchParams({ sort: $("#sort").value });
  if (state.category) params.set("category", state.category);
  if ($("#search").value.trim()) params.set("q", $("#search").value.trim());
  try {
    state.products = await api("/products?" + params);
    renderProducts();
  } catch (e) { toast(e.message, true); }
}

function renderProducts() {
  const box = $("#products");
  if (!state.products.length) { box.innerHTML = `<p class="hero">Ничего не найдено. Тишина — не наш жанр.</p>`; return; }
  box.innerHTML = state.products.map((p) => `
    <article class="card">
      <div class="pic">${picture(p)}</div>
      <div class="body">
        <span class="cat">${esc(p.category_name)}</span>
        <h3>${esc(p.title)}</h3>
        <p class="desc">${esc(p.description)}</p>
        <div class="row"><span class="price">${money(p.price)}</span>
          <span class="stock ${p.stock < 3 ? "low" : ""}">${p.stock ? "в наличии: " + p.stock : "нет в наличии"}</span></div>
        <button class="btn btn-red" data-add="${p.id}" ${p.stock ? "" : "disabled"}>В корзину</button>
      </div>
    </article>`).join("");
}

// ---------- корзина (localStorage) ----------
function loadCart() {
  try { return JSON.parse(localStorage.getItem("cart")) || {}; } catch { return {}; }
}
function saveCart() {
  try { localStorage.setItem("cart", JSON.stringify(state.cart)); } catch {}
  renderCart();
}
function addToCart(id) {
  const p = state.products.find((x) => x.id === id);
  const qty = (state.cart[id]?.qty || 0) + 1;
  if (qty > p.stock) return toast(`На складе только ${p.stock} шт.`, true);
  state.cart[id] = { id, title: p.title, price: p.price, qty, stock: p.stock };
  saveCart();
  toast(`${p.title} — в корзине 🤘`);
}
function changeQty(id, delta) {
  const line = state.cart[id];
  line.qty += delta;
  if (line.qty <= 0) delete state.cart[id];
  else if (line.qty > line.stock) { line.qty = line.stock; toast("Больше нет на складе", true); }
  saveCart();
}
function renderCart() {
  const lines = Object.values(state.cart);
  $("#cartCount").textContent = lines.reduce((s, l) => s + l.qty, 0);
  $("#cartTotal").textContent = money(lines.reduce((s, l) => s + l.qty * l.price, 0));
  $("#cartItems").innerHTML = lines.length ? lines.map((l) => `
    <div class="cart-line"><span>${esc(l.title)}</span>
      <span class="qty"><button class="btn" data-dec="${l.id}">−</button>${l.qty}<button class="btn" data-inc="${l.id}">+</button></span>
      <b>${money(l.qty * l.price)}</b></div>`).join("") : "<p>Корзина пуста</p>";
}

async function checkout(e) {
  e.preventDefault();
  const form = new FormData(e.target);
  const items = Object.values(state.cart).map((l) => ({ product_id: l.id, qty: l.qty }));
  if (!items.length) return toast("Корзина пуста", true);
  try {
    const order = await api("/orders", { method: "POST", body: JSON.stringify({ customer: Object.fromEntries(form), items }) });
    state.cart = {}; saveCart(); e.target.reset();
    $("#cart").classList.remove("open");
    toast(`Заказ #${order.id} на ${money(order.total)} оформлен!`);
    loadProducts();
  } catch (err) { toast(err.message, true); }
}

// ---------- статистика ----------
async function loadStats() {
  try {
    const s = await api("/stats");
    const sold = Object.values(s.categories).reduce((a, c) => a + c.sold_units, 0);
    const stock = Object.values(s.categories).reduce((a, c) => a + c.stock_units, 0);
    $("#statCards").innerHTML = [["Заказов", s.orders_count], ["Выручка", money(s.revenue_total)], ["Продано, шт.", sold], ["На складе, шт.", stock]]
      .map(([k, v]) => `<div class="plate"><b>${v}</b>${k}</div>`).join("");
    $("#chart").src = `${API}/stats/chart.png?t=${Date.now()}`;
  } catch (e) { toast(e.message, true); }
}

// ---------- админка ----------
const adminHeaders = () => ({ "X-Admin-Token": $("#token").value });

async function loadOrders() {
  try {
    const orders = await api("/orders", { headers: adminHeaders() });
    const products = await api("/products");
    $("#orders").innerHTML = `<h3 class="section-title" style="font-size:20px">Заказы</h3>
      <table><tr><th>#</th><th>Дата</th><th>Клиент</th><th>Состав</th><th>Сумма</th></tr>
      ${orders.map((o) => `<tr><td>${o.id}</td><td>${o.created_at.replace("T", " ")}</td><td>${esc(o.customer_name)}<br><small>${esc(o.email)}, ${esc(o.phone)}</small></td>
        <td>${o.lines.map((l) => `${esc(l.title)} × ${l.qty}`).join("<br>")}</td><td>${money(o.total)}</td></tr>`).join("") || "<tr><td colspan=5>Пока нет заказов</td></tr>"}</table>
      <h3 class="section-title" style="font-size:20px;margin-top:24px">Товары</h3>
      <table><tr><th>#</th><th>Товар</th><th>Цена</th><th>Остаток</th><th></th></tr>
      ${products.map((p) => `<tr><td>${p.id}</td><td>${esc(p.title)}</td><td>${money(p.price)}</td><td>${p.stock}</td><td><button class="del" data-del="${p.id}" title="Удалить">✖</button></td></tr>`).join("")}</table>`;
  } catch (e) { toast(e.message, true); }
}

async function addProduct(e) {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  data.price = Number(data.price); data.stock = Number(data.stock);
  try {
    const p = await api("/products", { method: "POST", headers: adminHeaders(), body: JSON.stringify(data) });
    toast(`Добавлен: ${p.title}`); e.target.reset(); loadOrders(); loadProducts();
  } catch (err) { toast(err.message, true); }
}

async function deleteProduct(id) {
  try {
    await api(`/products/${id}`, { method: "DELETE", headers: adminHeaders() });
    toast(`Товар #${id} удалён`); loadOrders(); loadProducts();
  } catch (err) { toast(err.message, true); }
}

// ---------- навигация и события ----------
function showView() {
  const view = (location.hash || "#catalog").slice(1);
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("hidden", v.id !== "view-" + view));
  document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("active", a.dataset.view === view));
  if (view === "stats") loadStats();
}

document.addEventListener("click", (e) => {
  const t = e.target.closest("button");
  if (!t) return;
  if (t.dataset.cat !== undefined) { state.category = t.dataset.cat; loadCategories(); loadProducts(); }
  if (t.dataset.add) addToCart(Number(t.dataset.add));
  if (t.dataset.inc) changeQty(Number(t.dataset.inc), 1);
  if (t.dataset.dec) changeQty(Number(t.dataset.dec), -1);
  if (t.dataset.del) deleteProduct(Number(t.dataset.del));
});
$("#cartBtn").onclick = () => $("#cart").classList.add("open");
$("#closeCart").onclick = () => $("#cart").classList.remove("open");
$("#checkout").onsubmit = checkout;
$("#productForm").onsubmit = addProduct;
$("#loadOrders").onclick = loadOrders;
$("#sort").onchange = loadProducts;
let searchTimer;
$("#search").oninput = () => { clearTimeout(searchTimer); searchTimer = setTimeout(loadProducts, 300); };
window.onhashchange = showView;

loadCategories().then(loadProducts).catch((e) => toast("Сервер недоступен: " + e.message, true));
renderCart();
showView();

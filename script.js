// SLUview — data.json (businesses[], reviews[]) join by businessId
// - On load: show ONE latest review from the first featured business
// - On click a business card: show ALL reviews for that business

const byId = (id) => document.getElementById(id);
const norm = (s) => (s || "").toLowerCase().trim();

function starsDisplay(stars) {
  const n = Number(stars);
  if (Number.isFinite(n) && n > 0) return "★ " + n.toFixed(1);
  if (typeof stars === "string" && stars) return stars;
  return "—";
}

// normalize date like "Sep 15, 2025" or "Jun 12, 2025\n\nSep 22, 2019"
function toEpoch(d) {
  if (!d) return 0;
  const first = String(d).split("\n")[0].trim();
  const t = Date.parse(first);
  return Number.isFinite(t) ? t : 0;
}

// strip "2 photos" etc from reviewer field
function cleanReviewer(s) {
  return String(s || "").split("\n")[0].trim();
}

function reviewEl(r) {
  const wrap = document.createElement("article");
  wrap.className = "review";
  wrap.innerHTML = `
    <div class="row">
      <span class="stars">${starsDisplay(r.stars ?? r.rating ?? r.rating_stars)}</span>
      <span>•</span>
      <span>${(r.date || r.published || "").toString().split("\n")[0]}</span>
      <span>•</span>
      <span>${cleanReviewer(r.reviewer || r.author || "Anonymous")}</span>
    </div>
    <div class="text">${(r.text || r.content || "").toString()}</div>
  `;
  return wrap;
}

function renderReviews(biz, count = Infinity) {
  const box = byId("reviews");
  box.innerHTML = "";
  const list = (biz?.reviews || []).slice(0, count);
  if (!list.length) {
    box.innerHTML = `<article class="review"><div class="text">No reviews available for ${biz?.name || "this business"}.</div></article>`;
    return;
  }
  list.forEach((r) => box.appendChild(reviewEl(r)));
}

function setActiveCard(card) {
  document.querySelectorAll(".featured .card").forEach((c) => c.classList.remove("active"));
  card?.classList.add("active");
}

async function load() {
  // 1) fetch data.json (must be served over http://)
  let data = null;
  try {
    const r = await fetch("data.json", { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    data = await r.json();
  } catch (e) {
    console.error("Could not load data.json:", e);
    byId("reviews").innerHTML = `<article class="review"><div class="text">
      Could not load <b>data.json</b>. Make sure it's next to index.html and use a local server:
      <code>python -m http.server</code>
    </div></article>`;
    return;
  }

  // 2) validate/shape
  const businesses = Array.isArray(data.businesses) ? data.businesses.slice() : [];
  const flatReviews = Array.isArray(data.reviews) ? data.reviews.slice() : [];

  // index businesses by id and name; ensure .reviews array exists
  const byIdMap = new Map();
  const byNameMap = new Map();
  for (const b of businesses) {
    b.reviews = []; // we’ll fill this
    byIdMap.set(String(b.id || "").trim(), b);
    if (b.name) byNameMap.set(norm(b.name), b);
  }

  // 3) attach reviews -> business.reviews by businessId
  for (const r of flatReviews) {
    const bid = String(r.businessId || "").trim();
    const biz = byIdMap.get(bid);
    if (biz) biz.reviews.push(r);
  }

  // 4) sort each business’s reviews by date (desc)
  businesses.forEach((b) => {
    b.reviews.sort((a, b_) => toEpoch(b_.date) - toEpoch(a.date));
  });

  // 5) wire featured cards (names in <h3> must match business.name)
  const cards = document.querySelectorAll(".featured .card");
  cards.forEach((card) => {
    const name = norm(card.querySelector("h3")?.textContent);
    const biz = byNameMap.get(name);
    if (!biz) return;

    card.style.cursor = "pointer";
    card.addEventListener("click", () => {
      setActiveCard(card);
      byId("reviews-title").textContent = `${biz.name} — Reviews`;
      renderReviews(biz, Infinity); // show all for clicked
    });
  });

  // 6) initial view = show ONE latest review from first featured card
  const firstCard = document.querySelector(".featured .card");
  const firstName = norm(firstCard?.querySelector("h3")?.textContent);
  const firstBiz = byNameMap.get(firstName) || businesses[0];

  setActiveCard(firstCard);
  byId("reviews-title").textContent = "Latest Review";
  renderReviews(firstBiz, 1);
}

load();

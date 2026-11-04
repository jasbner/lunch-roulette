// Paste into the browser console on a DoorDash city page, e.g.
// https://www.doordash.com/food-delivery/carrboro-nc-restaurants/
// It copies the restaurant list as JSON; paste that to Claude to refresh Lunch Roulette.
(() => {
  const places = new Map();
  for (const a of document.querySelectorAll('a[href*="/store/"]')) {
    const store = (a.getAttribute("href").match(/-(\d+)\/?(\?|$)/) || [])[1];
    if (!store || places.has(store)) continue;
    let card = a;
    for (let i = 0; i < 8 && card.parentElement; i++) {
      card = card.parentElement;
      if (/\d mi\b/.test(card.innerText) && /\(\d/.test(card.innerText)) break;
    }
    const lines = card.innerText.split("\n").map(s => s.trim()).filter(s => s && !s.startsWith('"'));
    const tags = (lines.find(s => s.startsWith("•")) || "").split("•").map(s => s.trim()).filter(Boolean);
    const mi = parseFloat((card.innerText.match(/([\d.]+) mi\b/) || [])[1]);
    places.set(store, {
      store: Number(store),
      name: lines[0],
      rating: parseFloat(lines[1]) || null,
      reviews: (lines[2] || "").replace(/[()]/g, ""),
      tags,
      mi: isNaN(mi) ? null : mi,
    });
  }
  const json = JSON.stringify([...places.values()], null, 1);
  try { copy(json); console.log(`Copied ${places.size} places to the clipboard.`); }
  catch { console.log(json); }
  return places.size;
})();

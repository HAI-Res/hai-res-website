(function () {
  const STORAGE_KEY = "hai-res-home-news-dismissed-version";
  const aside = document.getElementById("home-news");
  const listEl = document.getElementById("home-news-list");
  const closeBtn = document.querySelector(".home-news__close");
  if (!aside || !listEl) return;

  function hideNews() {
    aside.hidden = true;
    document.querySelector(".home-main")?.classList.add("home-main--no-news");
  }

  function newsVersion(items) {
    return items.map((item) => item.date).join("|");
  }

  function formatDate(iso) {
    if (!iso) return "";
    const [y, m, d] = iso.split("-").map(Number);
    if (!y || !m || !d) return iso;
    return new Date(y, m - 1, d).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function renderItem(item) {
    const li = document.createElement("li");
    li.className = "home-news__item";
    const date = document.createElement("time");
    date.className = "home-news__date";
    date.dateTime = item.date || "";
    date.textContent = formatDate(item.date);
    li.appendChild(date);
    const body = document.createElement("div");
    body.className = "home-news__text";
    body.innerHTML = item.html || "";
    li.appendChild(body);
    return li;
  }

  function showNews(items) {
    listEl.replaceChildren(...items.map(renderItem));
    aside.hidden = items.length === 0;
    if (!aside.hidden) {
      document.querySelector(".home-main")?.classList.remove("home-main--no-news");
    }
  }

  function loadNews() {
    const inline = document.getElementById("home-news-data");
    if (inline) {
      try {
        const data = JSON.parse(inline.textContent);
        if (Array.isArray(data) && data.length > 0) {
          return Promise.resolve(data);
        }
      } catch (_err) {
        /* fall through to fetch */
      }
    }

    return fetch("./data/news.json", { cache: "no-store" }).then((res) =>
      res.ok ? res.json() : []
    );
  }

  loadNews()
    .then((data) => {
      const items = Array.isArray(data) ? data : [];
      if (items.length === 0) {
        hideNews();
        return;
      }

      const version = newsVersion(items);
      if (localStorage.getItem(STORAGE_KEY) === version) {
        hideNews();
        return;
      }

      showNews(items);
      closeBtn?.addEventListener("click", () => {
        hideNews();
        localStorage.setItem(STORAGE_KEY, version);
      });
    })
    .catch(() => {
      hideNews();
    });
})();

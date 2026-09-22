(() => {
  const sections = [...document.querySelectorAll("main section[id], header.hero[id]")];
  const toc = document.getElementById("toc");
  if (!toc) return;

  const label = {
    top: "顶部",
    "sec-position": "定位与评分",
    "sec-pyramid": "评测金字塔",
    "sec-caps": "能力 8 维",
    "sec-hcut": "横切红线",
    "sec-order": "计算顺序",
    "sec-output": "output_type",
    "sec-pred": "谓词与 lawkb",
    "sec-judge": "Judge 与 pass^k",
    "sec-rank": "排名粒度",
    "sec-anti": "防作弊",
    "sec-road": "落地路线",
    "sec-ethics": "边界声明",
  };

  for (const el of sections) {
    const a = document.createElement("a");
    a.href = `#${el.id}`;
    a.textContent = label[el.id] || el.id;
    a.dataset.id = el.id;
    toc.appendChild(a);
  }

  const links = [...toc.querySelectorAll("a")];
  const setActive = (id) => {
    for (const a of links) a.classList.toggle("active", a.dataset.id === id);
  };

  const io = new IntersectionObserver(
    (entries) => {
      const hit = entries
        .filter((e) => e.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (hit) setActive(hit.target.id);
    },
    { rootMargin: "-15% 0px -55% 0px", threshold: [0.1, 0.4] }
  );
  for (const el of sections) io.observe(el);
  setActive(sections[0]?.id || "top");
})();

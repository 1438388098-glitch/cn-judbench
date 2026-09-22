/* Light enhancement only — page must work with JS disabled */
(function () {
  try {
    var links = document.querySelectorAll(".top-nav a");
    if (!links.length || !("IntersectionObserver" in window)) return;

    var map = {};
    var targets = [];
    links.forEach(function (a) {
      var id = (a.getAttribute("href") || "").replace("#", "");
      if (!id) return;
      var el = document.getElementById(id);
      if (!el) return;
      map[id] = a;
      targets.push(el);
    });

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var id = entry.target.id;
          links.forEach(function (a) {
            a.classList.toggle("active", a === map[id]);
          });
        });
      },
      { rootMargin: "-20% 0px -65% 0px", threshold: 0 }
    );

    targets.forEach(function (el) {
      observer.observe(el);
    });
  } catch (e) {
    /* silent — nav highlighting is optional */
  }
})();

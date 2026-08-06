// Animasi ringan bar komposisi tipe file saat dashboard dimuat.
(function () {
  const bars = document.querySelectorAll(".bar-dalam");
  if (!bars.length) return;
  bars.forEach((bar) => {
    const lebar = bar.style.width;
    bar.style.width = "0%";
    bar.style.transition = "width 0.6s ease";
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        bar.style.width = lebar;
      });
    });
  });
})();

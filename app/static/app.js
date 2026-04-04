window.addEventListener("DOMContentLoaded", () => {
  const cards = document.querySelectorAll(".card");
  cards.forEach((card, i) => {
    card.animate(
      [
        { opacity: 0, transform: "translateY(10px)" },
        { opacity: 1, transform: "translateY(0)" }
      ],
      {
        duration: 320,
        delay: i * 70,
        fill: "forwards",
        easing: "ease-out"
      }
    );
  });
});

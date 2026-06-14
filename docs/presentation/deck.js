const slides = Array.from(document.querySelectorAll('.slide'));
const prevButton = document.getElementById('prevSlide');
const nextButton = document.getElementById('nextSlide');
const counter = document.getElementById('slideCounter');
let currentSlide = 0;

function showSlide(index) {
  currentSlide = Math.max(0, Math.min(index, slides.length - 1));
  slides.forEach((slide, slideIndex) => {
    slide.classList.toggle('active', slideIndex === currentSlide);
  });
  counter.textContent = `${currentSlide + 1} / ${slides.length}`;
  prevButton.disabled = currentSlide === 0;
  nextButton.disabled = currentSlide === slides.length - 1;
}

function moveSlide(delta) {
  showSlide(currentSlide + delta);
}

prevButton.addEventListener('click', () => moveSlide(-1));
nextButton.addEventListener('click', () => moveSlide(1));

document.addEventListener('keydown', (event) => {
  if (event.key === 'ArrowRight' || event.key === 'PageDown') moveSlide(1);
  if (event.key === 'ArrowLeft' || event.key === 'PageUp') moveSlide(-1);
  if (event.key === 'Home') showSlide(0);
  if (event.key === 'End') showSlide(slides.length - 1);
});

const requestedSlide = new URLSearchParams(window.location.search).get('slide');
const initialSlide = requestedSlide
  ? slides.findIndex((slide) => slide.dataset.slideId === requestedSlide)
  : 0;

showSlide(initialSlide >= 0 ? initialSlide : 0);

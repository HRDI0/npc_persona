const slides = Array.from(document.querySelectorAll('.slide'));
const prevButton = document.getElementById('prevSlide');
const nextButton = document.getElementById('nextSlide');
const slideCounter = document.getElementById('slideCounter');

let currentSlide = 0;

function showSlide(index) {
  currentSlide = (index + slides.length) % slides.length;

  slides.forEach((slide, slideIndex) => {
    slide.classList.toggle('is-active', slideIndex === currentSlide);
  });

  slideCounter.textContent = `${currentSlide + 1} / ${slides.length}`;
}

function nextSlide() {
  showSlide(currentSlide + 1);
}

function prevSlide() {
  showSlide(currentSlide - 1);
}

nextButton.addEventListener('click', nextSlide);
prevButton.addEventListener('click', prevSlide);

document.addEventListener('keydown', (event) => {
  if (event.key === 'ArrowRight') {
    nextSlide();
  }

  if (event.key === 'ArrowLeft') {
    prevSlide();
  }
});

showSlide(currentSlide);

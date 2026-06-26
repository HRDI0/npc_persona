const slides = Array.from(document.querySelectorAll('.slide'));
const prevButton = document.getElementById('prevSlide');
const nextButton = document.getElementById('nextSlide');
const slideCounter = document.getElementById('slideCounter');

let currentSlide = 0;

function slideIndexFromHash() {
  const hashValue = decodeURIComponent(window.location.hash.slice(1));
  if (!hashValue) {
    return 0;
  }

  const numericIndex = Number.parseInt(hashValue, 10);
  if (Number.isInteger(numericIndex) && numericIndex >= 1 && numericIndex <= slides.length) {
    return numericIndex - 1;
  }

  const matchedIndex = slides.findIndex((slide) => slide.dataset.slideId === hashValue);
  return matchedIndex >= 0 ? matchedIndex : 0;
}

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

window.addEventListener('hashchange', () => {
  showSlide(slideIndexFromHash());
});

showSlide(slideIndexFromHash());

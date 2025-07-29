document.addEventListener('DOMContentLoaded', () => {
    const container = document.querySelector('.container');
    const prompt = document.querySelector('.prompt');

    setTimeout(() => {
        prompt.style.animation = "fadeIn 2s forwards 3s, blink 1s infinite 3s";
        container.addEventListener('click', () => {
            // window.location.href = 'main.html';
        });
    }, 3000);
});

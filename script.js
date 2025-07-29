document.addEventListener('DOMContentLoaded', () => {
    const container = document.querySelector('.container');
    const prompt = document.querySelector('.prompt');

    setTimeout(() => {
        prompt.style.opacity = 1;
        container.addEventListener('click', () => {
            // Redirect to the main page
            window.location.href = 'main.html';
        });
    }, 3000);
});

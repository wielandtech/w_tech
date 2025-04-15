document.addEventListener('DOMContentLoaded', function() {
    const likeButtons = document.querySelectorAll('.like-button');
    
    likeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const postId = this.dataset.id;
            const action = this.dataset.action;

            fetch('/blog/like/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: `id=${postId}&action=${action}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    const likes = data.likes;
                    this.dataset.action = action === 'like' ? 'unlike' : 'like';
                    this.textContent = action === 'like' ? '❤️' : '🤍';
                    document.querySelector(`#likes-count-${postId}`).textContent = likes;
                }
            });
        });
    });

    function getCookie(name) {
        let value = `; ${document.cookie}`;
        let parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }
});
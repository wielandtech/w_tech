document.addEventListener('DOMContentLoaded', function() {
    const likeButtons = document.querySelectorAll('.like-button');
    
    likeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const postId = this.dataset.id;
            const action = this.dataset.action;

            // Disable button during request
            this.disabled = true;

            fetch('/blog/like/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: `id=${postId}&action=${action}`
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'ok') {
                    const likes = data.likes;
                    this.dataset.action = action === 'like' ? 'unlike' : 'like';
                    this.textContent = action === 'like' ? '❤️' : '🤍';
                    document.querySelector(`#likes-count-${postId}`).textContent = likes;
                } else {
                    throw new Error(data.message || 'Like action failed');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                // Revert button state on error
                this.textContent = action === 'unlike' ? '❤️' : '🤍';
                alert('Could not process like action. Please try again.');
            })
            .finally(() => {
                // Re-enable button after request
                this.disabled = false;
            });
        });
    });

    function getCookie(name) {
        let value = `; ${document.cookie}`;
        let parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }
});
document.addEventListener('DOMContentLoaded', function() {
    console.log('Likes.js loaded');
    const likeButtons = document.querySelectorAll('.like-button');
    console.log('Found like buttons:', likeButtons.length);

    likeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.dataset.id;
            const action = this.dataset.action;

            fetch(`/blog/post/${postId}/${action}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    // Update like count
                    const likesCount = document.querySelector(`#likes-count-${postId}`);
                    if (likesCount) {
                        likesCount.textContent = data.likes;
                    }
                    // Toggle button state
                    this.dataset.action = action === 'like' ? 'unlike' : 'like';
                    this.innerHTML = action === 'like' ? '❤️' : '🤍';
                }
            })
            .catch(error => {
                console.error('Error updating like state:', error);
                alert('Failed to process like action. Please try again.');
            });
        });
    });
});

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
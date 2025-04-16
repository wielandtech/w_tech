document.addEventListener('DOMContentLoaded', function() {
    const likeButtons = document.querySelectorAll('.like-button');
    
    likeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const url = '/blog/like/';
            const postId = this.dataset.id;
            const action = this.dataset.action;
            
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    'id': postId,
                    'action': action
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    const likeIcon = this.querySelector('.like-icon');
                    const likesCount = this.querySelector('.likes-count');
                    
                    if (action === 'like') {
                        this.dataset.action = 'unlike';
                        likeIcon.textContent = '❤️';
                    } else {
                        this.dataset.action = 'like';
                        likeIcon.textContent = '🤍';
                    }
                    
                    likesCount.textContent = data.likes;
                }
            });
        });
    });
});

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
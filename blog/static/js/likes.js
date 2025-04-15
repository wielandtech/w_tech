document.addEventListener('DOMContentLoaded', function() {
    console.log('Likes.js loaded');
    const likeButtons = document.querySelectorAll('.like-button');
    console.log('Found like buttons:', likeButtons.length);
    
    likeButtons.forEach(button => {
        // Initialize button state based on data attributes
        const isLiked = button.dataset.initialState === 'true';
        const action = isLiked ? 'unlike' : 'like';
        const icon = isLiked ? '❤️' : '🤍';
        
        // Set initial state
        button.dataset.action = action;
        if (!button.textContent.trim()) {
            button.textContent = icon;
        }
        
        console.log('Button initialized:', {
            postId: button.dataset.id,
            action: action,
            isLiked: isLiked
        });

        button.addEventListener('click', async function(e) {
            console.log('Like button clicked:', this.dataset.id, 'Current action:', this.dataset.action);
            e.preventDefault();
            
            // Check if user is authenticated
            if (!document.querySelector('meta[name="user-authenticated"]')) {
                window.location.href = '/login/';
                return;
            }

            const postId = this.dataset.id;
            const action = this.dataset.action;
            const originalText = this.textContent;
            const likesCount = document.querySelector(`#likes-count-${postId}`);

            // Disable button and show loading state
            this.disabled = true;
            this.textContent = '...';

            try {
                const csrfToken = getCookie('csrftoken');
                if (!csrfToken) {
                    throw new Error('CSRF token not found');
                }

                const response = await fetch('/blog/like/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: `id=${postId}&action=${action}`
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                
                if (data.status === 'ok' && typeof data.likes === 'number') {
                    // Update button state and persist in dataset
                    const newAction = action === 'like' ? 'unlike' : 'like';
                    this.dataset.action = newAction;
                    this.textContent = newAction === 'like' ? '🤍' : '❤️';
                    
                    // Update likes count
                    if (likesCount) {
                        likesCount.textContent = data.likes;
                    }

                    console.log('Like state updated:', {
                        postId,
                        newAction,
                        likes: data.likes
                    });
                } else {
                    throw new Error(data.message || 'Invalid response format');
                }
            } catch (error) {
                console.error('Like action failed:', error);
                // Revert to original state
                this.textContent = originalText;
                alert('Failed to process like action. Please try again.');
            } finally {
                this.disabled = false;
            }
        });
    });

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return null;
    }
});
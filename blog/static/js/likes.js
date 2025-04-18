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

// Add CSRF token to jQuery AJAX requests
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
});

document.addEventListener('DOMContentLoaded', function() {
    $(document).on('click', '.like-button', function(e) {
        e.preventDefault();
        var $button = $(this);
        var $icon = $button.find('.like-icon');
        var $count = $button.find('.likes-count');
        var action = $button.data('action');
        var currentLikes = parseInt($count.text());
        var postUrl = $button.data('url');

        // Disable button temporarily to prevent double-clicks
        $button.prop('disabled', true);
        
        $.post(postUrl, {
            id: $button.data('id'),
            action: action
        })
        .done(function(data) {
            if (data['status'] === 'ok') {
                // Update count based on the action we just performed
                if (action === 'like') {
                    $count.text(currentLikes + 1);
                    $icon.text('❤️');
                    $button.data('action', 'unlike');
                } else {
                    $count.text(currentLikes - 1);
                    $icon.text('🤍');
                    $button.data('action', 'like');
                }
            }
        })
        .always(function() {
            // Re-enable button after request completes
            $button.prop('disabled', false);
        });
    });
});
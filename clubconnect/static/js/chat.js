document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh notification and message badges in navbar
    function updateNavbarBadges() {
        // Update notification badge
        fetch('/ajax/unread_notifications_count/')
            .then(response => response.json())
            .then(data => {
                const notificationBadge = document.querySelector('.notification-badge');
                if (data.unread_count > 0) {
                    if (notificationBadge) {
                        notificationBadge.textContent = data.unread_count;
                        notificationBadge.style.display = 'inline';
                    } else {
                        // Create badge if it doesn't exist
                        const notificationIcon = document.querySelector('.notification-icon');
                        if (notificationIcon) {
                            const badge = document.createElement('span');
                            badge.className = 'notification-badge';
                            badge.textContent = data.unread_count;
                            notificationIcon.appendChild(badge);
                        }
                    }
                } else {
                    if (notificationBadge) {
                        notificationBadge.style.display = 'none';
                    }
                }
            })
            .catch(error => console.error('Error fetching notifications:', error));

        // Update message badge
        fetch('/ajax/unread_messages_count/')
            .then(response => response.json())
            .then(data => {
                const messageBadgeNav = document.querySelector('.message-icon .message-badge');
                if (data.unread_count > 0) {
                    if (messageBadgeNav) {
                        messageBadgeNav.textContent = data.unread_count;
                        messageBadgeNav.style.display = 'inline';
                    } else {
                        // Create badge if it doesn't exist
                        const messageIcon = document.querySelector('.message-icon');
                        if (messageIcon) {
                            const badge = document.createElement('span');
                            badge.className = 'message-badge';
                            badge.textContent = data.unread_count;
                            messageIcon.appendChild(badge);
                        }
                    }
                } else {
                    if (messageBadgeNav) {
                        messageBadgeNav.style.display = 'none';
                    }
                }
            })
            .catch(error => console.error('Error fetching messages:', error));
    }

    // Update badges every 5 seconds
    setInterval(updateNavbarBadges, 5000);
    // Initial update
    updateNavbarBadges();

    const userList = document.getElementById('user-list');
    const chatWindow = document.getElementById('chat-window');
    const chatHeader = document.getElementById('chat-header');
    const chatMessages = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const sendMessageBtn = document.getElementById('send-message-btn');
    const userSearch = document.getElementById('user-search');

    if (userList) {
        let selectedUserId = null;
        let currentUserId = null;
        let currentUserUsername = null;

        // Get current user ID and username from data attributes
        const currentUserElement = document.getElementById('current-user-data');
        if (currentUserElement) {
            currentUserId = currentUserElement.dataset.userId;
            currentUserUsername = currentUserElement.dataset.userUsername;
        }

        userList.addEventListener('click', function(event) {
            const clickedItem = event.target.closest('.list-group-item');
            if (clickedItem) {
                event.preventDefault();
                selectedUserId = clickedItem.dataset.userId;
                const selectedUserName = clickedItem.querySelector('h5').textContent.trim();
                if (chatHeader) {
                    chatHeader.textContent = `Chat with ${selectedUserName}`;
                }
                document.getElementById('no-chat-selected').style.display = 'none';
                document.getElementById('chat-window').style.display = 'block';
                loadMessages(selectedUserId);
            }
        });

        if (userSearch) {
            userSearch.addEventListener('keyup', function() {
                const searchTerm = userSearch.value.toLowerCase();
                const users = userList.querySelectorAll('.list-group-item');
                users.forEach(user => {
                    const username = user.textContent.toLowerCase();
                    if (username.includes(searchTerm)) {
                        user.style.display = 'block';
                    } else {
                        user.style.display = 'none';
                    }
                });
            });
        }

        if (chatWindow && messageInput && sendMessageBtn) {
            function loadMessages(userId) {
                fetch(`/ajax/messages/${userId}/`)
                    .then(response => response.json())
                    .then(data => {
                        chatMessages.innerHTML = '';
                        data.messages.forEach(message => {
                            const messageElement = document.createElement('div');
                            messageElement.classList.add('message');
                            messageElement.dataset.messageId = message.id;

                            if (message.sender === currentUserUsername) {
                                messageElement.classList.add('sent');
                            } else {
                                messageElement.classList.add('received');
                            }

                            let messageHTML = `<p>${message.content}</p><small>${new Date(message.created_at).toLocaleString()}</small>`;

                            if (message.sender === currentUserUsername) {
                                messageHTML += `
                                    <div class="message-actions">
                                        <div class="dots-menu">...</div>
                                        <div class="actions-dropdown">
                                            <a href="#" class="edit-btn">Edit</a>
                                            <a href="#" class="unsend-btn">Unsend</a>
                                        </div>
                                    </div>
                                `;
                            }

                            messageElement.innerHTML = messageHTML;
                            chatMessages.appendChild(messageElement);
                        });
                        chatWindow.style.display = 'block';
                        chatMessages.scrollTop = chatMessages.scrollHeight;

                        // Add event listeners for message actions
                        addMessageActionListeners();
                        
                        // Mark messages as read
                        markMessagesAsRead(userId);
                    });
            }

            function addMessageActionListeners() {
                chatMessages.querySelectorAll('.dots-menu').forEach(menu => {
                    menu.addEventListener('click', function(event) {
                        event.stopPropagation();
                        const dropdown = this.nextElementSibling;
                        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
                    });
                });

                chatMessages.querySelectorAll('.edit-btn').forEach(btn => {
                    btn.addEventListener('click', function(event) {
                        event.preventDefault();
                        const messageElement = this.closest('.message');
                        const messageId = messageElement.dataset.messageId;
                        const p = messageElement.querySelector('p');
                        const currentContent = p.textContent;
                        
                        const input = document.createElement('input');
                        input.type = 'text';
                        input.value = currentContent;
                        
                        p.replaceWith(input);
                        input.focus();

                        input.addEventListener('blur', function() {
                            const newContent = this.value;
                            if (newContent.trim() !== '' && newContent !== currentContent) {
                                editMessage(messageId, newContent);
                            } else {
                                p.textContent = currentContent;
                                input.replaceWith(p);
                            }
                        });

                        input.addEventListener('keypress', function(e) {
                            if (e.key === 'Enter') {
                                this.blur();
                            }
                        });
                    });
                });

                chatMessages.querySelectorAll('.unsend-btn').forEach(btn => {
                    btn.addEventListener('click', function(event) {
                        event.preventDefault();
                        const messageElement = this.closest('.message');
                        const messageId = messageElement.dataset.messageId;
                        unsendMessage(messageId);
                    });
                });

                document.addEventListener('click', function() {
                    chatMessages.querySelectorAll('.actions-dropdown').forEach(dropdown => {
                        dropdown.style.display = 'none';
                    });
                });
            }

            function editMessage(messageId, newContent) {
                fetch(`/ajax/edit_message/${messageId}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({ content: newContent })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'Message edited') {
                        loadMessages(selectedUserId);
                    }
                });
            }

            function unsendMessage(messageId) {
                fetch(`/ajax/unsend_message/${messageId}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'Message unsent') {
                        loadMessages(selectedUserId);
                    }
                });
            }

            function markMessagesAsRead(userId) {
                fetch(`/ajax/mark_messages_as_read/${userId}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                }).then(() => {
                    // After marking messages as read, check for new messages again to update the UI
                    checkForNewMessages();
                });
            }

            function checkForNewMessages() {
                fetch(`/ajax/unread_messages_count/`)
                    .then(response => response.json())
                    .then(data => {
                        const messageBadge = document.querySelector('.message-badge');
                        if (data.unread_count > 0) {
                            if (messageBadge) {
                                messageBadge.textContent = data.unread_count;
                                messageBadge.style.display = 'inline';
                            }
                        } else {
                            if (messageBadge) {
                                messageBadge.style.display = 'none';
                            }
                        }

                        // Reset all user badges first
                        const userItems = userList.querySelectorAll('.list-group-item');
                        userItems.forEach(item => {
                            const badge = item.querySelector('.badge.bg-success');
                            if (badge) {
                                badge.style.display = 'none';
                                badge.textContent = '';
                            }
                        });

                        // Update individual user unread counts
                        if (data.unread_senders) {
                            for (const senderId in data.unread_senders) {
                                const userItem = userList.querySelector(`[data-user-id="${senderId}"]`);
                                if (userItem) {
                                    const badge = userItem.querySelector('.badge.bg-success');
                                    const unreadCount = data.unread_senders[senderId];
                                    if (badge && unreadCount > 0) {
                                        badge.textContent = unreadCount;
                                        badge.style.display = 'inline';
                                    }
                                }
                            }
                        }
                    })
                    .catch(error => console.error('Error fetching unread messages:', error));
            }

            function sendMessage() {
                const content = messageInput.value;
                if (content.trim() === '' || !selectedUserId) {
                    return;
                }

                fetch('/ajax/send_message/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        receiver_id: selectedUserId,
                        content: content
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'Message sent') {
                        messageInput.value = '';
                        loadMessages(selectedUserId);
                    }
                });
            }

            if (sendMessageBtn) {
                sendMessageBtn.addEventListener('click', sendMessage);
            }

            if (messageInput) {
                messageInput.addEventListener('keypress', function (e) {
                    if (e.key === 'Enter') {
                        sendMessage();
                    }
                });
            }

            // Periodically check for new messages and reload active conversation
            setInterval(function() {
                checkForNewMessages();
                // Auto-refresh active conversation if one is selected
                if (selectedUserId) {
                    loadMessages(selectedUserId);
                }
            }, 3000); // Refresh every 3 seconds

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
        }
    }
});
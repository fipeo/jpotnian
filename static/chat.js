document.addEventListener('DOMContentLoaded', () => {
    const socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

    const form = document.getElementById('chat-form');
    const messageInput = document.getElementById('message');
    const chatMessages = document.getElementById('chat-messages');

    form.addEventListener('submit', event => {
        event.preventDefault();
        const message = messageInput.value;

        if (message.trim() !== '') {
            socket.send(message);  // Enviar el mensaje al servidor
            messageInput.value = '';
        }
    });

    socket.on('message', data => {
        const msgElement = document.createElement('div');
        msgElement.classList.add('chat-message');
        msgElement.innerHTML = `<strong>${data.username}</strong> [${data.timestamp}]: ${data.message}`;
        chatMessages.appendChild(msgElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;  // Hacer scroll automáticamente
    });
});

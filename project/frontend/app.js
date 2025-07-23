const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");

const ws = new WebSocket("ws://localhost:8000/ws");

ws.onmessage = (event) => {
    const message = document.createElement("div");
    message.textContent = event.data;
    chatMessages.appendChild(message);
};

sendButton.addEventListener("click", () => {
    const message = chatInput.value;
    ws.send(message);
    chatInput.value = "";
});
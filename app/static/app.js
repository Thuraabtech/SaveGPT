const promptInput = document.getElementById("prompt");
const submitBtn = document.getElementById("submitBtn");
const statusNode = document.getElementById("status");
const tierNode = document.getElementById("tier");
const responseNode = document.getElementById("response");

const apiUrl = window.PROMPT_ROUTER_API_URL || "";

function setStatus(message) {
  statusNode.textContent = message;
}

submitBtn.addEventListener("click", async () => {
  const prompt = promptInput.value.trim();
  if (!prompt) {
    setStatus("Enter a prompt first.");
    return;
  }
  if (!apiUrl) {
    setStatus("Set window.PROMPT_ROUTER_API_URL before using the UI.");
    return;
  }

  submitBtn.disabled = true;
  setStatus("Routing prompt...");
  tierNode.textContent = "-";
  responseNode.textContent = "Working...";

  try {
    const response = await fetch(`${apiUrl}/prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Request failed");
    }

    tierNode.textContent = data.tier;
    responseNode.textContent = data.response;
    setStatus("Done.");
  } catch (error) {
    tierNode.textContent = "-";
    responseNode.textContent = error.message;
    setStatus("Request failed.");
  } finally {
    submitBtn.disabled = false;
  }
});

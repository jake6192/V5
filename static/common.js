// --- Config ---
const PIN_CODE = "1234";  // Stored centrally

// --- State ---
let pinSuccessCallback = null, pinModalIsOpen = false;
let pinModal, pinInput, submitPin, pinError;

// --- Trigger PIN Modal ---
function triggerPin(callback) {
  pinSuccessCallback = callback;
  pinModal.style.display = "flex";
  pinInput.value = "";
  pinError.style.display = "none";
  pinInput.focus();
  pinModalIsOpen = true;
}

// --- Handle PIN Submission ---
function setupPinSubmissionHandler() {
  submitPin.addEventListener("click", () => {
    if (pinInput.value.trim() === PIN_CODE) {
      pinModal.style.display = "none";
      if (typeof pinSuccessCallback === "function") {
        pinModalIsOpen = false;
        pinSuccessCallback();
      }
    } else {
      pinError.style.display = "block";
      pinModal.classList.remove("shake"); // retrigger animation
      void pinModal.offsetWidth;
      pinModal.classList.add("shake");
    }
  });
  
  pinInput.addEventListener("keydown", e => {
    if (e.key === "Enter") submitPin.click();
  });

  window.addEventListener("click", e => {
    if (pinModalIsOpen && !pinModal.querySelector(".pin-modal-content").contains(e.target) && e.target.id != "triggerPin") {
      pinModal.style.display = "none";
      pinInput.value = "";
      pinError.innerText = "";
      pinModalIsOpen = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  pinModal = document.getElementById("pinModal");
  pinInput = document.getElementById("pinInput");
  submitPin = document.getElementById("submitPin");
  pinError = document.getElementById("pinError");
  setupPinSubmissionHandler();
});

document.addEventListener("DOMContentLoaded", () => {
  const button = document.getElementById("action-btn");
  
  button.addEventListener("click", () => {
    alert("Tombol diklik!");
    
    // Contoh mengirim pesan ke background script
    browser.runtime.sendMessage({ action: "buttonClicked" })
      .then(response => {
        console.log("Respon dari background:", response);
      })
      .catch(error => {
        console.error("Error:", error);
      });
  });
});

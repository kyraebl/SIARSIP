document.addEventListener("DOMContentLoaded", () => {
  const tableBody = document.querySelector("#result_list tbody");
  if (!tableBody) return;

  let draggedRow = null;

  tableBody.addEventListener("dragstart", (event) => {
    const handle = event.target.closest(".kategori-drag-handle");
    if (!handle) {
      event.preventDefault();
      return;
    }

    draggedRow = handle.closest("tr");
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", handle.dataset.id);
    draggedRow.classList.add("opacity-50");
  });

  tableBody.addEventListener("dragend", () => {
    draggedRow?.classList.remove("opacity-50");
    draggedRow = null;
  });

  tableBody.addEventListener("dragover", (event) => {
    const targetRow = event.target.closest("tr");
    if (!draggedRow || !targetRow || targetRow === draggedRow) return;

    event.preventDefault();
    const insertAfter = event.clientY > targetRow.getBoundingClientRect().top
      + targetRow.getBoundingClientRect().height / 2;
    tableBody.insertBefore(draggedRow, insertAfter ? targetRow.nextSibling : targetRow);
  });

  tableBody.addEventListener("drop", async (event) => {
    if (!draggedRow) return;
    event.preventDefault();

    const ids = [...tableBody.querySelectorAll(".kategori-drag-handle")]
      .map((handle) => Number(handle.dataset.id));
    const url = draggedRow.querySelector(".kategori-drag-handle").dataset.url;
    const csrfToken = document.querySelector(
      '#changelist-form input[name="csrfmiddlewaretoken"]',
    )?.value;

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ ids }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Urutan kategori gagal disimpan.");
      window.location.reload();
    } catch (error) {
      window.alert(error.message || "Urutan kategori gagal disimpan.");
      window.location.reload();
    }
  });
});

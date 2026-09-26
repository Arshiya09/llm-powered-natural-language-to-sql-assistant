function setQuery(text) {
  document.getElementById("queryInput").value = text;
  runQuery();
}

async function runQuery() {
  const input = document.getElementById("queryInput");
  const query = input.value.trim();
  if (!query) return;

  const loadingEl = document.getElementById("loading");
  const errorCard = document.getElementById("errorCard");
  const resultsArea = document.getElementById("resultsArea");
  const submitBtn = document.getElementById("submitBtn");

  // Reset state
  errorCard.classList.add("hidden");
  resultsArea.classList.add("hidden");
  loadingEl.classList.remove("hidden");
  submitBtn.disabled = true;

  try {
    const res = await fetch("/api/v1/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail?.message || data.detail || "Query execution failed");
    }

    // Render strategy & SQL
    document.getElementById("explanationText").innerText = data.explanation;
    document.getElementById("sqlCode").innerText = data.sanitized_sql;
    document.getElementById("execStats").innerText = `⚡ ${data.execution_time_ms}ms • AST Validated`;

    // Render Table
    const tableHead = document.getElementById("tableHead");
    const tableBody = document.getElementById("tableBody");
    tableHead.innerHTML = "";
    tableBody.innerHTML = "";

    document.getElementById("rowCount").innerText = data.row_count;

    if (data.columns && data.columns.length > 0) {
      const headerRow = document.createElement("tr");
      data.columns.forEach(col => {
        const th = document.createElement("th");
        th.innerText = col;
        headerRow.appendChild(th);
      });
      tableHead.appendChild(headerRow);

      data.data.forEach(row => {
        const tr = document.createElement("tr");
        data.columns.forEach(col => {
          const td = document.createElement("td");
          td.innerText = row[col] !== null && row[col] !== undefined ? row[col] : "-";
          tr.appendChild(td);
        });
        tableBody.appendChild(tr);
      });
    }

    resultsArea.classList.remove("hidden");
  } catch (err) {
    document.getElementById("errorText").innerText = err.message;
    errorCard.classList.remove("hidden");
  } finally {
    loadingEl.classList.add("hidden");
    submitBtn.disabled = false;
  }
}

// Support Enter key press
document.getElementById("queryInput").addEventListener("keypress", function (e) {
  if (e.key === "Enter") {
    runQuery();
  }
});

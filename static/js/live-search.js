// Live search: as you type, fetch just the results for the current query and
// swap them in, keeping focus in the box and the URL shareable. Without
// JavaScript the form still submits normally.
(function () {
    document.querySelectorAll("form[data-live-search]").forEach((form) => {
        const target = document.getElementById(form.dataset.liveSearch);
        const input = form.querySelector('input[type="search"]');
        const status = document.querySelector("p[data-live-status]");
        if (!target || !input) return;

        let timer = null;
        let controller = null;
        let last = new URLSearchParams(new FormData(form)).toString();

        async function search() {
            const params = new URLSearchParams(new FormData(form));
            if (!params.get("q")) params.delete("q");
            const query = params.toString();
            if (query === last) return;
            last = query;

            if (controller) controller.abort();
            controller = new AbortController();
            target.setAttribute("aria-busy", "true");
            const url = `${form.getAttribute("action") || location.pathname}${query ? `?${query}` : ""}`;
            try {
                const response = await fetch(url, {
                    headers: { "X-Live-Search": "1" },
                    signal: controller.signal,
                });
                if (!response.ok) throw new Error(response.statusText);
                target.innerHTML = await response.text();
                const count = target.querySelector("template[data-live-status]");
                if (status && count) status.textContent = count.content.textContent.trim();
                history.replaceState(null, "", url);
            } catch (error) {
                if (error.name !== "AbortError") form.submit();
            } finally {
                target.setAttribute("aria-busy", "false");
            }
        }

        input.addEventListener("input", () => {
            clearTimeout(timer);
            timer = setTimeout(search, 200);
        });
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            clearTimeout(timer);
            search();
        });
    });
})();

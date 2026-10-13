// Live search component. Any <form data-live-search="<results id>"> (rendered
// by the {% livesearch %} tag) refreshes the matching results region as you
// type, or straight away when a filter <select> changes. The view (using
// LiveSearchMixin) returns just the results fragment when asked with the
// X-Live-Search header. Without JavaScript the form submits normally.
(function () {
    const DELAY = 200;

    function liveSearch(form) {
        const targetId = form.dataset.liveSearch;
        const target = document.getElementById(targetId);
        const status = document.querySelector(`[data-live-status="${targetId}"]`);
        if (!target) return;

        let timer = null;
        let controller = null;
        let last = queryString();

        function queryString() {
            const params = new URLSearchParams(new FormData(form));
            for (const [key, value] of [...params]) {
                if (!value) params.delete(key);
            }
            return params.toString();
        }

        async function refresh() {
            const query = queryString();
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
                const fragment = document.createElement("template");
                fragment.innerHTML = await response.text();
                const count = fragment.content.querySelector("template[data-live-count]");
                if (count) {
                    if (status) status.textContent = count.content.textContent.trim();
                    count.remove();
                }
                target.replaceChildren(fragment.content);
                history.replaceState(null, "", url);
            } catch (error) {
                if (error.name !== "AbortError") form.submit();
            } finally {
                target.setAttribute("aria-busy", "false");
            }
        }

        form.addEventListener("input", (event) => {
            if (event.target.tagName === "SELECT") return;
            clearTimeout(timer);
            timer = setTimeout(refresh, DELAY);
        });
        form.addEventListener("change", (event) => {
            if (event.target.tagName !== "SELECT") return;
            clearTimeout(timer);
            refresh();
        });
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            clearTimeout(timer);
            refresh();
        });
    }

    document.querySelectorAll("form[data-live-search]").forEach(liveSearch);
})();

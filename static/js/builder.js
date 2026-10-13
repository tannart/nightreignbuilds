// Builder niceties. The server checks everything again, so this only has to
// make the form pleasant: filter vessels to the chosen Nightfarer, colour
// the slots, hide relics that won't fit, and show/hide optional parts.
(function () {
    const vessel = document.getElementById("id_vessel");
    const deep = document.getElementById("id_deep_of_night");
    const deepPanel = document.getElementById("deep-slots");
    const farers = document.querySelectorAll('input[name="nightfarer"]');

    function slotColours() {
        const option = vessel && vessel.selectedOptions[0];
        return option && option.dataset.slots ? option.dataset.slots.split(",") : [];
    }

    function filterVessels() {
        if (!vessel) return;
        const chosen = document.querySelector('input[name="nightfarer"]:checked');
        const id = chosen ? chosen.value : null;
        for (const option of vessel.options) {
            if (!option.value) continue;
            const usable = !id || !option.dataset.nightfarer || option.dataset.nightfarer === id;
            option.hidden = !usable;
            option.disabled = !usable;
            if (!usable && option.selected) vessel.value = "";
        }
        colourSlots();
    }

    // Rebuild a select from its original options, keeping those that pass.
    // Safari ignores `hidden` on options, so they have to be removed.
    const originals = new WeakMap();
    function showOptions(select, keep) {
        if (!originals.has(select)) {
            originals.set(select, Array.from(select.children, (node) => node.cloneNode(true)));
        }
        const value = select.value;
        const nodes = [];
        for (const node of originals.get(select)) {
            if (node.tagName === "OPTGROUP") {
                const options = Array.from(node.children).filter(keep);
                if (!options.length) continue;
                const group = node.cloneNode(false);
                group.append(...options.map((option) => option.cloneNode(true)));
                nodes.push(group);
            } else if (keep(node)) {
                nodes.push(node.cloneNode(true));
            }
        }
        select.replaceChildren(...nodes);
        select.value = value;
        if (select.selectedIndex === -1) select.value = "";
    }

    function colourSlots() {
        const colours = slotColours();
        document.querySelectorAll("select[data-slot]").forEach((select) => {
            const colour = colours[Number(select.dataset.slot) - 1];
            const fits = (c) => !colour || colour === "white" || c === colour;
            const gem = document.querySelector(`[data-gem-for="${select.id}"]`);
            if (gem) gem.className = `gem ${colour || "white empty"}`;
            showOptions(select, (option) => !option.dataset.colour || fits(option.dataset.colour));
            // The custom relic's colour picker follows the same rule.
            const prefix = select.name.replace(/-relic$/, "");
            const custom = document.querySelector(`select[name="${prefix}-custom_colour"]`);
            if (custom) showOptions(custom, (option) => !option.value || fits(option.value));
        });
    }

    function toggleCustom(checkbox) {
        const panel = document.querySelector(`[data-custom-for="${checkbox.id}"]`);
        const select = document.querySelector(`select[name="${checkbox.name.replace(/-custom$/, "-relic")}"]`);
        if (panel) panel.hidden = !checkbox.checked;
        if (select) {
            select.disabled = checkbox.checked;
            if (checkbox.checked) select.value = "";
        }
    }

    farers.forEach((radio) => radio.addEventListener("change", filterVessels));
    if (vessel) vessel.addEventListener("change", colourSlots);
    if (deep && deepPanel) {
        deep.addEventListener("change", () => { deepPanel.hidden = !deep.checked; });
    }
    document.querySelectorAll('input[type="checkbox"][name$="-custom"]').forEach((box) => {
        box.addEventListener("change", () => toggleCustom(box));
        toggleCustom(box);
    });
    if (vessel) filterVessels();

    // "Copy link" on a shared build.
    document.querySelectorAll("[data-copy]").forEach((button) => {
        button.addEventListener("click", async () => {
            const input = document.getElementById(button.dataset.copy);
            try {
                await navigator.clipboard.writeText(input.value);
            } catch {
                input.select();
                document.execCommand("copy");
            }
            const label = button.textContent;
            button.textContent = "Copied!";
            setTimeout(() => { button.textContent = label; }, 1600);
        });
    });
})();

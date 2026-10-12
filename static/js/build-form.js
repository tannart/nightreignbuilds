// Colours each slot to match the chosen vessel and greys out relics that
// won't fit it (white slots take anything). The server re-checks all of this.
(function () {
    const vessel = document.getElementById("id_vessel");
    const slots = document.querySelectorAll("select[data-slot]");
    if (!vessel || !slots.length) return;

    function slotColours() {
        const option = vessel.selectedOptions[0];
        return option && option.dataset.slots ? option.dataset.slots.split(",") : [];
    }

    function update() {
        const colours = slotColours();
        slots.forEach((select) => {
            const colour = colours[Number(select.dataset.slot) - 1];
            const gem = document.querySelector(`[data-gem-for="${select.id}"]`);
            if (gem) gem.className = `gem ${colour || "white empty"}`;
            for (const option of select.options) {
                if (!option.value) continue;
                const fits = !colour || colour === "white" || option.dataset.colour === colour;
                option.disabled = !fits;
                if (!fits && option.selected) select.value = "";
            }
        });
    }

    vessel.addEventListener("change", update);
    update();
})();

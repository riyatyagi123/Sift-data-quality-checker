document.addEventListener('DOMContentLoaded', () => {
    const margin = 12;

    function placeTooltip(tooltip, anchor) {
        tooltip.classList.add('tooltip-fixed');
        tooltip.style.visibility = 'hidden';
        tooltip.style.left = '0px';
        tooltip.style.top = '0px';

        const anchorRect = anchor.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        const placements = [
            {
                top: anchorRect.top - tooltipRect.height - margin,
                left: anchorRect.left + (anchorRect.width - tooltipRect.width) / 2
            },
            {
                top: anchorRect.bottom + margin,
                left: anchorRect.left + (anchorRect.width - tooltipRect.width) / 2
            },
            {
                top: anchorRect.top + (anchorRect.height - tooltipRect.height) / 2,
                left: anchorRect.left - tooltipRect.width - margin
            },
            {
                top: anchorRect.top + (anchorRect.height - tooltipRect.height) / 2,
                left: anchorRect.right + margin
            }
        ];

        const fits = ({ top, left }) =>
            top >= margin &&
            left >= margin &&
            top + tooltipRect.height <= viewportHeight - margin &&
            left + tooltipRect.width <= viewportWidth - margin;

        const placement = placements.find(fits) || placements[0];
        const top = Math.min(
            Math.max(placement.top, margin),
            viewportHeight - tooltipRect.height - margin
        );
        const left = Math.min(
            Math.max(placement.left, margin),
            viewportWidth - tooltipRect.width - margin
        );

        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;
        tooltip.style.visibility = '';
    }

    function resetTooltip(tooltip) {
        tooltip.classList.remove('tooltip-fixed');
        tooltip.style.top = '';
        tooltip.style.left = '';
        tooltip.style.visibility = '';
    }

    document.addEventListener('mouseover', (event) => {
        const group = event.target.closest('.group');
        if (!group || group.dataset.tooltipActive === 'true') return;

        const tooltip = group.querySelector(':scope > span.pointer-events-none');
        if (!tooltip) return;

        group.dataset.tooltipActive = 'true';
        placeTooltip(tooltip, group);
    });

    document.addEventListener('mouseout', (event) => {
        const group = event.target.closest('.group');
        if (!group || group.contains(event.relatedTarget)) return;

        const tooltip = group.querySelector(':scope > span.pointer-events-none');
        if (!tooltip) return;

        group.dataset.tooltipActive = 'false';
        resetTooltip(tooltip);
    });

    window.addEventListener('scroll', () => {
        document.querySelectorAll('.group[data-tooltip-active="true"]').forEach((group) => {
            const tooltip = group.querySelector(':scope > span.pointer-events-none');
            if (tooltip) placeTooltip(tooltip, group);
        });
    }, { passive: true });

    window.addEventListener('resize', () => {
        document.querySelectorAll('.group[data-tooltip-active="true"]').forEach((group) => {
            const tooltip = group.querySelector(':scope > span.pointer-events-none');
            if (tooltip) placeTooltip(tooltip, group);
        });
    });
});

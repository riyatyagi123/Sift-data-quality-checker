document.addEventListener('DOMContentLoaded', () => {
    const margin = 12;
    const gap = 10;

    function getOwnerCard(anchor) {
        return anchor.closest('.hover-card, [class*="rounded-2xl"], [class*="rounded-3xl"]');
    }

    function getVisibleRect(element) {
        const rect = element.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return null;
        return rect;
    }

    function intersects(a, b) {
        return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
    }

    function viewportOverflow(rect) {
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        return Math.max(0, margin - rect.left) +
            Math.max(0, rect.right - (viewportWidth - margin)) +
            Math.max(0, margin - rect.top) +
            Math.max(0, rect.bottom - (viewportHeight - margin));
    }

    function neighboringCardOverlap(rect, ownerCard) {
        const cards = Array.from(document.querySelectorAll('.hover-card'));
        return cards.some((card) => {
            if (card === ownerCard || card.contains(ownerCard) || ownerCard?.contains(card)) return false;
            const cardRect = getVisibleRect(card);
            return cardRect && intersects(rect, cardRect);
        });
    }

    function clamp(value, min, max) {
        if (max < min) return min;
        return Math.min(Math.max(value, min), max);
    }

    function raiseOwnerCard(anchor) {
        const ownerCard = getOwnerCard(anchor);
        if (!ownerCard) return;

        if (ownerCard.dataset.tooltipRaised !== 'true') {
            ownerCard.dataset.tooltipPreviousZIndex = ownerCard.style.zIndex || '';
            ownerCard.dataset.tooltipRaised = 'true';
        }
        ownerCard.style.zIndex = '1000';
    }

    function resetOwnerCard(anchor) {
        const ownerCard = getOwnerCard(anchor);
        if (!ownerCard || ownerCard.dataset.tooltipRaised !== 'true') return;

        ownerCard.style.zIndex = ownerCard.dataset.tooltipPreviousZIndex || '';
        delete ownerCard.dataset.tooltipPreviousZIndex;
        delete ownerCard.dataset.tooltipRaised;
    }

    function getTooltip(anchor) {
        return anchor.querySelector(':scope > span.pointer-events-none');
    }

    function placeTooltip(tooltip, anchor) {
        raiseOwnerCard(anchor);
        tooltip.classList.add('tooltip-popover');
        tooltip.style.visibility = 'hidden';
        tooltip.style.top = '0px';
        tooltip.style.left = '0px';

        const anchorRect = anchor.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        const ownerCard = getOwnerCard(anchor);
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        const candidates = [
            {
                name: 'right',
                top: (anchorRect.height - tooltipRect.height) / 2,
                left: anchorRect.width + gap
            },
            {
                name: 'left',
                top: (anchorRect.height - tooltipRect.height) / 2,
                left: -tooltipRect.width - gap
            },
            {
                name: 'above',
                top: -tooltipRect.height - gap,
                left: (anchorRect.width - tooltipRect.width) / 2
            }
        ].map((candidate) => {
            const viewportRect = {
                top: anchorRect.top + candidate.top,
                left: anchorRect.left + candidate.left,
                right: anchorRect.left + candidate.left + tooltipRect.width,
                bottom: anchorRect.top + candidate.top + tooltipRect.height
            };

            return {
                ...candidate,
                viewportRect,
                overflow: viewportOverflow(viewportRect),
                overlapsCard: neighboringCardOverlap(viewportRect, ownerCard)
            };
        });

        const preferred = candidates.find(candidate => candidate.overflow === 0 && !candidate.overlapsCard) ||
            candidates.find(candidate => candidate.overflow === 0) ||
            candidates.slice().sort((a, b) => a.overflow - b.overflow)[0];

        const unclampedTop = anchorRect.top + preferred.top;
        const unclampedLeft = anchorRect.left + preferred.left;
        const clampedTop = clamp(unclampedTop, margin, viewportHeight - tooltipRect.height - margin);
        const clampedLeft = clamp(unclampedLeft, margin, viewportWidth - tooltipRect.width - margin);

        tooltip.dataset.tooltipPlacement = preferred.name;
        tooltip.style.top = `${preferred.top + (clampedTop - unclampedTop)}px`;
        tooltip.style.left = `${preferred.left + (clampedLeft - unclampedLeft)}px`;
        tooltip.style.visibility = '';
    }

    function showTooltip(anchor) {
        if (!anchor || anchor.dataset.tooltipActive === 'true') return;

        const tooltip = getTooltip(anchor);
        if (!tooltip) return;

        anchor.dataset.tooltipActive = 'true';
        placeTooltip(tooltip, anchor);
    }

    function hideTooltip(anchor, force = false) {
        if (!anchor || (!force && anchor.dataset.tooltipPinned === 'true')) return;

        const tooltip = getTooltip(anchor);
        if (!tooltip) return;

        anchor.dataset.tooltipActive = 'false';
        anchor.dataset.tooltipPinned = 'false';
        tooltip.classList.remove('tooltip-popover');
        tooltip.style.top = '';
        tooltip.style.left = '';
        tooltip.style.visibility = '';
        delete tooltip.dataset.tooltipPlacement;
        resetOwnerCard(anchor);
    }

    function closePinnedTooltips(exceptAnchor) {
        document.querySelectorAll('.group[data-tooltip-active="true"]').forEach((anchor) => {
            if (anchor !== exceptAnchor) hideTooltip(anchor, true);
        });
    }

    document.addEventListener('mouseover', (event) => {
        const anchor = event.target.closest('.group');
        if (!anchor || !getTooltip(anchor)) return;
        showTooltip(anchor);
    });

    document.addEventListener('mouseout', (event) => {
        const anchor = event.target.closest('.group');
        if (!anchor || anchor.contains(event.relatedTarget)) return;
        hideTooltip(anchor);
    });

    document.addEventListener('click', (event) => {
        const anchor = event.target.closest('.group');
        if (!anchor || !getTooltip(anchor)) {
            closePinnedTooltips();
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        const isPinned = anchor.dataset.tooltipPinned === 'true';
        closePinnedTooltips(anchor);

        if (isPinned) {
            hideTooltip(anchor, true);
        } else {
            anchor.dataset.tooltipPinned = 'true';
            if (anchor.dataset.tooltipActive === 'true') {
                placeTooltip(getTooltip(anchor), anchor);
            } else {
                showTooltip(anchor);
            }
        }
    });

    window.addEventListener('scroll', () => {
        document.querySelectorAll('.group[data-tooltip-active="true"]').forEach((anchor) => {
            const tooltip = getTooltip(anchor);
            if (tooltip) placeTooltip(tooltip, anchor);
        });
    }, { passive: true });

    window.addEventListener('resize', () => {
        document.querySelectorAll('.group[data-tooltip-active="true"]').forEach((anchor) => {
            const tooltip = getTooltip(anchor);
            if (tooltip) placeTooltip(tooltip, anchor);
        });
    });
});

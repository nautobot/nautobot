const DRAGGABLE_CLASS = 'nb-draggable';
const DRAGGABLE_CONTAINER_CLASS = 'nb-draggable-container';
const DRAGGABLE_GRIP_CLASS = 'nb-draggable-grip';
const DRAGGABLE_HANDLE_CLASS = 'nb-draggable-handle';
const DRAGGING_CLASS = 'nb-dragging';

const KEYBOARD_MOVE_KEYS = ['ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowUp'];

/*
 * Available draggable flows are:
 *   - `BIDIRECTIONAL`: default value, agnostic of the axis in which the nearest draggable should be looked for.
 *   - `COLUMN`: prioritizes searching the nearest draggable in the nearest column container, if such structure exists.
 */
const DRAGGABLE_FLOW = { BIDIRECTIONAL: 'bidirectional', COLUMN: 'column' };
const DRAGGABLE_FLOW_DATA_ATTRIBUTE = 'data-nb-draggable-flow';

export const initializeDraggable = () => {
  const closest = (element, className) => element?.closest?.(`.${className}`);

  const createHandleOnMouseListener = (isDraggable) => (event) => {
    const handle = closest(event.target, DRAGGABLE_HANDLE_CLASS);
    if (handle) {
      const draggable = closest(handle, DRAGGABLE_CLASS);
      draggable.setAttribute('draggable', String(isDraggable));
    }
  };

  /*
   * According to HTML spec, `event.dataTransfer` is only available in `onDragStart` and `onDrop` events, and in the
   * rest of the Drag and Drop API event handlers, it is in *protected* mode, in which some of the drag store properties
   * are enumerable but not readable. Hence, store drag details in this `dragDataRef.current` React-style ref object.
   * Source: https://html.spec.whatwg.org/multipage/dnd.html#the-drag-data-store
   */
  const dragDataRef = { current: { draggable: null, insert: {} } };

  const onMouseDown = createHandleOnMouseListener(true);
  const onMouseUp = createHandleOnMouseListener(false);

  const onDragStart = (event) => {
    const draggable = closest(event.target, DRAGGABLE_CLASS);
    if (draggable) {
      draggable.classList.add(DRAGGING_CLASS);

      dragDataRef.current = {
        ...dragDataRef.current,
        draggable: event.target,
        insert: {
          ...dragDataRef.current.insert,
          [event.target.id]: {
            after: event.target.nextElementSibling ? null : event.target,
            before: event.target.nextElementSibling,
            inside: null,
          },
        },
      };
    }
  };

  const onDragEnd = (event) => {
    const draggable = closest(event.target, DRAGGABLE_CLASS);
    if (draggable) {
      draggable.classList.remove(DRAGGING_CLASS);
      draggable.setAttribute('draggable', 'false');

      // When dragging is finished, remove `dragData` `draggable` element and its `insert` data.
      const { [draggable.id]: insert, ...nextDragDataInsert } = dragDataRef.current.insert;
      dragDataRef.current = { ...dragDataRef.current, draggable: null, insert: nextDragDataInsert };

      // Remove drop indicator by resetting its `inset` CSS property to initial 0 size.
      const draggableContainer = closest(event.target, DRAGGABLE_CONTAINER_CLASS);
      draggableContainer.style.setProperty('--drop-indicator-inset', '0 0 100% 100%');

      if (insert.after && insert.after !== draggable && insert.after.nextElementSibling !== draggable) {
        insert.after.after(draggable);
      } else if (insert.before && insert.before !== draggable && insert.before.previousElementSibling !== draggable) {
        insert.before.before(draggable);
      } else if (insert.inside) {
        insert.inside.append(draggable);
      }
    }
  };

  const onDragOver = (event) => {
    /*
     * This `draggable` element is (technically speaking) not referenced 100% properly here, but it's still the best
     * reference we can get at this point. `event.dataTransfer` cannot be used in `onDragOver` handler due to its
     * *protected* mode (see `dragDataRef` comment above), and `event.target` refers to the element being dragged over,
     * rather than the dragged element itself.
     */
    const { draggable } = dragDataRef.current;
    const draggableContainer = closest(event.target, DRAGGABLE_CONTAINER_CLASS);
    if (draggable && draggableContainer) {
      event.preventDefault();

      const insert = (() => {
        const findNearestElement = (container, selector, options) =>
          [...container.querySelectorAll(selector)]
            .map((element) => {
              const { bottom, left, right, top } = element.getBoundingClientRect();

              const isWithinXBounds = event.clientX >= left && event.clientX <= right;
              const isWithinYBounds = event.clientY >= top && event.clientY <= bottom;

              const distanceX = isWithinXBounds
                ? 0
                : Math.min(Math.abs(event.clientX - left), Math.abs(event.clientX - right));
              const distanceY = isWithinYBounds
                ? 0
                : Math.min(Math.abs(event.clientY - bottom), Math.abs(event.clientY - top));
              // eslint-disable-next-line id-length
              const distance = { normalized: Math.sqrt(distanceX ** 2 + distanceY ** 2), x: distanceX, y: distanceY };

              return { distance, element };
            })
            // eslint-disable-next-line id-length
            .sort((a, b) => {
              const prioritizeAxis = options?.prioritizeAxis;
              return prioritizeAxis && a.distance[prioritizeAxis] !== b.distance[prioritizeAxis]
                ? b.distance[prioritizeAxis] - a.distance[prioritizeAxis]
                : b.distance.normalized - a.distance.normalized;
            })
            .pop()?.element;

        const container = (() => {
          const draggableFlow =
            draggableContainer.getAttribute(DRAGGABLE_FLOW_DATA_ATTRIBUTE) ?? DRAGGABLE_FLOW.BIDIRECTIONAL;
          const areDraggablesGrouped = [...draggableContainer.children].every(
            (child) => !child.classList.contains(DRAGGABLE_CLASS),
          );
          if (draggableFlow === DRAGGABLE_FLOW.COLUMN && areDraggablesGrouped) {
            return findNearestElement(draggableContainer, ':scope > *', { prioritizeAxis: 'x' });
          }

          return draggableContainer;
        })();

        const nearestDraggable = findNearestElement(container, `.${DRAGGABLE_CLASS}`);
        if (nearestDraggable) {
          const nearestDraggableRect = nearestDraggable.getBoundingClientRect();
          const nearestDraggableCenterCords = {
            x: nearestDraggableRect.left + nearestDraggableRect.width / 2, // eslint-disable-line id-length
            y: nearestDraggableRect.top + nearestDraggableRect.height / 2, // eslint-disable-line id-length
          };

          const isBelowTheNearestDraggable = nearestDraggableCenterCords.y < event.clientY;
          return isBelowTheNearestDraggable
            ? { after: nearestDraggable, before: null, inside: null }
            : { after: null, before: nearestDraggable, inside: null };
        }

        return { after: null, before: null, inside: container };
      })();

      // Re-calculate drop indicator position when `insert` element has changed, otherwise skip the entire operation.
      if (
        insert.after !== dragDataRef.current.insert[draggable.id]?.after ||
        insert.before !== dragDataRef.current.insert[draggable.id]?.before ||
        insert.inside !== dragDataRef.current.insert[draggable.id]?.inside
      ) {
        // Calculate the drop indicator line geometry in relation to its offset parent (nearest positioned ancestor).
        draggableContainer.style.setProperty(
          '--drop-indicator-inset',
          (() => {
            const HEIGHT = '0.125rem'; // Constant drop indicator height = `0.125rem` (`2px`).
            const heightHalf = `${parseFloat(HEIGHT) / 2}rem`;

            if (insert.after) {
              // Take whitespace into calculations only if the next sibling element is in the same column.
              const whitespace =
                insert.after.nextElementSibling?.offsetLeft === insert.after.offsetLeft
                  ? insert.after.nextElementSibling.offsetTop - (insert.after.offsetTop + insert.after.offsetHeight)
                  : 0;
              const bottom = `calc(${insert.after.offsetParent.offsetHeight - (insert.after.offsetTop + insert.after.offsetHeight) - whitespace / 2}px - ${heightHalf})`;
              const left = `${insert.after.offsetLeft}px`;
              const right = `${insert.after.offsetParent.offsetWidth - (insert.after.offsetLeft + insert.after.offsetWidth)}px`;
              const top = `calc(${insert.after.offsetTop + insert.after.offsetHeight + whitespace / 2}px - ${heightHalf})`;
              return `${top} ${right} ${bottom} ${left}`;
            }

            if (insert.before || insert.inside) {
              const insertElement = insert.before ?? insert.inside;
              // Take whitespace into calculations only if the previous sibling element is in the same column.
              const whitespace =
                insert.before && insert.before.previousElementSibling?.offsetLeft === insert.before.offsetLeft
                  ? insert.before.offsetTop -
                    (insert.before.previousElementSibling.offsetTop + insert.before.previousElementSibling.offsetHeight)
                  : 0;
              const bottom = `calc(${insertElement.offsetParent.offsetHeight - insertElement.offsetTop + whitespace / 2}px - ${heightHalf})`;
              const left = `${insertElement.offsetLeft}px`;
              const right = `${insertElement.offsetParent.offsetWidth - (insertElement.offsetLeft + insertElement.offsetWidth)}px`;
              const top = `calc(${insertElement.offsetTop - whitespace / 2}px - ${heightHalf})`;
              return `${top} ${right} ${bottom} ${left}`;
            }

            return '0 0 100% 100%';
          })(),
        );
      }

      dragDataRef.current = {
        ...dragDataRef.current,
        insert: { ...dragDataRef.current.insert, [draggable.id]: insert ?? null },
      };
    } else if (draggable && !draggableContainer) {
      /*
       * Remove the `insert` node stored for this draggable element and the drop indicator from its draggable container.
       * To get valid container, traverse the tree up from the currently dragged element (`draggable`). This is
       * partially similar to (but not the same as!) `onDragEnd` event handler above.
       */
      // eslint-disable-next-line id-length, no-unused-vars
      const { [draggable.id]: _, ...nextDragDataInsert } = dragDataRef.current.insert;
      dragDataRef.current = { ...dragDataRef.current, insert: nextDragDataInsert };

      const validDraggableContainer = closest(draggable, DRAGGABLE_CONTAINER_CLASS);
      validDraggableContainer.style.setProperty('--drop-indicator-inset', '0 0 100% 100%');
    }
  };

  const onDrop = (event) => {
    const { draggable } = dragDataRef.current;
    if (draggable) {
      /*
       * Disable drop default actions. Instead, handle drop in `onDragEnd` due to inconsistent `onDrop` behavior.
       * "Inconsistent" means that in theory `onDrop` should always fire when draggable element is dropped inside a
       * valid container, but apparently in practice it is not always the case, and sometimes for some reason drops are
       * "lost". `onDragEnd` on the other hand fires always when drag action ends and can be used deterministically.
       */
      event.preventDefault();
    }
  };

  /*
   * ---------------------------------------------------------------------------------------------------------------
   * Keyboard alternative to dragging (WCAG 2.5.7 Dragging Movements)
   * ---------------------------------------------------------------------------------------------------------------
   *
   * Everything above this point is driven by pointer events only, which left keyboard and switch users with no way to
   * reorder anything at all. The handler below implements the conventional accessible pattern: a focusable grip button
   * that is "picked up" with Enter or Space, moved with the arrow keys, and dropped with Enter, Space or Escape.
   *
   * Reordering is done purely by moving DOM nodes, which is also how the pointer implementation works. Consumers that
   * persist the order (the homepage watches its container with a `MutationObserver`) therefore pick keyboard moves up
   * without any extra wiring.
   */

  /**
   * Get the column elements of a draggable container, or the container itself when draggables are not grouped.
   * @param {HTMLElement} container - Draggable container element.
   * @returns {HTMLElement[]} Elements that directly hold draggables.
   */
  const getColumns = (container) => {
    const children = [...container.children];
    const areDraggablesGrouped = children.every((child) => !child.classList.contains(DRAGGABLE_CLASS));
    return areDraggablesGrouped ? children : [container];
  };

  const getColumnDraggables = (column) =>
    [...column.children].filter((child) => child.classList.contains(DRAGGABLE_CLASS));

  /**
   * Move a draggable one step in the given direction, across columns where relevant.
   * @param {HTMLElement} draggable - The draggable element to move.
   * @param {string} key - One of the `KEYBOARD_MOVE_KEYS` values.
   * @returns {boolean} `true` when the element actually moved, `false` when it was already at the boundary.
   */
  const moveDraggableByKey = (draggable, key) => {
    const container = closest(draggable, DRAGGABLE_CONTAINER_CLASS);
    if (!container) {
      return false;
    }

    const columns = getColumns(container);
    const column = columns.find((candidate) => candidate.contains(draggable));
    const columnIndex = columns.indexOf(column);
    const siblings = getColumnDraggables(column);
    const index = siblings.indexOf(draggable);

    if (key === 'ArrowUp') {
      const previous = siblings[index - 1];
      if (!previous) {
        return false;
      }
      previous.before(draggable);
      return true;
    }

    if (key === 'ArrowDown') {
      const next = siblings[index + 1];
      if (!next) {
        return false;
      }
      next.after(draggable);
      return true;
    }

    // Horizontal movement only means anything when draggables are actually grouped into separate columns.
    const targetColumn = columns[columnIndex + (key === 'ArrowRight' ? 1 : -1)];
    if (!targetColumn || targetColumn === column) {
      return false;
    }

    /*
     * Keep the element at a comparable depth in the target column rather than always appending, so that moving right and
     * then left again lands roughly where it started.
     */
    const targetSiblings = getColumnDraggables(targetColumn);
    const reference = targetSiblings[index];
    if (reference) {
      reference.before(draggable);
    } else {
      targetColumn.appendChild(draggable);
    }
    return true;
  };

  /**
   * Describe a draggable's current position for announcement, e.g. "column 2 of 4, position 1 of 3".
   * @param {HTMLElement} draggable - The draggable element being described.
   * @returns {string} Human readable position.
   */
  const describePosition = (draggable) => {
    const container = closest(draggable, DRAGGABLE_CONTAINER_CLASS);
    const columns = container ? getColumns(container) : [];
    const column = columns.find((candidate) => candidate.contains(draggable));
    const siblings = column ? getColumnDraggables(column) : [];
    const position = `position ${siblings.indexOf(draggable) + 1} of ${siblings.length}`;
    return columns.length > 1 ? `column ${columns.indexOf(column) + 1} of ${columns.length}, ${position}` : position;
  };

  /*
   * A single shared live region is enough: only one draggable can be grabbed at a time. It is created lazily so that
   * pages without any draggables do not grow an extra node.
   */
  const liveRegionRef = { current: null };

  const announce = (message) => {
    if (!liveRegionRef.current) {
      const liveRegion = document.createElement('div');
      liveRegion.className = 'visually-hidden';
      liveRegion.setAttribute('aria-atomic', 'true');
      liveRegion.setAttribute('aria-live', 'assertive');
      liveRegion.setAttribute('role', 'status');
      document.body.appendChild(liveRegion);
      liveRegionRef.current = liveRegion;
    }
    liveRegionRef.current.textContent = message;
  };

  const grabbedRef = { current: null };

  const setGrabbed = (grip, grabbed) => {
    const draggable = closest(grip, DRAGGABLE_CLASS);
    grabbedRef.current = grabbed ? grip : null;

    grip.setAttribute('aria-pressed', String(grabbed));
    draggable?.classList.toggle(DRAGGING_CLASS, grabbed);

    const name = grip.dataset.nbDraggableLabel || 'Panel';
    announce(
      grabbed
        ? `${name} grabbed. ${describePosition(draggable)}. Use the arrow keys to move it, then press Enter or Escape to drop it.`
        : `${name} dropped. ${describePosition(draggable)}.`,
    );
  };

  const onGripKeyDown = (event) => {
    const grip = event.target.closest?.(`.${DRAGGABLE_GRIP_CLASS}`);
    if (!grip) {
      return;
    }

    const isGrabbed = grabbedRef.current === grip;

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault(); // Space would otherwise scroll the page, Enter would submit an enclosing form.
      setGrabbed(grip, !isGrabbed);
      return;
    }

    if (event.key === 'Escape' && isGrabbed) {
      event.preventDefault();
      event.stopPropagation(); // Do not let an enclosing dismissible component also react to Escape.
      setGrabbed(grip, false);
      return;
    }

    if (isGrabbed && KEYBOARD_MOVE_KEYS.includes(event.key)) {
      event.preventDefault(); // Arrow keys would otherwise scroll the page while the element is grabbed.
      const draggable = closest(grip, DRAGGABLE_CLASS);
      const name = grip.dataset.nbDraggableLabel || 'Panel';

      if (moveDraggableByKey(draggable, event.key)) {
        /*
         * Moving the node detaches and reinserts it, which drops focus to `<body>`, so focus has to be restored to the
         * grip for the interaction to continue.
         */
        grip.focus();
        announce(`${name} moved. ${describePosition(draggable)}.`);
      } else {
        announce(`${name} cannot move any further in that direction. ${describePosition(draggable)}.`);
      }
    }
  };

  // Dropping on blur avoids leaving a draggable in a grabbed state that the user can no longer control.
  const onGripBlur = (event) => {
    const grip = event.target.closest?.(`.${DRAGGABLE_GRIP_CLASS}`);
    if (grip && grabbedRef.current === grip) {
      setGrabbed(grip, false);
    }
  };

  // Using event delegation pattern here to avoid re-creating listeners each time DOM is modified.
  document.addEventListener('mousedown', onMouseDown);
  document.addEventListener('mouseup', onMouseUp);
  document.addEventListener('dragstart', onDragStart);
  document.addEventListener('dragend', onDragEnd);
  document.addEventListener('dragover', onDragOver);
  document.addEventListener('drop', onDrop);
  document.addEventListener('keydown', onGripKeyDown);
  document.addEventListener('focusout', onGripBlur);
};

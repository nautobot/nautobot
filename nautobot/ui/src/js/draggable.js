const DRAGGABLE_CLASS = 'nb-draggable';
const DRAGGABLE_CONTAINER_CLASS = 'nb-draggable-container';
const DRAGGABLE_HANDLE_CLASS = 'nb-draggable-handle';
const DRAGGING_CLASS = 'nb-dragging';

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

  // Using event delegation pattern here to avoid re-creating listeners each time DOM is modified.
  document.addEventListener('mousedown', onMouseDown);
  document.addEventListener('mouseup', onMouseUp);
  document.addEventListener('dragstart', onDragStart);
  document.addEventListener('dragend', onDragEnd);
  document.addEventListener('dragover', onDragOver);
  document.addEventListener('drop', onDrop);
};

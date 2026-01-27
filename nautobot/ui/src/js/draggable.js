const DRAGGABLE_CLASS = 'nb-draggable';
const DRAGGABLE_CONTAINER_CLASS = 'nb-draggable-container';
const DRAGGABLE_HANDLE_CLASS = 'nb-draggable-handle';
const DRAGGING_CLASS = 'nb-dragging';

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
  const dragDataRef = { current: { draggable: null, insertBefore: {} } };

  const onMouseDown = createHandleOnMouseListener(true);
  const onMouseUp = createHandleOnMouseListener(false);

  const onDragStart = (event) => {
    const draggable = closest(event.target, DRAGGABLE_CLASS);
    if (draggable) {
      draggable.classList.add(DRAGGING_CLASS);

      dragDataRef.current = {
        ...dragDataRef.current,
        draggable: event.target,
        insertBefore: { ...dragDataRef.current.insertBefore, [event.target.id]: event.target.nextElementSibling },
      };
    }
  };

  const onDragEnd = (event) => {
    const draggable = closest(event.target, DRAGGABLE_CLASS);
    if (draggable) {
      draggable.classList.remove(DRAGGING_CLASS);
      draggable.setAttribute('draggable', 'false');

      // When dragging is finished, remove `dragData` `draggable` element and its `insertBefore` data.
      const { [draggable.id]: insertBefore, ...nextDragDataInsertBefore } = dragDataRef.current.insertBefore;
      dragDataRef.current = { ...dragDataRef.current, draggable: null, insertBefore: nextDragDataInsertBefore };

      // Remove drop indicator by resetting its `inset` CSS property to initial 0 size.
      const draggableContainer = closest(event.target, DRAGGABLE_CONTAINER_CLASS);
      draggableContainer.style.setProperty('--drop-indicator-inset', '0 0 100% 100%');

      if (insertBefore) {
        draggableContainer.insertBefore(draggable, insertBefore);
      } else if (insertBefore === null) {
        // Add to end of the list.
        draggableContainer.append(draggable);
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

      const insertBefore = (() => {
        // Were we dropped onto another draggable?
        const dropDraggable = closest(event.target, DRAGGABLE_CLASS);
        if (dropDraggable) {
          /*
           * Were we dropped in the top half or the bottom half of the target draggable?
           *   - Top half - insert before that draggable.
           *   - Bottom half - insert after that draggable.
           */
          const { height, top } = dropDraggable.getBoundingClientRect();
          const isTopHalf = event.clientY < top + height / 2;
          return isTopHalf ? dropDraggable : dropDraggable.nextElementSibling;
        }

        // We were dropped into empty space - find the closest draggable by geometry.
        return [...draggableContainer.children]
          .filter((child) => child.classList.contains(DRAGGABLE_CLASS))
          .find((child) => {
            const { left, right, top } = child.getBoundingClientRect();
            // Are we in the correct column?
            if (left > event.clientX) {
              // Found the first child that is too far to the right, so we insert before that child.
              return true;
            } else if (right >= event.clientX) {
              // Child is in the correct column.
              if (top >= event.clientY) {
                // Found the first child in this column we were dropped above, so we insert before that child.
                return true;
              }
            }
            return false;
          });
      })();

      // Only re-calculate drop indicator position when `insertBefore` element has changed, otherwise skip it.
      if (insertBefore !== dragDataRef.current.insertBefore[draggable.id]) {
        // Calculate the drop indicator line geometry in relation to its offset parent (nearest positioned ancestor).
        draggableContainer.style.setProperty(
          '--drop-indicator-inset',
          (() => {
            const HEIGHT = '0.125rem'; // Constant drop indicator height = `0.125rem` (`2px`).
            const heightHalf = `${parseFloat(HEIGHT) / 2}rem`;

            if (insertBefore) {
              const bottom = `calc(${insertBefore.offsetParent.offsetHeight - insertBefore.offsetTop}px - ${heightHalf})`;
              const left = `${insertBefore.offsetLeft}px`;
              const right = `${insertBefore.offsetParent.offsetWidth - (insertBefore.offsetLeft + insertBefore.offsetWidth)}px`;
              const top = `calc(${insertBefore.offsetTop}px - ${heightHalf})`;
              return `${top} ${right} ${bottom} ${left}`;
            }

            /*
             * When `insertBefore` is explicitly `null`, it means there is no node to insert the element *before*, so
             * instead insert it *after* the last child in the container, effectively at the end of the list.
             */
            const insertAfter = draggableContainer.lastElementChild;
            const bottom = `calc(${insertAfter.offsetParent.offsetHeight - (insertAfter.offsetTop + insertAfter.offsetHeight)}px - ${heightHalf})`;
            const left = `${insertAfter.offsetLeft}px`;
            const right = `${insertAfter.offsetParent.offsetWidth - (insertAfter.offsetLeft + insertAfter.offsetWidth)}px`;
            const top = `calc(${insertAfter.offsetTop + insertAfter.offsetHeight}px - ${heightHalf})`;
            return `${top} ${right} ${bottom} ${left}`;
          })(),
        );
      }

      dragDataRef.current = {
        ...dragDataRef.current,
        insertBefore: { ...dragDataRef.current.insertBefore, [draggable.id]: insertBefore ?? null },
      };
    } else if (draggable && !draggableContainer) {
      /*
       * Remove the `insertBefore` node stored for this draggable element and the drop indicator from its draggable
       * container. To get valid container, traverse the tree up from the currently dragged element (`draggable`). This
       * is partially similar to (but not the same as!) `onDragEnd` event handler above.
       */
      // eslint-disable-next-line id-length, no-unused-vars
      const { [draggable.id]: _, ...nextDragDataInsertBefore } = dragDataRef.current.insertBefore;
      dragDataRef.current = { ...dragDataRef.current, insertBefore: nextDragDataInsertBefore };

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

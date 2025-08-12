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

  const onMouseDown = createHandleOnMouseListener(true);
  const onMouseUp = createHandleOnMouseListener(false);

  const onDragStart = (event) => {
    const draggable = closest(event.target, DRAGGABLE_CLASS);
    if (draggable) {
      event.dataTransfer.clearData('text/plain');
      event.dataTransfer.setData('text/plain', event.target.id);
      draggable.classList.add(DRAGGING_CLASS);
    }
  };

  const onDragEnd = (event) => {
    const draggable = closest(event.target, DRAGGABLE_CLASS);
    if (draggable) {
      draggable.classList.remove(DRAGGING_CLASS);
      draggable.setAttribute('draggable', 'false');
    }
  };

  const onDragOver = (event) => {
    const draggableContainer = closest(event.target, DRAGGABLE_CONTAINER_CLASS);
    if (draggableContainer) {
      event.preventDefault();
    }
  };

  const onDrop = (event) => {
    const draggable = document.getElementById(event.dataTransfer.getData('text/plain'));
    if (draggable) {
      event.preventDefault();

      const container = closest(draggable, DRAGGABLE_CONTAINER_CLASS);

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
          return isTopHalf ? dropDraggable : dropDraggable.nextSibling;
        }

        // We were dropped into empty space - find the closest draggable by geometry.
        return [...container.children].find((child) => {
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

      if (insertBefore) {
        container.insertBefore(draggable, insertBefore);
      } else {
        // Add to end of the list.
        container.append(draggable);
      }

      draggable.classList.add(DRAGGING_CLASS);
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

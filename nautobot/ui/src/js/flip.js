import htmx from 'htmx.org';
import { setAttribute } from './utils.js';

const FLIP_DATA_ATTRIBUTE = 'data-nb-flip';

/**
 * Flip element attributes between two given sets.
 *   - `data-nb-flip` is a string containing a space-separated set of attributes subject to flip.
 *   - `data-nb-flip-{name}` defines a "parked" attribute which is not in effect until the next flip.
 * @param {Element|null} element - Element which attributes are to be flipped.
 */
export const flipAttributes = (element) => {
  const attributes = element?.getAttribute(FLIP_DATA_ATTRIBUTE)?.split(' ');

  attributes?.forEach((attribute) => {
    const currentName = attribute;
    const currentValue = element.getAttribute(attribute);

    const flipName = `${FLIP_DATA_ATTRIBUTE}-${attribute}`;
    const flipValue = element.getAttribute(flipName);

    setAttribute(element, currentName, flipValue);
    setAttribute(element, flipName, currentValue);
  });

  // When htmx attributes change, they need to be additionally processed to take effect.
  if (attributes?.some((attribute) => attribute.includes('hx'))) {
    htmx.process(element);
  }
};

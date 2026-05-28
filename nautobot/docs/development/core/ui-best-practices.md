# UI Best Practices

Whether you're unsure of where to start the implementation of your UI, or just curious about the best possible approach you could take, this guide is to answer the questions you may have.

To browse Nautobot example code snippets and their representations see [Previewing the theme](#previewing-the-theme).

!!! note
    These are roughly outlined general guides, and it is impossible for them to cover every scenario. Always use your best judgement in a specific situation.

## Structure

Throughout the UI composition process, always work in this order:

1. Consult [New Nautobot Custom UI APIs](../apps/migration/from-v2/new-nautobot-custom-ui-apis.md), as it contains high-level re-usable custom Nautobot-specific components.
2. Otherwise, try matching your use case with already existing layouts and components from [Bootstrap](https://getbootstrap.com/).
3. If none the above are sufficient, we recommend working your way through combining [Style](#style) and [Behavior](#behavior) guides below.

!!! note
    This step may be difficult at times, but it is worth every effort. Choosing right building blocks for bigger UI structures is arguably the most important part of their implementation, as it is crucial for the end-product usability and maintainability.

To get a better picture of why putting effort into finding the best matching existing components is beneficial for you, let's take a look at examples below:

```html
<div style="background-color: #ffffff; border: 1px solid #dedede; border-radius: 4px; color: #1a1a1a; display: flex; flex-direction: column; overflow: hidden; position: relative; word-wrap: break-word;">
    <div style="flex: 1 1 auto; padding-block: 8px; padding-inline: 10px;">
        Content
    </div>
</div>
```

The component presented above is - to simply put it - an antipattern. Although initial effort of writing it from scratch, or copying it over from somewhere else, is low, other than that it has virtually no advantages. It uses basic `style` HTML attributes and hardcoded color and pixel values. Not only is it difficult to decipher its purpose, but it is also prone to all sorts of errors.

```html
<div class="bg-body border d-flex flex-column overflow-hidden position-relative rounded text-break text-body">
    <div class="flex-grow px-8 py-10">
        Content
    </div>
</div>
```

The above component is generally well-built, with Bootstrap helpers and utilities used for proper styling. With some slight differences this could be an actual go-to implementation for a hypothetical component. But in this specific case we can do better. Let's see the last example.

```html
<div class="card">
    <div class="card-body">
        Content
    </div>
</div>
```

This is the exact same component as the previous ones, but instead of building styles up from the bottom it re-uses basic Bootstrap Card component, and require no further styling. Real world scenarios may not be as simple as this, but it servers as a good example of the idea that's being laid out here.

## Style

### Style overrides

As mentioned, it is recommended to use off-the-shelf components and elements, but sometimes they may require various style adjustments to meet specific requirements, be it a custom color, size, spacing, etc.

Bootstrap offers a broad range of re-usable styles, from single-style [Helpers](https://getbootstrap.com/docs/5.3/helpers/) and [Utilities](https://getbootstrap.com/docs/5.3/utilities/) to ready-to-use layouts and components. On top of that, Nautobot also provides its own extensions documented in [New Nautobot Custom UI APIs](../apps/migration/from-v2/new-nautobot-custom-ui-apis.md#extended-bootstrap-utilities).

When styling elements, we recommend starting with base high-level (component) classes and, if needed, override their specific styles with Bootstrap or Nautobot helpers and utilities.

To expand on the previous Card component example, let's say we need to render a card with green background and border, i.e. a "success card":

```html
<div class="card bg-success-subtle border-success">
    <div class="card-body">
        Success
    </div>
</div>
```

### Custom styles

In case available helpers and utilities are not sufficient to style a component, there are two possible ways to approach this problem. To find the more suitable out of them depends on a particular use case. Let's answer these questions first:

1. Is the style used in a single or - at most - very few places?
2. Is the style simple and does not require any combined selectors?
3. If the style involves a custom defined color - should the color be the same for application's light and dark theme?

If the answer to all these questions is yes, then we advise using HTML `style` attribute for simplicity as well as coupling the style tightly with a specific element.

Otherwise, define a custom CSS code within `<style>` tag in document head, preferably inside a `{% block extra_styles %}` Django template block. If developing for the core and custom styles are intended to be used throughout multiple pages, consider adding them to the main `nautobot.scss` file.

### Custom colors

It is a good practice to define custom colors for both light and dark themes of the application. For example:

```css
/* CSS */
.custom-color {
    --custom-color: #000000;
    color: var(--custom-color);
}

[data-bs-theme="dark"] .custom-color {
    --custom-color: #ffffff;
}
```

Or in SCSS:

```scss
/* SCSS */
.custom-color {
    --custom-color: #000000;
    color: var(--custom-color);
}

@include color-mode(dark, true) {
  .custom-color {
      --custom-color: #ffffff;
  }
}
```

### Length units

It is a good practice to use length values expressed in `rem` instead of `px` units. As opposed to absolute pixels, `rem` values scale in relation to the root font size, making the application more accessible. By default, `1rem` is equal to `16px`. For example:

```css
.custom-size {
    height: 0.625rem; /* 10px */
    width: 1.5rem; /* 24px */
}
```

### Buttons and other inline elements whitespace

Buttons and other inline elements by default preserve whitespace between its child nodes. When there are multiple children, most of the time these whitespaces are not desirable due to their somewhat uncontrolled nature. We recommend using explicit gaps instead, while removing the whitespace:

```html
<a href="{{ return_url }}" class="btn btn-secondary">
    <span aria-hidden="true" class="mdi mdi-close me-4"></span><!--
    -->Cancel
</a>
```

In this example we removed whitespace between the nodes with HTML comment (`<!-- -->`) and used margin (`me-4`) to create a gap.

!!! note
    This rule does not apply to `inline-flex` elements, as they render their child nodes without whitespaces in between.

## Behavior

Some UI parts require special behaviors ouf of scope of available components or basic web platform capabilities. To achieve this, implementing JavaScript logic is necessary. We recommend writing JavaScript code that is specific to given page within `<script>` tag, preferably inside a `{% block javascript %}` Django template block. When a script is intended to be used on multiple pages, or globally, we recommend creating a separate `.js` file and importing it appropriately.

!!! warning
    Unless necessary, we advise against introducing any lower density of scripting than recommended above, that is for example inside templates that can be included multiple times on a single page, which would in turn execute a single script more than once and potentially lead to errors.

### Functional JavaScript and immutability

It is a good practice to follow functional JavaScript rules with immutability principle whenever possible, to create easily understandable code with fewer errors. Here's an example in which we compare two approaches:

```javascript
/* Non-functional, mutable */
const elements = document.querySelectorAll('.example');
const visibleElements = [];

for (element of elements) {
    const isVisible =  window.getComputedStyle(element).display !== 'none';
    if (isVisible) {
        visibleElements.push(element);
    }
}
```

```javascript
/* Functional, immutable */
const elements = document.querySelectorAll('.example');
const visibleElements = [...elements].filter((element) => window.getComputedStyle(element).display !== 'none');
```

### Document DOM Content Loaded event

When implementing your own custom JavaScript logic, our recommendation is to wrap it with `document` `DOMContentLoaded` event handler. This makes sure that the script is executed only after the page DOM has been fully loaded, and all core scripts have been run.

```javascript
document.addEventListener('DOMContentLoaded', () => {
    // Your JavaScript logic goes here.
});
```

If parts of the DOM are loaded or reloaded via [HTMX](htmx.md), and need custom JavaScript to set them up after they are retrieved, you may want to reuse the same logic as a function linked to the `htmx.onLoad()` event handler, for example:

```javascript
document.addEventListener('DOMContentLoaded', () => {
    doTheThing(document);
});

htmx.onLoad((content) => {
    doTheThing(content);
});
```

### jQuery deprecation

As of Nautobot 3.0, any jQuery usage is deprecated. There are other libraries still in use that depend on it (like Select2), but unless absolutely necessary, vanilla JavaScript should be used instead.

## Previewing the theme

When `settings.DEBUG` is set to `True`, an authenticated Nautobot user can access the URL `/theme-preview/` to retrieve a templated view that showcases many of the different Nautobot UI elements. While not necessarily comprehensive, this view is designed to provide an overview of the current theme more conveniently than clicking around to various specific pages in the UI. Feel free to add more example content into this view as needed.

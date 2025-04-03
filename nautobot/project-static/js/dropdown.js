$(document).on('show.bs.dropdown', '.table-responsive .dropdown', function() {
    const $dropdown = $(this);
    const $toggle = $dropdown.find('.dropdown-toggle');
    const $menu = $dropdown.find('.dropdown-menu');

    const toggleOffset = $toggle.offset();
    const topOffset = toggleOffset.top + $toggle.outerHeight()
    // calculate left offset to match right side edges of dropdown and toggle button
    const leftOffset = toggleOffset.left + $toggle.outerWidth() - $menu.outerWidth()

    $menu.appendTo('body').css({
        position: 'absolute',
        top: topOffset,
        left: leftOffset,
        display: 'table', // required, because we're outside any container
    });

    // move dropdown back and hide
    $dropdown.one('hidden.bs.dropdown', function () {
        $menu.appendTo($dropdown);
        $menu.removeAttr('style');
    });

    // hide dropdown when scrolling vertically to avoid recalculating position
    $('.table-responsive').one('scroll', function() {
        $toggle.trigger("click");
    });
});

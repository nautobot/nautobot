export function hexToRgb(hex) {
    var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result
        ? [
              parseInt(result[1], 16),
              parseInt(result[2], 16),
              parseInt(result[3], 16),
          ]
        : null;
}

export function calculateLuminance(hex_color) {
    var [R, G, B] = hexToRgb(hex_color);
    return (R + R + R + B + G + G + G + G + G + G) / 10;
}

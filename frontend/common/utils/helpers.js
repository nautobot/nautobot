export const capitalize = (label) => {
  if (!label) return "";
  return label
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
};

export const duplicateInputValue =
  (...targetInputs) =>
  (value) => {
    targetInputs.forEach((targetInput) => {
      const targetElement = document.getElementById(`control-${targetInput}`);
      targetElement.value = value;
    });
  };

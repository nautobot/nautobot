import { useMemo } from "react";

// Helper function to build an array from start index to end index
const range = (start, end) => {
    let length = end - start + 1;
    return Array.from({ length }, (_, idx) => idx + start);
};

export const usePagination = ({
    totalDataCount,
    pageSize,
    siblingCount = 1,
    currentPage,
}) => {
    const paginationRange = useMemo(() => {
        const totalPageCount = Math.ceil(totalDataCount / pageSize);
        const totalPageNumbers = siblingCount + 5;
        // If the total page numbers rendered is greater than the total page available
        if (totalPageNumbers >= totalPageCount) {
            return range(1, totalPageCount);
        }
        // previous page of of the current page
        const leftIndex = Math.max(currentPage + 1 - siblingCount, 1);
        // next page of of the current page
        const rightIndex = Math.min(
            currentPage + 1 + siblingCount,
            totalPageCount
        );
        const showLeftDots = leftIndex > 2;
        const showRightDots = rightIndex < totalPageCount - 2;
        const firstIndex = 1;
        const lastIndex = totalPageCount;

        if (!showLeftDots && showRightDots) {
            // e.g < 1 2 3 ... 21 >
            let leftItemCount = 3 + 2 * siblingCount;
            let leftRange = range(1, leftItemCount);
            return [...leftRange, "...", lastIndex];
        }
        if (showLeftDots && !showRightDots) {
            // e.g < 1 ... 19 20 21 >
            let rightItemCount = 3 + 2 * siblingCount;
            let rightRange = range(
                totalPageCount - rightItemCount + 1,
                totalPageCount
            );
            return [firstIndex, "...", ...rightRange];
        }

        if (showLeftDots && showRightDots) {
            // e.g < 1 ... 7 8 9 ... 21 >
            let middleRange = range(leftIndex, rightIndex);
            return [firstIndex, "...", ...middleRange, "...", lastIndex];
        }
    }, [totalDataCount, pageSize, siblingCount, currentPage]);
    return paginationRange;
};

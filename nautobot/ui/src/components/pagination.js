import React, { useEffect, useState } from "react";
import { usePagination } from "./usePagination";
import { useSearchParams } from "react-router-dom";
import { Box, Text } from "@nautobot/nautobot-ui";
import { Flex, FormControl, FormErrorMessage, IconButton, Input } from "@chakra-ui/react";
import { ChevronLeftIcon, ChevronRightIcon } from "@chakra-ui/icons";

export default function Pagination({
    totalDataCount,
    siblingCount = 1,
    currentPage,
    pageSize,
    scroll_ref,
}) {
    let [searchParams, setSearchParams] = useSearchParams();

    const paginationRange = usePagination({
        currentPage,
        totalDataCount,
        siblingCount,
        pageSize,
    });

    // currentPage starts from 0
    currentPage = ~~currentPage;
    // trueCurrentPage increments currentPage by 1 to get the accurate human-form page number
    let trueCurrentPage = currentPage + 1;

    let firstPage = 1;
    let lastPage = totalDataCount / pageSize;
    lastPage = ~~lastPage + 1;

    // State to track the current page number
    const [pageNumber, setPageNumber] = useState(trueCurrentPage);
    // State to track the page number form control input validity
    const [isInputInvalid, setIsInputInvalid] = useState(false);
    
    // Keeps the pageNumber var updated to trueCurrentPage (i.e. if trueCurrentPage changes via arrow click)
    useEffect(() => {
        setPageNumber(trueCurrentPage);
    }, [trueCurrentPage]);

    // Changes the page number based on the input component after a blur event (i.e. when user clicks out of input box and element loses focus)
    function handleOnBlur(event) {
        const enteredValue = parseInt(event.target.value);
        // Checks that the entered value is a number and within the valid page range
        if (!isNaN(enteredValue) && enteredValue >= firstPage && enteredValue <= lastPage) {
            setPageNumber(enteredValue);
            setIsInputInvalid(false);

            // Checks that the entered value is not already the current page
            if (enteredValue !== trueCurrentPage) {
                onPageNumberChange(enteredValue);
            }

            // Reset input value
            event.target.value = "";
        } 
        // Checks if nothing is entered into input and, if so, do nothing
        else if (event.target.value == "") {
            setIsInputInvalid(false);
        }
        // Otherwise, mark input as invalid
        else {
            setIsInputInvalid(true);
        }
    }

    // If there is only one/zero page in the pagination range, we do not render anything.
    if (paginationRange.length < 2) {
        return null;
    }
    function onPageNumberChange(targetPageNumber) {
        let limit = searchParams.get("limit");
        /* TODO: we need a REST API endpoint to query get_settings_or_config("PAGINATE_COUNT") rather than hard-coding this to 50. */
        // Scroll to the top of the ObjectListTable Container on table reload
        scroll_ref.current.scrollIntoView({
            alignToTop: true,
            behavior: "smooth",
        });

        currentPage++;
        let newPageNumber;
        if (targetPageNumber === "<") {
            newPageNumber = currentPage - 1;
        } else if (targetPageNumber === ">") {
            newPageNumber = currentPage + 1;
        } else {
            newPageNumber = targetPageNumber;
        }

        setIsInputInvalid(false);

        setSearchParams({
            offset: pageSize * (newPageNumber - 1),
            limit: limit ? limit : 50,
        });
    }

    return (
        <Flex align="center">
            <Box color="gray-3" pl="xs" pr="xs" mr="lg" fontSize="md" border='1px' borderColor='gray-1' borderRadius="sm">
                {totalDataCount} rows
            </Box>
            <Text color="gray-3" whiteSpace="nowrap">
                You are on page
            </Text>
            {currentPage + 1 > firstPage ? (
                <IconButton
                    onClick={() => onPageNumberChange("<")}
                    icon={<ChevronLeftIcon />}
                    color="gray-4"
                    variant="ghost"
                    pl="xs"
                    _hover={{
                        transform: "scale(1.2)",
                        color: "#007DFF"
                    }}
                />
            ) : (
                <Box pl="xs"/>
            )}
            <FormControl isInvalid={isInputInvalid} align="center" pl="xs" pr="xs">
                <Input
                    type="number"
                    placeholder={pageNumber}
                    textAlign="center"
                    width="50px"
                    onBlur={handleOnBlur}
                />
                {isInputInvalid && (
                    <FormErrorMessage>Page out of range</FormErrorMessage>
                )}
            </FormControl>
            {currentPage + 1 < lastPage ? (
                <IconButton
                    onClick={() => onPageNumberChange(">")}
                    icon={<ChevronRightIcon />}
                    color="gray-4"
                    variant="ghost"
                    pr="xs"
                    _hover={{
                        transform: "scale(1.2)",
                        color: "#007DFF"
                    }}
                />
            ) : (
                <Box pr="xs"/>
            )}
            <Text color="gray-3" whiteSpace="nowrap">
                out of {lastPage}
            </Text>
        </Flex>
    );
}

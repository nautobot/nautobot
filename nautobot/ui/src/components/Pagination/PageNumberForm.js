import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Box, Flex, FormControl, Input, Text } from "@nautobot/nautobot-ui";
import { IconButton } from "@chakra-ui/react";
import {
    ArrowLeftIcon,
    ArrowRightIcon,
    ChevronLeftIcon,
    ChevronRightIcon,
} from "@chakra-ui/icons";

export default function PageNumberForm({
    firstPage,
    lastPage,
    pageSize,
    scroll_ref,
    totalDataCount,
    trueCurrentPage,
}) {
    let [searchParams, setSearchParams] = useSearchParams();

    // State to track the current page number
    const [pageNumber, setPageNumber] = useState(trueCurrentPage);
    // State to track the page number form control input validity
    const [isInputInvalid, setIsInputInvalid] = useState(false);
    // State to track if the input box is focused
    const [isInputFocused, setIsInputFocused] = useState(false);

    // Keeps the pageNumber var updated to trueCurrentPage (i.e. if trueCurrentPage changes via arrow click)
    useEffect(() => {
        setPageNumber(trueCurrentPage);
    }, [trueCurrentPage]);

    // Sets isInputFocused to true
    function handleOnFocus() {
        setIsInputFocused(true);
    }

    // Changes the page number based on the input component after a blur event (i.e. when user clicks out of input box and element loses focus)
    function handleOnBlur(event) {
        const enteredValue = parseInt(event.target.value);
        // Checks that the entered value is a number and within the valid page range
        if (
            !isNaN(enteredValue) &&
            enteredValue >= firstPage &&
            enteredValue <= lastPage
        ) {
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
        else if (event.target.value === "") {
            setIsInputInvalid(false);
        }
        // Otherwise, mark input as invalid
        else {
            setIsInputInvalid(true);
        }
        setIsInputFocused(false);
    }

    function handleOnKeyDown(event) {
        if (event.key === "Enter") {
            event.preventDefault();

            const enteredValue = parseInt(event.target.value);
            // Checks that the entered value is a number and within the valid page range
            if (
                !isNaN(enteredValue) &&
                enteredValue >= firstPage &&
                enteredValue <= lastPage
            ) {
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
            else if (event.target.value === "") {
                setIsInputInvalid(false);
            }
            // Otherwise, mark input as invalid
            else {
                setIsInputInvalid(true);
            }
            setIsInputFocused(false);
        }
    }

    function onPageNumberChange(targetPageNumber) {
        let limit = searchParams.get("limit");
        /* TODO: we need a REST API endpoint to query get_settings_or_config("PAGINATE_COUNT") rather than hard-coding this to 50. */
        // Scroll to the top of the ObjectListTable Container on table reload
        scroll_ref.current.scrollIntoView({
            alignToTop: true,
            behavior: "smooth",
        });

        let newPageNumber;
        if (targetPageNumber === "<") {
            newPageNumber = trueCurrentPage - 1;
        } else if (targetPageNumber === ">") {
            newPageNumber = trueCurrentPage + 1;
        } else {
            newPageNumber = targetPageNumber;
        }

        setIsInputInvalid(false);

        setSearchParams({
            limit: limit ? limit : 50,
            offset: pageSize * (newPageNumber - 1),
        });
    }

    return (
        <Flex align="center">
            <Box
                color="gray-3"
                pl="xs"
                pr="xs"
                mr="lg"
                fontSize="md"
                border="1px"
                borderColor="gray-1"
                borderRadius="sm"
            >
                {totalDataCount} rows
            </Box>
            <Text color="gray-3" whiteSpace="nowrap">
                You are on page
            </Text>
            {trueCurrentPage > firstPage ? (
                <Box>
                    <IconButton
                        onClick={() => onPageNumberChange(firstPage)}
                        icon={<ArrowLeftIcon boxSize={3} />}
                        color="gray-4"
                        variant="ghost"
                        pl="sm"
                        _hover={{
                            transform: "scale(1.2)",
                            color: "#007DFF",
                        }}
                    />
                    <IconButton
                        onClick={() => onPageNumberChange("<")}
                        icon={<ChevronLeftIcon />}
                        color="gray-4"
                        variant="ghost"
                        pl="xs"
                        _hover={{
                            transform: "scale(1.2)",
                            color: "#007DFF",
                        }}
                    />
                </Box>
            ) : (
                <Box pl="xs" />
            )}
            <FormControl
                isInvalid={isInputInvalid}
                align="center"
                pl="xs"
                pr="xs"
            >
                <Input
                    type="number"
                    placeholder={isInputFocused ? "" : pageNumber}
                    textAlign="center"
                    width="50px"
                    onFocus={handleOnFocus}
                    onBlur={handleOnBlur}
                    onKeyDown={handleOnKeyDown}
                />
            </FormControl>
            {trueCurrentPage < lastPage ? (
                <Box>
                    <IconButton
                        onClick={() => onPageNumberChange(">")}
                        icon={<ChevronRightIcon />}
                        color="gray-4"
                        variant="ghost"
                        pr="xs"
                        _hover={{
                            transform: "scale(1.2)",
                            color: "#007DFF",
                        }}
                    />
                    <IconButton
                        onClick={() => onPageNumberChange(lastPage)}
                        icon={<ArrowRightIcon boxSize={3} />}
                        color="gray-4"
                        variant="ghost"
                        pr="sm"
                        _hover={{
                            transform: "scale(1.2)",
                            color: "#007DFF",
                        }}
                    />
                </Box>
            ) : (
                <Box pr="xs" />
            )}
            <Text color="gray-3" whiteSpace="nowrap">
                out of {lastPage}
            </Text>
        </Flex>
    );
}

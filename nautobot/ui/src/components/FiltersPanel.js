import {
    Box,
    Button,
    calc,
    CloseButton,
    Divider,
    Flex,
    FormContainer,
    FormControl,
    FormLabel,
    forwardRef,
    getCssVar,
    Heading,
    Input,
    NtcThumbnailIcon,
    ReactSelect,
    Tag,
    TagCloseButton,
    TagLabel,
} from "@nautobot/nautobot-ui";
import React, {
    cloneElement,
    createContext,
    Fragment,
    isValidElement,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";
import { useSearchParams } from "react-router-dom";

export const FILTER_RESET_QUERY_PARAMS = ["offset"];
export const NON_FILTER_QUERY_PARAMS = [
    // Copied from `nautobot/core/api/filter_backends.py`.
    "api_version",
    "depth",
    "format",
    "include",
    "limit",
    "offset",
    "sort",
];

const FiltersPanel = forwardRef(
    (
        {
            children,
            content,
            id,
            isOpen,
            right = getCssVar("space.md").reference,
            title,
            width = "400px",
            onClose,
            onMount,
            ...rest
        },
        ref
    ) => {
        const internalRef = useRef();

        const filtersPanelRef = ref ?? internalRef;

        useEffect(() => {
            onMount?.(filtersPanelRef);
        }, []); // eslint-disable-line react-hooks/exhaustive-deps

        return (
            <Flex
                ref={filtersPanelRef}
                background="white-0"
                borderRadius="md"
                direction="column"
                height={calc.subtract(
                    getCssVar("sizes.full").reference,
                    getCssVar("space.md").reference
                )}
                marginLeft="md"
                overflow="auto"
                position="absolute"
                right={right}
                top={0}
                transitionDuration="default"
                transitionProperty="opacity, transform, visibility"
                transitionTimingFunction="default"
                width={width}
                {...(isOpen
                    ? {
                          opacity: 1,
                          visibility: "visible",
                      }
                    : {
                          opacity: 0,
                          transform: "translateX(100%)",
                          visibility: "hidden",
                      })}
                {...rest}
            >
                {children ? (
                    children
                ) : (
                    <>
                        <Flex align="center" flex="none" gap="sm" margin="md">
                            <NtcThumbnailIcon height="auto" width={24} />
                            <Heading lineHeight="tall">{title}</Heading>
                            <CloseButton marginLeft="auto" onClick={onClose} />
                        </Flex>
                        <Box flex="1" paddingBottom="md" paddingX="md">
                            {isValidElement(content)
                                ? cloneElement(content, {
                                      onClose,
                                      ...content?.props,
                                  })
                                : content}
                        </Box>
                    </>
                )}
            </Flex>
        );
    }
);

FiltersPanel.displayName = "FiltersPanel";

export const FiltersPanelContainer = forwardRef(
    ({ children, ...rest }, ref) => {
        const filtersPanelContext = useFiltersPanelContext();

        const hasPanels =
            filtersPanelContext.panels.length > 0 &&
            filtersPanelContext.panels.some((panel) => panel?.isOpen);

        return (
            <Box
                ref={ref}
                as="aside"
                flex="none"
                height="full"
                position="relative"
                transitionDuration="default"
                transitionProperty="width"
                transitionTimingFunction="default"
                width={
                    hasPanels
                        ? calc.add(getCssVar("space.md").reference, "400px")
                        : 0
                }
                {...rest}
            >
                {filtersPanelContext.panels.map((props) => (
                    <FiltersPanel key={props.id} {...props} />
                ))}
            </Box>
        );
    }
);

FiltersPanelContainer.displayName = "FiltersPanelContainer";

export const FiltersPanelContent = forwardRef(
    ({ lookupFields, objectType, onClose, onSave }, ref) => {
        const LAST_USED_FILTERS_LOCAL_STORAGE_KEY = "lastUsedFilters";

        const [searchParams, setSearchParams] = useSearchParams();

        const previousObjectTypeRef = useRef(objectType);

        const isFilterAlreadyApplied = useCallback(
            (label, value) =>
                searchParams
                    .getAll(label)
                    .some((searchParamValue) => searchParamValue === value),
            [searchParams]
        );

        /*
         * `activeFilters` do not use `React` state, to keep `searchParams` as
         * a single source of truth for them. Otherwise, if `useState` was used,
         * it would have to be synced with `searchParams`, similarly to how
         * `lastUsedFilters` state is synced with `localStorage`.
         */
        const activeFilters = useMemo(
            () =>
                [...searchParams]
                    .filter(
                        ([param]) => !NON_FILTER_QUERY_PARAMS.includes(param)
                    )
                    .map(([param, value]) => ({ label: param, value })),
            [searchParams]
        );

        const addActiveFilter = useCallback(
            ({ label, value }) => {
                if (label && value && !isFilterAlreadyApplied(label, value)) {
                    setSearchParams([
                        [label, value],
                        ...[...searchParams].filter(
                            ([searchParamLabel]) =>
                                !FILTER_RESET_QUERY_PARAMS.includes(
                                    searchParamLabel
                                )
                        ),
                    ]);
                }
            },
            [isFilterAlreadyApplied, searchParams, setSearchParams]
        );

        const removeActiveFilter = useCallback(
            ({ label, value }) => {
                if (label && value && isFilterAlreadyApplied(label, value)) {
                    setSearchParams(
                        [...searchParams]
                            .filter(
                                ([searchParamLabel, searchParamValue]) =>
                                    searchParamLabel !== label ||
                                    searchParamValue !== value
                            )
                            .filter(
                                ([searchParamLabel]) =>
                                    !FILTER_RESET_QUERY_PARAMS.includes(
                                        searchParamLabel
                                    )
                            )
                    );
                }
            },
            [isFilterAlreadyApplied, searchParams, setSearchParams]
        );

        const clearActiveFilters = useCallback(
            () =>
                setSearchParams(
                    [...searchParams]
                        .filter(([searchParamLabel]) =>
                            NON_FILTER_QUERY_PARAMS.includes(searchParamLabel)
                        )
                        .filter(
                            ([searchParamLabel]) =>
                                !FILTER_RESET_QUERY_PARAMS.includes(
                                    searchParamLabel
                                )
                        )
                ),
            [searchParams, setSearchParams]
        );

        const getInitialLastUsedFilters = useCallback(() => {
            try {
                const lastUsedFiltersLocalStorage = window.localStorage.getItem(
                    LAST_USED_FILTERS_LOCAL_STORAGE_KEY
                );

                return lastUsedFiltersLocalStorage
                    ? JSON.parse(lastUsedFiltersLocalStorage)?.[objectType] ??
                          []
                    : [];
            } catch (exception) {}

            return [];
        }, [objectType]);

        const [lastUsedFilters, setLastUsedFilters] = useState(
            getInitialLastUsedFilters
        );

        const [lookupField, setLookupField] = useState(null);
        const [lookupType, setLookupType] = useState(null);
        const [lookupValue, setLookupValue] = useState("");

        const lookupFieldOptions = useMemo(
            () =>
                Object.entries(lookupFields).map(([key, value]) => ({
                    label: value.label,
                    value: key,
                })),
            [lookupFields]
        );

        const fieldLookupChoices = useMemo(
            () =>
                lookupField
                    ? lookupFields[lookupField].lookup_types.map((filter) => ({
                          value: filter.value,
                          label: filter.label,
                      }))
                    : [],
            [lookupField, lookupFields]
        );

        const onChangeLookupField = useCallback(
            (newValue) => setLookupField(newValue.value),
            [setLookupField]
        );

        const onChangeLookupType = useCallback(
            (newValue) => setLookupType(newValue.value),
            [setLookupType]
        );

        const onChangeLookupValue = useCallback(
            (event) => setLookupValue(event.currentTarget.value),
            [setLookupValue]
        );

        const onSubmitFilter = useCallback(
            (event) => {
                event.preventDefault();

                if (
                    lookupField &&
                    lookupType &&
                    lookupValue &&
                    !isFilterAlreadyApplied(lookupType, lookupValue)
                ) {
                    addActiveFilter({ label: lookupType, value: lookupValue });

                    setLastUsedFilters((currentLastUsedFilters) =>
                        currentLastUsedFilters.every(
                            ({ label, value }) =>
                                label !== lookupType || value !== lookupValue
                        )
                            ? [
                                  { label: lookupType, value: lookupValue },
                                  ...currentLastUsedFilters,
                              ]
                            : currentLastUsedFilters
                    );
                }
            },
            [
                addActiveFilter,
                isFilterAlreadyApplied,
                lookupField,
                lookupType,
                lookupValue,
                setLastUsedFilters,
            ]
        );

        useEffect(() => {
            setLookupField(null);
        }, [lookupFields, setLookupField]);

        useEffect(() => {
            fieldLookupChoices.length === 1
                ? setLookupType(fieldLookupChoices[0].value)
                : setLookupType(null);
            setLookupValue("");
        }, [fieldLookupChoices, lookupField, setLookupType, setLookupValue]);

        useEffect(() => {
            if (
                typeof window !== "undefined" &&
                window.localStorage &&
                previousObjectTypeRef.current === objectType
            ) {
                try {
                    const lastUsedFiltersLocalStorage =
                        window.localStorage.getItem(
                            LAST_USED_FILTERS_LOCAL_STORAGE_KEY
                        );

                    const currentLastUsedFilters = lastUsedFiltersLocalStorage
                        ? JSON.parse(lastUsedFiltersLocalStorage) ?? {}
                        : {};

                    window.localStorage.setItem(
                        LAST_USED_FILTERS_LOCAL_STORAGE_KEY,
                        JSON.stringify({
                            ...currentLastUsedFilters,
                            [objectType]: lastUsedFilters,
                        })
                    );
                } catch (exception) {
                    console.error(exception);

                    window.localStorage.removeItem(
                        LAST_USED_FILTERS_LOCAL_STORAGE_KEY
                    );
                }
            }
        }, [lastUsedFilters, objectType]);

        useEffect(() => {
            if (previousObjectTypeRef.current !== objectType) {
                setLastUsedFilters(getInitialLastUsedFilters);
            }

            previousObjectTypeRef.current = objectType;
        }, [getInitialLastUsedFilters, objectType, setLastUsedFilters]);

        return (
            <Box height="full" ref={ref}>
                <FormContainer as="form" onSubmit={onSubmitFilter}>
                    <Heading as="h3" size="H3">
                        Add new filter
                    </Heading>

                    <FormControl>
                        <FormLabel>Filter Field</FormLabel>
                        <ReactSelect
                            isSearchable
                            name="lookup_field"
                            options={lookupFieldOptions}
                            value={
                                lookupFieldOptions.find(
                                    ({ value }) => value === lookupField
                                ) ?? null
                            }
                            onChange={onChangeLookupField}
                        />
                    </FormControl>

                    <FormControl>
                        <FormLabel>Lookup Type</FormLabel>
                        <ReactSelect
                            isSearchable
                            name="lookup_type"
                            options={fieldLookupChoices}
                            value={
                                fieldLookupChoices.find(
                                    ({ value }) => value === lookupType
                                ) ?? null
                            }
                            onChange={onChangeLookupType}
                        />
                    </FormControl>

                    <FormControl>
                        <FormLabel>Value</FormLabel>
                        <Input
                            name="lookup_value"
                            placeholder="Type..."
                            value={lookupValue}
                            onChange={onChangeLookupValue}
                        />
                    </FormControl>

                    <Button
                        alignSelf="flex-end"
                        isDisabled={!lookupField || !lookupType || !lookupValue}
                        type="submit"
                        variant="secondary"
                    >
                        Add filter
                    </Button>
                </FormContainer>

                {[
                    {
                        filters: activeFilters,
                        heading: "Active filters",
                        tag: {
                            variant: "info",
                            label: { color: "gray-1" },
                            closeButton: { onClick: removeActiveFilter },
                        },
                        onClickClearAll: clearActiveFilters,
                    },
                    {
                        filters: lastUsedFilters,
                        heading: "Last used filters",
                        tag: {
                            backgroundColor: "gray-0",
                            boxShadow: "none",
                            color: "black-0",
                            label: { color: "gray-4" },
                            closeButton: {
                                color: "blue-1",
                                sx: { svg: { transform: "rotate(-45deg)" } },
                                onClick: addActiveFilter,
                            },
                        },
                        onClickClearAll: () => setLastUsedFilters([]),
                    },
                ].map(
                    ({
                        filters,
                        heading,
                        tag: { label, closeButton, ...tag },
                        onClickClearAll,
                    }) => (
                        <Fragment key={heading}>
                            <Divider marginBottom="sm" marginTop="lg" />

                            <Box>
                                <Heading as="h3" size="H3">
                                    {heading}
                                </Heading>

                                <Flex
                                    align="center"
                                    gap="sm"
                                    marginY="sm"
                                    wrap="wrap"
                                >
                                    {filters.map((filter) => (
                                        <Tag
                                            key={`${filter.label}: ${filter.value}`}
                                            {...tag}
                                        >
                                            <TagLabel fontSize="md">
                                                <Box
                                                    as="span"
                                                    marginRight="xs"
                                                    {...label}
                                                >
                                                    {filter.label}:
                                                </Box>
                                                {filter.value}
                                            </TagLabel>
                                            {filter.label !== "q" && (
                                                <TagCloseButton
                                                    marginLeft="xs"
                                                    {...closeButton}
                                                    onClick={() =>
                                                        closeButton.onClick(
                                                            filter
                                                        )
                                                    }
                                                />
                                            )}
                                        </Tag>
                                    ))}
                                </Flex>

                                <Button
                                    isDisabled={filters.length === 0}
                                    display="block"
                                    marginLeft="auto"
                                    type="reset"
                                    variant="secondary"
                                    onClick={onClickClearAll}
                                >
                                    Clear all
                                </Button>
                            </Box>
                        </Fragment>
                    )
                )}
            </Box>
        );
    }
);

FiltersPanelContent.displayName = "FiltersPanelContent";

export const FiltersPanelContext = createContext({
    close: (id) => {},
    mount: (props) => {},
    open: (id) => {},
    panels: [],
    setPanels: (currentPanels) => {},
    unmount: (id) => {},
});

FiltersPanelContext.displayName = "FiltersPanelContext";

export const FiltersPanelContextProvider = ({ children }) => {
    const [panels, setPanels] = useState([]);

    const unmount = useCallback(
        (id) => {
            setPanels((currentPanels) =>
                currentPanels.filter((currentPanel) => currentPanel.id !== id)
            );
        },
        [setPanels]
    );

    const close = useCallback(
        (id) => {
            setPanels((currentPanels) =>
                currentPanels.map((currentPanel) =>
                    currentPanel.id === id
                        ? {
                              ...currentPanel,
                              isOpen: false,
                              onTransitionEnd: (event) => {
                                  if (event.currentTarget === event.target) {
                                      unmount(currentPanel?.id);
                                  }
                              },
                          }
                        : currentPanel
                )
            );
        },
        [setPanels, unmount]
    );

    const open = useCallback(
        (id) => {
            setPanels((currentPanels) => [
                ...currentPanels.map((currentPanel) =>
                    currentPanel.id === id
                        ? {
                              ...currentPanel,
                              isOpen: true,
                          }
                        : {
                              ...currentPanel,
                              isOpen: false,
                              onTransitionEnd: (event) => {
                                  if (event.currentTarget === event.target) {
                                      unmount(currentPanel?.id);
                                  }
                              },
                          }
                ),
            ]);
        },
        [setPanels, unmount]
    );

    const mount = useCallback(
        (props) => {
            setPanels((currentPanels) => {
                const doesPanelAlreadyExist = currentPanels.some(
                    (currentPanel) => currentPanel.id === props.id
                );

                const mountProps = {
                    ...props,
                    onClose: () => {
                        close(props.id);
                    },
                    onMount: (ref) => {
                        if (ref?.current) {
                            // eslint-disable-next-line no-unused-expressions
                            window.getComputedStyle(ref.current).opacity;
                        }

                        open(props.id);
                    },
                };

                return doesPanelAlreadyExist
                    ? currentPanels.map((currentPanel) =>
                          currentPanel.id === props.id
                              ? { ...mountProps, isOpen: currentPanel.isOpen }
                              : currentPanel
                      )
                    : [...currentPanels, { ...mountProps, isOpen: false }];
            });
        },
        [close, open, setPanels]
    );

    const value = useMemo(
        () => ({ close, mount, open, panels, setPanels, unmount }),
        [close, mount, open, panels, setPanels, unmount]
    );

    return (
        <FiltersPanelContext.Provider value={value}>
            {children}
        </FiltersPanelContext.Provider>
    );
};

FiltersPanelContextProvider.displayName = "FiltersPanelContextProvider";

export const useFiltersPanel = (props) => {
    const {
        close: filtersPanelContextClose,
        mount: filtersPanelContextMount,
        panels: filtersPanelContextPanels,
    } = useFiltersPanelContext();

    const id = useMemo(() => props?.id ?? Math.random(), [props?.id]);

    const isOpen = useMemo(
        () => !!filtersPanelContextPanels.find((panel) => panel.id === id),
        [filtersPanelContextPanels, id]
    );

    const close = useCallback(() => {
        filtersPanelContextClose(id);
    }, [filtersPanelContextClose, id]);

    const open = useCallback(() => {
        filtersPanelContextMount({ ...props, id });
    }, [filtersPanelContextMount, id, props]);

    return useMemo(() => ({ close, isOpen, open }), [close, isOpen, open]);
};

export const useFiltersPanelContext = () => useContext(FiltersPanelContext);

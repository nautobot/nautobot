import {
    Box,
    calc,
    CloseButton,
    Flex,
    forwardRef,
    getCssVar,
    Heading,
    NtcThumbnailIcon,
} from "@nautobot/nautobot-ui";
import React, {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";

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
                        <Flex align="center" gap="sm" margin="md">
                            <NtcThumbnailIcon height="auto" width={24} />
                            <Heading lineHeight="tall">{title}</Heading>
                            <CloseButton marginLeft="auto" onClick={onClose} />
                        </Flex>
                        <Box paddingBottom="md" paddingX="md">
                            {content}
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

import { render } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Pagination } from "@components/Pagination";

describe("Pagination", () => {
    it("renders the pagination form with correct start and end range", () => {
        const data_count = 30;
        const page_size = 10;
        const active_page = 1;
        const url = "https://example.com/list";

        render(
            <BrowserRouter>
                <Pagination
                    url={url}
                    data_count={data_count}
                    page_size={page_size}
                    active_page={active_page}
                />
            </BrowserRouter>
        );

        // const allPaginationButton = document.evaluate('//*[contains(@class, "page-link")]', document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        // const firstPageButton = allPaginationButton.snapshotItem(0)
        // const totalBtn = allPaginationButton.snapshotLength
        // const lastPageButton = allPaginationButton.snapshotItem(totalBtn-1)
        // const pageOneButton = allPaginationButton.snapshotItem(1)
        // const pageTwoButton = allPaginationButton.snapshotItem(2)
        // const pageThreeButton = allPaginationButton.snapshotItem(3)

        // // Assert we only have 5 buttons, i.e First, 1, 2, 3 and Last
        // expect(allPaginationButton.snapshotLength).toBe(5)

        // Assert all has approriate href links
        // expect(firstPageButton.getAttribute("href")).toBe("https://example.com/list?limit=10&offset=0")
        // expect(pageOneButton.getAttribute("href")).toBe("https://example.com/list?limit=10&offset=0")
        // expect(pageTwoButton.getAttribute("href")).toBe("https://example.com/list?limit=10&offset=10")
        // expect(pageThreeButton.getAttribute("href")).toBe("https://example.com/list?limit=10&offset=20")
        // expect(lastPageButton.getAttribute("href")).toBe("https://example.com/list?limit=10&offset=20")

        // TODO(timizuo): Include test to get active Button
    });
});

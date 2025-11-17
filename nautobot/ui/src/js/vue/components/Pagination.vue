<template>
    <nav v-if="totalPages > 1" aria-label="Page navigation">
        <ul class="pagination justify-content-center">
            <li class="page-item" :class="{ disabled: currentPage === 1 }">
                <a
                    class="page-link"
                    href="#"
                    @click.prevent="goToPage(currentPage - 1)"
                >
                    Previous
                </a>
            </li>

            <li
                v-for="page in visiblePages"
                :key="page"
                class="page-item"
                :class="{ active: page === currentPage }"
            >
                <a class="page-link" href="#" @click.prevent="goToPage(page)">
                    {{ page }}
                </a>
            </li>

            <li
                class="page-item"
                :class="{ disabled: currentPage === totalPages }"
            >
                <a
                    class="page-link"
                    href="#"
                    @click.prevent="goToPage(currentPage + 1)"
                >
                    Next
                </a>
            </li>
        </ul>

        <div class="text-center text-muted mt-2">
            Showing page {{ currentPage }} of {{ totalPages }} ({{ totalCount }}
            total items)
        </div>
    </nav>
</template>

<script>
export default {
    name: 'Pagination',
    props: {
        currentPage: {
            type: Number,
            required: true,
        },
        totalPages: {
            type: Number,
            required: true,
        },
        totalCount: {
            type: Number,
            required: true,
        },
        maxVisible: {
            type: Number,
            default: 10,
        },
    },
    computed: {
        visiblePages() {
            const pages = [];
            const start = Math.max(
                1,
                this.currentPage - Math.floor(this.maxVisible / 2),
            );
            const end = Math.min(this.totalPages, start + this.maxVisible - 1);

            for (let i = start; i <= end; i++) {
                pages.push(i);
            }

            return pages;
        },
    },
    methods: {
        goToPage(page) {
            if (
                page >= 1 &&
                page <= this.totalPages &&
                page !== this.currentPage
            ) {
                this.$emit('page-change', page);
            }
        },
    },
};
</script>

<style scoped>
.pagination {
    margin-top: 2rem;
}
</style>
